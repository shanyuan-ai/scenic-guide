# measureapp/utils/sentiment.py
def analyze_sentiment(text):
    """
    简单的情感分析
    返回 0-1 之间的分数
    """
    if not text:
        return 0.5

    # 简单关键词匹配
    positive_keywords = ['谢谢', '感谢', '不错', '很好', '喜欢', '棒', '赞', '好', '开心']
    negative_keywords = ['差', '坏', '垃圾', '失望', '不行', '不好', '差评', '讨厌']

    score = 0.5
    for kw in positive_keywords:
        if kw in text:
            score += 0.1
    for kw in negative_keywords:
        if kw in text:
            score -= 0.1

    return max(0, min(1, round(score, 2)))