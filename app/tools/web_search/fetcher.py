# app/tools/web_search/fetcher.py
"""自研网页正文爬取器(默认正文提取路径,替代 Tavily)。

流水线: SSRF 校验 → httpx 异步抓取 → 编码探测 → trafilatura 正文提取(lxml 启发式降级)。

并发模型:
- 模块级单例 httpx.AsyncClient,复用连接池(keep-alive),由 app.main lifespan 创建/回收。
- extract_batch 用 asyncio.Semaphore 限流 + asyncio.gather 并发,单 URL 失败不影响批次。
"""
import asyncio
import ipaddress
import re
import socket
from typing import Optional

import httpx

from app.config import (
    FETCHER_ALLOWED_IPS,
    FETCHER_CONCURRENCY,
    FETCHER_CONNECT_TIMEOUT,
    FETCHER_MAX_RETRIES,
    FETCHER_MAX_URLS,
    FETCHER_MIN_CHARS,
    FETCHER_READ_TIMEOUT,
    FETCHER_SSRF_ENABLED,
    FETCHER_USER_AGENT,
)


class FetchError(Exception):
    """抓取/提取异常(SSRF 拦截 / 网络错误 / 正文过短)。"""


def _build_allowed_networks() -> list:
    """把配置里的 CIDR 字符串预编译为 ip_network。"""
    nets = []
    for cidr in FETCHER_ALLOWED_IPS:
        try:
            nets.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            pass
    return nets


_ALLOWED_NETWORKS = _build_allowed_networks()


def _is_allowed(ip: ipaddress) -> bool:
    """IP 是否命中白名单 CIDR(fake-ip 段等)。"""
    return any(ip in net for net in _ALLOWED_NETWORKS)


# ------------------------------------------------------------------ #
# httpx AsyncClient 单例(lifespan 管理)
# ------------------------------------------------------------------ #
_client: Optional[httpx.AsyncClient] = None

_DEFAULT_HEADERS = {
    'User-Agent': FETCHER_USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def get_client() -> httpx.AsyncClient:
    """获取/懒创建单例 AsyncClient。"""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers=_DEFAULT_HEADERS,
            timeout=httpx.Timeout(
                connect=FETCHER_CONNECT_TIMEOUT,
                read=FETCHER_READ_TIMEOUT,
                write=10.0,
                pool=5.0,
            ),
            follow_redirects=True,
            max_redirects=5,
            limits=httpx.Limits(
                max_connections=FETCHER_CONCURRENCY * 2,
                max_keepalive_connections=FETCHER_CONCURRENCY,
            ),
        )
    return _client


async def close_client() -> None:
    """lifespan shutdown 调用,回收连接池。"""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


# ------------------------------------------------------------------ #
# SSRF 防护
# ------------------------------------------------------------------ #
def validate_url(url: str) -> None:
    """校验 URL 安全性:仅 http(s),且解析出的 IP 不得落入私网/保留/元数据段。

    DNS rebinding(解析后 connect 前换 IP)是已知残留风险,根治需 transport hook 锁定 IP。
    """
    if not FETCHER_SSRF_ENABLED:
        return
    try:
        parsed = httpx.URL(url)
    except Exception as exc:  # noqa: BLE001
        raise FetchError(f'非法 URL: {exc}') from exc

    if parsed.scheme not in ('http', 'https'):
        raise FetchError(f'仅允许 http/https,拒绝 scheme: {parsed.scheme}')

    host = parsed.host
    if not host:
        raise FetchError('URL 缺少主机名')

    # 解析全部 A/AAAA 记录,逐个校验 IP 归属。
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise FetchError(f'域名解析失败: {host}') from exc

    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local       # 含 169.254.169.254 元数据端点
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ) and not _is_allowed(ip):
            raise FetchError(f'拒绝访问内网/保留地址: {host} -> {addr}')


# ------------------------------------------------------------------ #
# 编码探测
# ------------------------------------------------------------------ #
_META_CHARSET_RE = re.compile(rb'charset\s*=\s*["\']?\s*([a-zA-Z0-9_\-]+)', re.I)


def decode_bytes(raw: bytes, content_type: str = '') -> str:
    """字节流解码为文本。优先级: HTTP header > meta 标签 > 三级回退 > replace。"""
    candidates = []

    # 1) HTTP Content-Type 里的 charset
    for m in _META_CHARSET_RE.finditer(content_type.encode('utf-8', errors='ignore')):
        candidates.append(m.group(1).decode('ascii', errors='ignore').lower())
        break

    # 2) HTML meta 标签(只看前 4KB 提速)
    head = raw[:4096]
    for m in _META_CHARSET_RE.finditer(head):
        candidates.append(m.group(1).decode('ascii', errors='ignore').lower())
        break

    # 3) 三级回退
    candidates.extend(['utf-8', 'gbk', 'gb2312'])

    for enc in candidates:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')


# ------------------------------------------------------------------ #
# 正文提取(trafilatura 主路径 + lxml 启发式降级)
# ------------------------------------------------------------------ #
def _extract_with_lxml(html: str) -> tuple[str, str]:
    """降级路径: lxml 去 boilerplate 后取文本。标题取 <title>。"""
    from lxml import html as lxml_html

    try:
        tree = lxml_html.fromstring(html)
    except Exception:  # noqa: BLE001
        return '', ''

    title = ''
    title_nodes = tree.xpath('//title/text()')
    if title_nodes:
        title = title_nodes[0].strip()

    # 移除明显的非正文区块。
    for tag in ('script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript'):
        for node in tree.xpath(f'//{tag}'):
            node.getparent().remove(node)

    text = tree.text_content() if hasattr(tree, 'text_content') else ''
    text = re.sub(r'\s+', ' ', text).strip()
    return title, text


def extract_content(html: str, url: str = '') -> tuple[str, str]:
    """从 HTML 提取 (title, 正文)。trafilatura 为主,失败/过短降级 lxml。"""
    import trafilatura

    title = ''
    text = ''

    try:
        text = trafilatura.extract(
            html,
            url=url or None,
            include_tables=True,
            favor_recall=True,
            deduplicate=True,
        ) or ''
        try:
            meta = trafilatura.extract_metadata(html, default_url=url or None)
            if meta is not None:
                title = (meta.title or '').strip()
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        text = ''

    # trafilatura 提空或过短 → 降级 lxml 启发式。
    if len(text) < FETCHER_MIN_CHARS:
        fallback_title, fallback_text = _extract_with_lxml(html)
        if len(fallback_text) > len(text):
            text = fallback_text
            if not title:
                title = fallback_title

    return title.strip(), text.strip()


# ------------------------------------------------------------------ #
# 抓取与提取(单 URL)
# ------------------------------------------------------------------ #
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


async def _fetch_html(url: str) -> tuple[str, str]:
    """抓取单个 URL,返回 (html, content_type)。带重试。"""
    client = get_client()
    last_exc: Optional[Exception] = None
    for attempt in range(FETCHER_MAX_RETRIES + 1):
        try:
            resp = await client.get(url)
            if resp.status_code in _RETRYABLE_STATUS and attempt < FETCHER_MAX_RETRIES:
                await asyncio.sleep(0.8 * (attempt + 1))
                continue
            resp.raise_for_status()
            return decode_bytes(resp.content, resp.headers.get('content-type', '')), resp.headers.get('content-type', '')
        except httpx.HTTPStatusError:
            raise
        except (httpx.HTTPError, OSError) as exc:
            last_exc = exc
            if attempt < FETCHER_MAX_RETRIES:
                await asyncio.sleep(0.8 * (attempt + 1))
                continue
            raise
    raise FetchError(f'抓取失败: {last_exc}')


async def extract_one(url: str) -> dict:
    """抓取并提取单个 URL 的正文。失败返回 {url, error}。"""
    try:
        validate_url(url)
        html, _ = await _fetch_html(url)
        title, text = extract_content(html, url)
        if not text:
            return {'url': url, 'error': '未能提取到正文'}
        return {
            'url': url,
            'title': title,
            'raw_content': text,
            'word_count': len(text),
        }
    except FetchError as exc:
        return {'url': url, 'error': str(exc)}
    except (httpx.HTTPError, OSError) as exc:
        return {'url': url, 'error': f'网络错误: {exc}'}
    except Exception as exc:  # noqa: BLE001
        return {'url': url, 'error': f'提取失败: {exc}'}


# ------------------------------------------------------------------ #
# 批量并发
# ------------------------------------------------------------------ #
async def extract_batch(urls: list[str]) -> dict:
    """批量抓取并提取正文。并发限流,单 URL 失败不影响其他。

    返回 {'results': [...], 'failed_results': [...], 'response_time': float}。
    """
    start = asyncio.get_event_loop().time()

    # 去重(保序) + 截断。
    seen: set[str] = set()
    unique = [u for u in urls if u and u not in seen and not seen.add(u)][:FETCHER_MAX_URLS]

    sem = asyncio.Semaphore(FETCHER_CONCURRENCY)

    async def _bounded(url: str) -> dict:
        async with sem:
            return await extract_one(url)

    raw_results = await asyncio.gather(*[_bounded(u) for u in unique])

    results, failed_results = [], []
    for r in raw_results:
        if 'error' in r:
            failed_results.append(r)
        else:
            results.append(r)

    elapsed = asyncio.get_event_loop().time() - start
    return {
        'results': results,
        'failed_results': failed_results,
        'response_time': round(elapsed, 3),
    }
