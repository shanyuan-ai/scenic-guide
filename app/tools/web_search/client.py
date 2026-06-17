# app/tools/web_search/client.py
"""Tavily 风格 HTTP API 客户端。

走自建代理(TAVILY_BASE_URL),使用 Bearer token 鉴权。
支持 search / extract / map / crawl / research 五类端点。
所有方法返回规整后的 dict;失败抛 TavilyError。
"""
import json
import time
import urllib.error
import urllib.request
from typing import Any

from app.config import TAVILY_API_KEY, TAVILY_BASE_URL


class TavilyError(Exception):
    """Tavily 调用异常(未配置 key / HTTP 错误 / 网络失败)。"""


# 代理(tavily.ivanli.cc)对所有端点都会随机返回 554/5xx,
# 这些视为可重试的瞬时错误;4xx(鉴权/参数错误)不重试。
_RETRYABLE_STATUS = {429, 500, 502, 503, 504, 554}


def _request(path: str, payload: dict, timeout: int = 60, max_retries: int = 2) -> dict:
    """向代理发 POST,返回解析后的 JSON。

    遇到可重试状态码(554/5xx/429)或网络异常(超时/连接重置)时,
    按线性退避自动重试,最多 max_retries 次。
    """
    if not TAVILY_API_KEY:
        raise TavilyError('Tavily API key 未配置,请在 .env 中设置 TAVILY_API_KEY')

    url = f'{TAVILY_BASE_URL.rstrip("/")}/{path.lstrip("/")}'
    data = json.dumps(payload).encode('utf-8')

    last_exc: 'TavilyError | None' = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {TAVILY_API_KEY}',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            if exc.code in _RETRYABLE_STATUS and attempt < max_retries:
                last_exc = TavilyError(
                    f'Tavily HTTP {exc.code} (第 {attempt + 1}/{max_retries} 次重试): {body[:200]}'
                )
                time.sleep(0.8 * (attempt + 1))
                continue
            raise TavilyError(f'Tavily HTTP {exc.code}: {body[:500]}') from exc
        except TavilyError:
            raise
        except Exception as exc:  # noqa: BLE001  超时 / 连接重置等网络异常
            if attempt < max_retries:
                last_exc = TavilyError(
                    f'Tavily 请求失败 (第 {attempt + 1}/{max_retries} 次重试): {exc}'
                )
                time.sleep(0.8 * (attempt + 1))
                continue
            raise TavilyError(f'Tavily 请求失败: {exc}') from exc

    # 理论上不会走到(重试耗尽会在循环内 raise)
    raise last_exc or TavilyError('Tavily 请求失败')


def _result(r: dict) -> dict:
    """规整单条搜索/抓取结果。"""
    return {
        'title': r.get('title', ''),
        'url': r.get('url', ''),
        'content': r.get('content', ''),
        'raw_content': r.get('raw_content', ''),
        'score': r.get('score'),
    }


def search(
    query: str,
    max_results: int = 5,
    search_depth: str = 'basic',
    topic: str = 'general',
    include_answer: bool = False,
) -> dict:
    data = _request('search', {
        'query': query,
        'max_results': max_results,
        'search_depth': search_depth,
        'topic': topic,
        'include_answer': include_answer,
    })
    results = [
        {
            'title': r.get('title') or '',
            'url': r.get('url') or '',
            'content': r.get('content') or '',
            'score': r.get('score'),
        }
        for r in data.get('results', [])
    ]
    return {
        'query': data.get('query', query),
        'answer': data.get('answer'),
        'results': results,
        'response_time': data.get('response_time'),
    }


def extract(urls: list[str], extract_depth: str = 'basic') -> dict:
    data = _request('extract', {'urls': urls, 'extract_depth': extract_depth})
    results = [
        {
            'url': r.get('url') or '',
            'title': r.get('title') or '',
            'raw_content': r.get('raw_content') or '',
        }
        for r in data.get('results', [])
    ]
    return {
        'results': results,
        'failed_results': data.get('failed_results', []),
        'response_time': data.get('response_time'),
    }


def map_site(url: str, max_depth: int = 1, limit: int = 20) -> dict:
    data = _request('map', {'url': url, 'max_depth': max_depth, 'limit': limit})
    return {
        'base_url': data.get('base_url', url),
        'results': data.get('results', []),
        'response_time': data.get('response_time'),
    }


def crawl(url: str, max_depth: int = 1, limit: int = 10, timeout: int = 180) -> dict:
    # crawl 会批量抓取,较慢,默认超时放宽到 180s。
    data = _request(
        'crawl',
        {'url': url, 'max_depth': max_depth, 'limit': limit},
        timeout=timeout,
    )
    results = [_result(r) for r in data.get('results', [])]
    return {
        'results': results,
        'response_time': data.get('response_time'),
    }


def research(input_text: str, max_results: int = 5, timeout: int = 300) -> dict:
    # research 是深度研究,耗时长;输出结构不固定,原样透传。
    return _request(
        'research',
        {'input': input_text, 'max_results': max_results},
        timeout=timeout,
    )
