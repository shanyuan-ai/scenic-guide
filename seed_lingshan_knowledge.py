"""灵山胜境知识库种子数据导入脚本(FastAPI/SQLAlchemy 版)。

用法:
    python seed_lingshan_knowledge.py

导入后自动重建向量索引。如需下载模型先运行 download_model.py。
"""
from app.common.db import init_db, SessionLocal
from app.tools.rag.models import KnowledgeItem
from app.tools.rag.vector_service import vector_service


def seed():
    init_db()

    items = [
        {
            'title': '灵山胜境概览（四大主体景观与“四相成道”轴线）',
            'category': 'history',
            'content': (
                '部分资料将灵山胜境的核心看点概括为四大主体景观：灵山大佛、九龙灌浴、灵山梵宫、五印坛城。也有资料从空间叙事角度概括为在景区中轴线上展示佛陀“出生、降魔、说法、涅槃”四相成道的故事线。\n\n'
                '提示：景区项目、演出与开放区域可能会调整，实际以景区当日公告为准。\n\n'
                '来源：\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
                '- http://wx.bendibao.com/tour/20211012/57204.shtm\n'
            ),
        },
        {
            'title': '灵山大佛（简介与手印含义）',
            'category': 'nature',
            'content': (
                '灵山大佛常被介绍为释迦牟尼佛露天青铜佛像。部分资料对其手势解释为：右手“施无畏印”、左手“与愿印”，寓意除却众生痛苦、给予众生欢乐。\n\n'
                '提示：尺寸、建造细节以景区官方说明为准。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
            ),
        },
        {
            'title': '“抱佛脚”参观提示（大佛脚下参拜与电梯）',
            'category': 'faq',
            'content': (
                '部分介绍提到：在大佛脚下区域可进行“抱佛脚/亲近大佛”的参观体验，并提及可通过电梯等方式抵达相应位置（具体开放与动线以现场为准）。\n\n'
                '来源：\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
                '- https://www.wuxi.gov.cn/doc/2025/07/20/4615469.shtml\n'
            ),
        },
        {
            'title': '天下第一掌（“施无畏印”与“摸佛手”习俗）',
            'category': 'nature',
            'content': (
                '“天下第一掌”常被介绍为灵山大佛右手的复制件，形状与大小与大佛右手一致。相关介绍中提到其印相为“施无畏印”，并流传“摸摸佛手，增福添寿；抱抱佛脚，平安到老”等说法。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
            ),
        },
        {
            'title': '百子戏弥勒（艺术形象与寓意）',
            'category': 'nature',
            'content': (
                '“百子戏弥勒”在资料中被描述为大型青铜艺术作品：弥勒斜倚而卧、笑容可掬，身上塑有一百个嬉戏顽童形象，用艺术化方式表现弥勒“慈颜常笑、大肚能容”的意象。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
            ),
        },
        {
            'title': '祥符禅寺（沿革概览：唐-宋赐额-近现代重建）',
            'category': 'history',
            'content': (
                '部分资料介绍：祥符禅寺始建于唐贞观年间；北宋大中祥符年间曾由真宗诏改为“祥符禅院”，后又定名为“祥符禅寺”。资料还提到1938年寺院受损、1994年重建等信息。\n\n'
                '提示：历史细节请以权威史志或寺院/景区官方说明为准。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
            ),
        },
        {
            'title': '杏坛广场（古银杏与拍照打卡）',
            'category': 'nature',
            'content': (
                '资料中提到：杏坛广场名称与大佛脚下的古银杏树相关，并作为景区古树名木与历史遗存的代表。相关描述称其“传植于唐贞观年间”等。\n\n'
                '提示：古树树龄与历史传说类信息，建议以官方科普牌示为准。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
            ),
        },
        {
            'title': '九龙灌浴（演出内容与观演提示）',
            'category': 'nature',
            'content': (
                '“九龙灌浴”通常被介绍为露天实景/音乐动态群雕演出，通过莲花开启、太子佛像升起、九龙喷水等形式演绎佛陀诞生故事；部分资料还提到结束时会有“八功德水”等内容描述。\n\n'
                '提示：演出场次与时间会调整，以景区当日公告为准。\n\n'
                '来源：\n'
                '- http://wx.bendibao.com/tour/2022825/67555.shtm\n'
                '- http://wx.bendibao.com/tour/2022825/67553.shtm\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
            ),
        },
        {
            'title': '灵山梵宫（建筑风格与馆内看点）',
            'category': 'nature',
            'content': (
                '资料中常将梵宫描述为融合佛教石窟艺术与传统佛教建筑元素的宫殿式建筑，内部可见木雕、壁画、琉璃等装饰与展陈（具体展项以现场为准）。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
            ),
        },
        {
            'title': '曼飞龙塔（南传佛教建筑风格）',
            'category': 'nature',
            'content': (
                '资料介绍：曼飞龙塔通体雪白，常被作为南传佛教建筑风格的代表性景观之一；部分描述提到其由主塔与若干小塔组合成群塔形态。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
            ),
        },
        {
            'title': '五印坛城（藏传佛教建筑与文化体验）',
            'category': 'nature',
            'content': (
                '资料中将五印坛城描述为藏传佛教建筑风格的文化艺术空间，提到内部装饰可能包含彩绘、木雕、唐卡等传统工艺元素，并与灵山大佛、梵宫、曼飞龙塔共同呈现佛教多元建筑文化。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
                '- http://wx.bendibao.com/tour/2022825/67555.shtm\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
            ),
        },
        {
            'title': '灵山胜境开放时间（夏令时/冬令时）',
            'category': 'faq',
            'content': (
                '资料中常见说法：灵山胜境景区夏令时入园时间约为 7:00-17:30，冬令时约为 7:00-17:00（不同信息源的口径可能略有差异）。\n\n'
                '提示：具体以景区当日公告/官方渠道为准。\n\n'
                '来源：\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
                '- http://wx.bendibao.com/tour/2022825/67553.shtm\n'
            ),
        },
        {
            'title': '梵宫/珍宝馆/五印坛城开放时间（参考）',
            'category': 'faq',
            'content': (
                '无锡本地宝的“持续更新”页面给出参考口径：梵宫约 9:00-17:30；梵宫珍宝馆约 9:30-16:30；五印坛城约 9:00-17:30。\n\n'
                '提示：具体以景区当日公告为准。\n\n'
                '来源：\n'
                '- http://wx.bendibao.com/tour/2022825/67553.shtm\n'
            ),
        },
        {
            'title': '九龙灌浴与吉祥颂等演出时间（参考）',
            'category': 'faq',
            'content': (
                '无锡本地宝“持续更新”页面提供参考场次（可能随节假日/运营调整）：\n'
                '1) 《吉祥颂》：平日约 10:35、11:30、14:00；周末增加 16:00。\n'
                '2) 九龙灌浴：平日约 10:00、11:30、14:45、16:40；周末增加 13:00。\n'
                '3) 梵宫文化体验之旅：平日约 10:00、11:00、12:00、13:30、15:30；周末增加 14:30。\n\n'
                '提示：具体以景区当日公告为准。\n\n'
                '来源：\n'
                '- http://wx.bendibao.com/tour/2022825/67553.shtm\n'
            ),
        },
        {
            'title': '灵山胜境交通（公交与乐游线）',
            'category': 'faq',
            'content': (
                '资料中常见公共交通建议：无锡火车站可乘 88/89 路直达；也有“乐游2号线”等旅游巴士/线路信息。不同线路票价与站点可能会调整。\n\n'
                '来源：\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
                '- http://wx.bendibao.com/tour/2022825/67559.shtm\n'
            ),
        },
        {
            'title': '灵山胜境交通（自驾路线参考：上海/南京/常州）',
            'category': 'faq',
            'content': (
                '无锡本地宝页面给出多条自驾参考线路（例如上海经沪宁高速、无锡互通、锡宜高速、马山出口等；南京经沪宁高速至无锡相关出口；常州经武进等地）。\n\n'
                '提示：线路以导航与实时路况为准。\n\n'
                '来源：\n'
                '- http://wx.bendibao.com/tour/2022825/67559.shtm\n'
            ),
        },
        {
            'title': '停车与园内交通（参考）',
            'category': 'faq',
            'content': (
                '资料中提到停车收费会按车型与节假日调整；园内观光车也可能有单独收费及套票信息。\n\n'
                '提示：收费以景区现场/官方渠道为准。\n\n'
                '来源：\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
                '- http://wx.bendibao.com/tour/2022825/67559.shtm\n'
            ),
        },
        {
            'title': '灵山胜境门票与优惠政策（参考汇总）',
            'category': 'faq',
            'content': (
                '无锡本地宝页面整理了免票/半票等人群范围（如儿童、老人、学生、军人、残障人士等）及部分注意事项，并提示《吉祥颂》演出票可能需要另购。\n\n'
                '提示：票价与优惠政策会调整，以景区官方政策为准。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/67554.shtm\n'
            ),
        },
        {
            'title': '游览路线（官方步行推荐与备选路线参考）',
            'category': 'route',
            'content': (
                '游记攻略页面提供了“步行官方推荐路线”示例（南门→佛足坛→九龙灌浴→…→灵山大佛→梵宫→曼飞龙塔→五印坛城→出口），并给出人多时的备选走法（如先去五印坛城/梵宫再回到大佛区域等）。\n\n'
                '提示：具体动线以景区导览与现场指引为准。\n\n'
                '来源：\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
            ),
        },
        {
            'title': '无锡本地宝路线推荐（精华/休闲/祈福线路）',
            'category': 'route',
            'content': (
                '无锡本地宝给出多条路线口径：精华路线（大照壁-五明桥-胜境楼门-洗心池-佛足坛-九龙灌浴-梵宫-阿育王柱-天下第一掌-百子戏弥勒-祥符禅寺-灵山大佛等）、休闲路线与祈福线等。\n\n'
                '来源：\n'
                '- http://wx.bendibao.com/tour/2022825/67555.shtm\n'
            ),
        },
        {
            'title': '马山景区规划要点（“一环双核串六区”与灵山胜境游览区）',
            'category': 'history',
            'content': (
                '无锡市自然资源和规划局发布信息提到《太湖风景名胜区马山景区详细规划》获批，并提出“一环双核串六区”的空间结构：一环为环岛风光游线；双核包括“灵山佛文化展示核”和“拈花湾禅文化体验核”；六区中包含“灵山胜境游览区”等。\n\n'
                '来源：\n'
                '- https://zrzy.wuxi.gov.cn/doc/2026/01/15/4725134.shtml\n'
            ),
        },
        {
            'title': '春游季活动信息（灵山胜境/拈花湾等推荐）',
            'category': 'history',
            'content': (
                '无锡市文化广电和旅游局发布的活动信息提到，相关活动在灵山胜境举办，并对灵山胜境、拈花湾、龙头渚等进行推介（活动内容与合作信息可能用于文旅宣传）。\n\n'
                '来源：\n'
                '- https://crtt.wuxi.gov.cn/doc/2025/03/04/4512111.shtml\n'
            ),
        },
        {
            'title': '客流与活动案例（无锡政府报道：灵山胜境周末客流）',
            'category': 'history',
            'content': (
                '无锡市政府网站报道中提到：某周末灵山胜境景区截至中午入园游客超过 1.8 万人次，且景区相关负责人提到周末预订游客规模与来源地占比等，并列举了如“梵境双辉”艺术对话展、XR体验等活动。\n\n'
                '提示：该类数据为报道时点信息，仅供了解景区热度，不代表日常水平。\n\n'
                '来源：\n'
                '- https://www.wuxi.gov.cn/doc/2025/07/20/4615469.shtml\n'
            ),
        },
        {
            'title': '行李寄存与小程序（参考）',
            'category': 'faq',
            'content': (
                '游记攻略页面提到：景区入口服务中心可提供免费行李寄存；并提到可通过小程序预约部分演出/查看地图与演出时间等。\n\n'
                '提示：服务点位与规则可能调整。\n\n'
                '来源：\n'
                '- http://linshan.yywxc.com/tpl/yjgl/yjgl_24.html\n'
            ),
        },
        {
            'title': '祈福线路要点（摸佛手/礼佛/抱佛脚等）',
            'category': 'route',
            'content': (
                '无锡本地宝“祈福路线图+景点介绍”页面给出一条祈福向导览：包括天下第一掌（摸佛手）、百子戏弥勒、祥符禅寺、杏坛广场、灵山大佛等，并包含部分习俗类表达。\n\n'
                '来源：\n'
                '- https://m.wx.bendibao.com/tour/75100.shtm\n'
            ),
        },
    ]

    session = SessionLocal()
    created = 0
    updated = 0
    try:
        for it in items:
            existing = session.query(KnowledgeItem).filter_by(title=it['title']).first()
            if existing:
                existing.content = it['content']
                existing.category = it['category']
                existing.is_indexed = True
                updated += 1
            else:
                session.add(KnowledgeItem(
                    title=it['title'],
                    content=it['content'],
                    category=it['category'],
                    is_indexed=True,
                ))
                created += 1
        session.commit()
    finally:
        session.close()

    indexed_doc_count = vector_service.sync_all_knowledge()
    print(f'seeded created={created} updated={updated} indexed_doc_count={indexed_doc_count}')


if __name__ == '__main__':
    seed()
