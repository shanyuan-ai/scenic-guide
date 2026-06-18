# app/tools/feedback/integrator.py
"""报单智能整合模块。

流程:
1. 关键词原子化: 复合关键词(如 "垃圾桶少;卫生差")拆成独立原子
2. LLM 两轮交互:
   - 第 1 轮: 把已评估报单的关键词发给 LLM,让它判断新报单关键词中哪些与已有问题相似
   - 第 2 轮: 根据 LLM 回传的关键词查到对应报单详情,再让 LLM 评估是否合并
3. 合并决策:
   - 合并: 被合并报单移入回收站,原始报单得到补充(duplicate_count +1, group_summary 更新)
   - 新问题: 标记 evaluated=True, 成为新的"已评估锚点"供未来匹配
4. 优先级调整: 按 duplicate_count 自动提升 priority
5. LLM 不可用时降级为规则版(按 scenic_spot+type 签名分组)
"""
import json
import logging
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.llm import llm_chat_json, llm_chat
from app.tools.feedback.models import FeedbackItem, FeedbackRecycleBin

logger = logging.getLogger(__name__)

# 优先级阈值: duplicate_count >= N 时升级
PRIORITY_THRESHOLDS = [
    (8, 'P1'),
    (4, 'P2'),
    (2, 'P3'),
]


def _parse_keywords(raw) -> list[str]:
    """把存储的 keywords(JSON 字符串或列表)解析为 Python list。"""
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _atomize_keywords(keywords: list[str]) -> list[str]:
    """关键词原子化:按分号/逗号/顿号拆分,去重去空。"""
    atoms = set()
    for kw in keywords:
        if not kw:
            continue
        # 按各种分隔符拆
        for sep in [';', '；', ',', '，', '、', '|']:
            kw = kw.replace(sep, '\n')
        for part in kw.split('\n'):
            part = part.strip()
            if part:
                atoms.add(part)
    return sorted(atoms)


def normalize_keywords(raw) -> list[str]:
    """规范化关键词为单关键词:先原子化(拆复合),再只保留第一个。

    单关键词设计:每个报单只挂一个关键词,避免一个报单同时匹配多个组、
    以及合并时关键词无限累加膨胀,降低匹配歧义与 bug 风险。
    """
    atoms = _atomize_keywords(_parse_keywords(raw))
    return atoms[:1]


def _count_to_priority(count: int) -> str | None:
    """按重复数量返回对应优先级;count<2 返回 None(不调整)。"""
    for threshold, prio in PRIORITY_THRESHOLDS:
        if count >= threshold:
            return prio
    return None


# ============================================================
# LLM 路径
# ============================================================

def _llm_extract_keywords(description: str) -> list[str]:
    """LLM 从描述提取单个核心关键词(仅当报单未提供 keywords 时使用)。

    单关键词设计:只返回长度≤1的列表(原子化后取第一个)。
    """
    prompt = f"""从以下游客反馈中提取1个最能代表核心问题的关键词。
关键词应简洁(2-6字),如"垃圾桶少"、"排队时间长"、"卫生间脏"、"门票贵"。

反馈描述: {description}

用JSON数组格式返回,只含1个关键词: ["关键词"]"""
    result = llm_chat_json(prompt, temperature=0.1, max_tokens=60)
    if isinstance(result, list) and result:
        return normalize_keywords([str(result[0])])
    return []


def _llm_pick_primary_keyword(description: str, keywords: list[str]) -> str | None:
    """从多个候选关键词中,让 LLM 选出最能代表核心原因的一个。

    优先选具体、可定位、可执行的原因(如"垃圾桶少"、"排队时间长"),
    避开空泛宽泛的结果描述(如"卫生差"、"服务差"、"环境差")。

    Returns:
        选中的关键词(必须是候选之一);LLM 失败返回 None(调用方降级取第一个)。
    """
    if len(keywords) <= 1:
        return keywords[0] if keywords else None

    candidates = '\n'.join(f'{i + 1}. {kw}' for i, kw in enumerate(keywords))
    prompt = f"""从以下候选关键词中,选出1个最能代表反馈核心原因的关键词。
优先选具体、可定位、可执行的原因(如"垃圾桶少"、"排队时间长"、"门票贵"),避免空泛宽泛的描述(如"卫生差"、"服务差"、"环境差")。

反馈描述: {description}

候选关键词:
{candidates}

只返回选中关键词的原文(从候选中复制),不要解释,不要序号。"""
    text = llm_chat(prompt, temperature=0.1, max_tokens=30)
    if not text:
        return None
    cleaned = text.strip().strip('"\'`，。、；:：').strip()
    # 优先精确匹配候选词
    for kw in keywords:
        if cleaned == kw:
            return kw
    # 容错:包含关系
    for kw in keywords:
        if kw in cleaned or cleaned in kw:
            return kw
    return None


def _llm_round1_match(new_keywords: list[str], evaluated_items: list[FeedbackItem]) -> dict | None:
    """第 1 轮: 把已评估报单关键词 + 新报单关键词发给 LLM,
    让它判断新关键词与哪些已有问题相似。

    Returns:
        {keyword: [matched_evaluated_ids]} 映射; 失败返回 None。
    """
    if not evaluated_items:
        # 没有已评估报单,所有新关键词都是新问题
        return {}

    # 构造已评估报单的关键词列表(带序号)
    eval_lines = []
    eval_id_map = {}  # 序号 -> evaluated item id
    for idx, item in enumerate(evaluated_items, 1):
        kws = _parse_keywords(item.keywords)
        eval_lines.append(f"[{idx}] 关键词: {', '.join(kws) if kws else '(无)'} (报单#{item.id}: {item.description[:40]})")
        eval_id_map[idx] = item.id

    new_lines = []
    new_kw_map = {}  # 新关键词序号
    for idx, kw in enumerate(new_keywords, 1):
        new_lines.append(f"[N{idx}] {kw}")
        new_kw_map[idx] = kw

    prompt = f"""你是景区反馈分析助手。下面有一批"已评估的反馈关键词"(带序号)和"待评估的新反馈关键词"(带N前缀序号)。

已评估反馈:
{chr(10).join(eval_lines)}

待评估新关键词:
{chr(10).join(new_lines)}

请判断每个新关键词(N序号)是否与某个已评估反馈(数字序号)描述的是同一类问题。
只返回真正相似/重复的配对。

用JSON格式返回:
{{"matches": [{{"new": "N1", "eval": 3, "reason": "都关于垃圾桶不足"}}, ...], "unmatched": ["N2", ...]}}

unmatched 是没有匹配到任何已评估反馈的新关键词(代表新问题)。"""

    result = llm_chat_json(prompt, temperature=0.1, max_tokens=800)
    if not isinstance(result, dict):
        return None

    # 解析成 {new_keyword: [evaluated_item_ids]}
    matches = {}
    for m in result.get('matches', []):
        new_label = m.get('new', '')
        eval_label = m.get('eval')
        # 解析 N序号 -> 实际关键词
        new_idx = None
        if isinstance(new_label, str) and new_label.startswith('N'):
            try:
                new_idx = int(new_label[1:])
            except ValueError:
                pass
        new_kw = new_kw_map.get(new_idx)
        if new_kw is None:
            continue
        # 解析数字序号 -> evaluated item id
        eval_id = None
        if isinstance(eval_label, int):
            eval_id = eval_id_map.get(eval_label)
        elif isinstance(eval_label, str) and eval_label.isdigit():
            eval_id = eval_id_map.get(int(eval_label))
        if eval_id is None:
            continue
        matches.setdefault(new_kw, []).append(eval_id)

    return matches


def _llm_round2_evaluate(
    new_item: FeedbackItem,
    matched_keyword: str,
    candidate_items: list[FeedbackItem],
) -> dict | None:
    """第 2 轮: 把新报单 + 候选已评估报单详情发给 LLM,让它决定是否合并。

    Returns:
        {action: "merge"/"new", merge_into_id: int, summary: str, extracted_content: str}
        失败返回 None。
    """
    candidate_lines = []
    for c in candidate_items:
        candidate_lines.append(
            f"#{c.id} (关键词: {_parse_keywords(c.keywords)}): {c.description}"
        )

    prompt = f"""你是景区反馈分析助手。判断新报单是否应合并到某个已有报单。

匹配关键词: "{matched_keyword}"

新报单:
{new_item.description}

候选已有报单:
{chr(10).join(candidate_lines)}

如果新报单确实是同一问题(同一关键词指向的重复反馈),选择合并到最早的候选报单。
从新报单描述中提取与该关键词相关的补充信息。

用JSON格式返回:
{{"action": "merge", "merge_into_id": 3, "summary": "对合并后问题的综合摘要(一句话)", "extracted_content": "从新报单提取的补充信息"}}

如果是新问题(不重复),返回:
{{"action": "new"}}"""

    result = llm_chat_json(prompt, temperature=0.2, max_tokens=400)
    if not isinstance(result, dict):
        return None
    return result


def _merge_into_recycle_bin(session: Session, item: FeedbackItem, target: FeedbackItem,
                            reason: str, extracted_content: str = ''):
    """把 item 合并到 target: item 移入回收站,target 得到补充。"""
    # 防御:禁止自合并(并发或异常时可能出现 target==item,改判为新锚点)
    if target.id == item.id:
        logger.warning('检测到自合并企图(报单#%d -> 自身),改标记为新锚点', item.id)
        _mark_as_evaluated(session, item)
        return

    # 防御:已存在该 original_id 的回收记录则跳过重复归档(幂等)
    exists = session.query(FeedbackRecycleBin).filter(
        FeedbackRecycleBin.original_id == item.id
    ).first()
    if exists:
        logger.info('报单#%d 已有回收记录,跳过重复归档', item.id)
        item.status = 'merged'
        item.evaluated = True
        item.merged_into_id = target.id
        session.commit()
        return

    # 1. 迁移到回收站
    recycle = FeedbackRecycleBin(
        original_id=item.id,
        type=item.type,
        priority=item.priority,
        scenic_spot=item.scenic_spot,
        description=item.description,
        keywords=item.keywords,
        image_paths=item.image_paths,
        merged_into_id=target.id,
        merge_reason=reason,
        contact_info=item.contact_info,
        created_at=item.created_at,
    )
    session.add(recycle)

    # 2. target 得到补充
    target.duplicate_count += 1
    # 关键词保持单标签(评估时已收敛),不累加被合并报单的关键词
    if extracted_content:
        # 把补充信息追加到描述
        target.description = target.description.rstrip() + f"\n[补充#{item.id}] {extracted_content}"
    # 按数量调整优先级
    new_prio = _count_to_priority(target.duplicate_count)
    if new_prio:
        target.priority = new_prio

    # 3. item 标记为 merged,移出主查询(status='merged')
    item.status = 'merged'
    item.evaluated = True
    item.merged_into_id = target.id

    session.commit()
    logger.info('报单#%d 合并到 #%d (原因: %s)', item.id, target.id, reason)


def _mark_as_evaluated(session: Session, item: FeedbackItem, primary_keyword: str | None = None):
    """标记报单为已评估,成为新的锚点供未来匹配。

    评估后单关键词:primary_keyword 指定时用它(通常由 LLM 从多候选中选出核心原因),
    否则原子化后取第一个(规则降级路径用,不调 LLM)。
    """
    item.evaluated = True
    atoms = _atomize_keywords(_parse_keywords(item.keywords))
    primary = primary_keyword or (atoms[0] if atoms else None)
    if primary:
        item.keywords = json.dumps([primary])
    # 单条报单,默认 group_id = 自己的 id(字符串)
    item.group_id = str(item.id)
    session.commit()


def _empty_result(method: str = 'llm', error: str | None = None) -> dict:
    return {
        'evaluated_count': 0, 'merged_count': 0,
        'new_groups': 0, 'priority_upgrades': 0,
        'method': method, 'error': error,
    }


# 全局整合锁:同一进程内同一时刻只允许一个整合任务运行。
# 快速提交多条报单时,每次 create 都会后台触发 integrate,若无锁会
# 多个任务重叠处理同一条 pending,导致重复归档 / 自合并等竞态 bug。
_integrate_lock = threading.Lock()


def integrate_feedback(session: Session) -> dict:
    """主入口:执行报单智能整合(并发安全)。

    用全局锁串行化。若已有任务在运行,本次直接跳过(method='skipped')——
    运行中的任务会在 drain 循环中把新到达的 pending 也处理掉,不会漏。
    """
    if not _integrate_lock.acquire(blocking=False):
        logger.info('已有整合任务在运行,跳过本次触发')
        return _empty_result(method='skipped', error='另一整合任务进行中')

    try:
        total = _empty_result()
        # drain 循环:持续处理直到没有 pending(覆盖运行期间新到达的报单)
        for _ in range(200):  # 安全上限,防异常死循环
            pending = session.query(FeedbackItem).filter(
                FeedbackItem.evaluated == False,  # noqa: E712
                FeedbackItem.status != 'merged',
            ).order_by(FeedbackItem.created_at.asc()).all()
            if not pending:
                break
            try:
                r = _integrate_with_llm(session, pending)
            except Exception as exc:
                logger.warning('LLM 整合失败,降级规则版: %s', exc)
                r = _integrate_with_rules(session, pending)
            # 累加统计
            for k in ('evaluated_count', 'merged_count', 'new_groups', 'priority_upgrades'):
                total[k] += r.get(k, 0)
            if r.get('method') == 'rule':
                total['method'] = 'rule'
            if r.get('error') and not total['error']:
                total['error'] = r['error']
        return total
    finally:
        _integrate_lock.release()


def _integrate_with_llm(session: Session, pending: list[FeedbackItem]) -> dict:
    """LLM 路径整合。"""
    merged_count = 0
    evaluated_count = 0
    new_groups = 0
    priority_upgrades = 0

    for item in pending:
        # 1. 确保有关键词(没有就 LLM 提取)
        kws = _parse_keywords(item.keywords)
        if not kws:
            kws = _llm_extract_keywords(item.description)
            item.keywords = json.dumps(kws)
            session.commit()

        if not kws:
            # 无关键词也无法提取,直接标评估
            _mark_as_evaluated(session, item)
            evaluated_count += 1
            continue

        # 取当前已评估锚点(每次循环重新查,因为可能新增)
        current_evaluated = session.query(FeedbackItem).filter(
            FeedbackItem.evaluated == True,  # noqa: E712
            FeedbackItem.status != 'merged',
        ).all()

        # 2. 第 1 轮: 关键词匹配
        matches = _llm_round1_match(kws, current_evaluated)

        if matches is None:
            # LLM 失败,降级单条处理
            _mark_as_evaluated(session, item)
            evaluated_count += 1
            new_groups += 1
            continue

        # 3. 处理匹配结果
        any_merged = False
        for kw, eval_ids in matches.items():
            if not eval_ids:
                continue
            # 取候选报单(按 id 升序,最早的优先)
            candidates = session.query(FeedbackItem).filter(
                FeedbackItem.id.in_(eval_ids),
                FeedbackItem.status != 'merged',
            ).order_by(FeedbackItem.id.asc()).all()

            if not candidates:
                continue

            # 4. 第 2 轮: 详情评估
            verdict = _llm_round2_evaluate(item, kw, candidates)
            if verdict and verdict.get('action') == 'merge':
                merge_into_id = verdict.get('merge_into_id')
                target = next((c for c in candidates if c.id == merge_into_id), candidates[0])
                before_prio = target.priority
                _merge_into_recycle_bin(
                    session, item, target,
                    reason=f"LLM判定与#{target.id}重复 (关键词: {kw})",
                    extracted_content=verdict.get('extracted_content', ''),
                )
                merged_count += 1
                if target.priority != before_prio:
                    priority_upgrades += 1
                # 更新组摘要
                if verdict.get('summary'):
                    target.group_summary = verdict['summary']
                    session.commit()
                any_merged = True
                break  # 已合并,处理下一条 pending

        if not any_merged:
            # 没有匹配到,标为新问题
            atoms = _atomize_keywords(kws)
            if len(atoms) >= 2:
                # 多候选:让 LLM 选最核心的原因(具体可执行优先,避开空泛描述)
                primary = _llm_pick_primary_keyword(item.description, atoms) or atoms[0]
            else:
                primary = atoms[0] if atoms else None
            _mark_as_evaluated(session, item, primary_keyword=primary)
            evaluated_count += 1
            new_groups += 1

    return {
        'evaluated_count': evaluated_count,
        'merged_count': merged_count,
        'new_groups': new_groups,
        'priority_upgrades': priority_upgrades,
        'method': 'llm',
        'error': None,
    }


# ============================================================
# 规则降级路径
# ============================================================

def _integrate_with_rules(session: Session, pending: list[FeedbackItem]) -> dict:
    """规则版降级:按 (scenic_spot, type) 签名分组,无 LLM。"""
    # 收集所有未 merged 报单(含已评估)按签名分组
    all_items = session.query(FeedbackItem).filter(
        FeedbackItem.status != 'merged',
    ).order_by(FeedbackItem.id.asc()).all()

    groups: dict[tuple, list[FeedbackItem]] = {}
    for it in all_items:
        sig = (it.scenic_spot or '', it.type)
        groups.setdefault(sig, []).append(it)

    merged_count = 0
    evaluated_count = 0
    new_groups = 0
    priority_upgrades = 0

    for sig, members in groups.items():
        if len(members) < 2:
            # 单条,标评估
            for m in members:
                if not m.evaluated:
                    _mark_as_evaluated(session, m)
                    evaluated_count += 1
            continue
        # 多条同签名:最早的为锚点,其余合并
        members.sort(key=lambda x: x.id)
        anchor = members[0]
        if not anchor.evaluated:
            _mark_as_evaluated(session, anchor)
            evaluated_count += 1
            new_groups += 1
        anchor.group_id = str(anchor.id)
        session.commit()

        for m in members[1:]:
            if m.status == 'merged':
                continue
            before_prio = anchor.priority
            _merge_into_recycle_bin(
                session, m, anchor,
                reason=f"规则匹配:同景点同类型 ({sig})",
            )
            merged_count += 1
            if anchor.priority != before_prio:
                priority_upgrades += 1
        # 按数量调整优先级
        new_prio = _count_to_priority(anchor.duplicate_count)
        if new_prio:
            anchor.priority = new_prio
            session.commit()

    return {
        'evaluated_count': evaluated_count,
        'merged_count': merged_count,
        'new_groups': new_groups,
        'priority_upgrades': priority_upgrades,
        'method': 'rule',
        'error': 'LLM 不可用,使用规则版降级',
    }
