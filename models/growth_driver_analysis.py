import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional

# 驱动因素配置（五大类别）
DRIVER_CONFIG = {
    "汰品影响": {
        "name": "汰品影响",
        "icon": "🗑️",
        "category": "🗑️ 汰品淘汰",
        "color": "#f44336",
        "description": "淘汰滞销品带来的销售影响",
        "positive_advice": "汰品策略效果积极，释放货架空间给高潜力商品",
        "negative_advice": "汰品导致销售流失，需重新评估汰品标准，延长观察期",
        "action_items": [
            "评估销量排名后10%的商品",
            "连续30天销量<5件的商品标记为滞销",
            "汰品前进行1周促销清仓测试"
        ]
    },
    "新品影响": {
        "name": "新品影响",
        "icon": "🆕",
        "category": "🍱 新品引入",
        "color": "#4caf50",
        "description": "新上市商品带来的销售增量",
        "positive_advice": "新品贡献正向增长，建议持续引入同类风格新品",
        "negative_advice": "新品贡献不足，需优化选品策略或加强新品推广",
        "action_items": [
            "引入2-3款潜力新品进行测试",
            "新品上架首周给予黄金陈列位",
            "新品上市配合试吃/买赠活动"
        ]
    },
    "老品价格变动影响": {
        "name": "价格影响",
        "icon": "💰",
        "category": "💰 价格优化",
        "color": "#ff9800",
        "description": "老品价格调整带来的销售变化",
        "positive_advice": "价格策略有效，可考虑扩大调价范围",
        "negative_advice": "价格调整效果不佳，建议优化定价策略或恢复原价",
        "action_items": [
            "敏感商品降价5-8%测试弹性",
            "非敏感商品维持原价",
            "高毛利商品采用捆绑销售"
        ]
    },
    "老品销量影响": {
        "name": "销量影响",
        "icon": "📊",
        "category": "🎉 促销/时段",
        "color": "#2196f3",
        "description": "老品自身销量波动的销售影响（不含价格因素）",
        "positive_advice": "销量增长良好，保持现有运营策略",
        "negative_advice": "销量下滑明显，建议加强促销活动或优化陈列",
        "action_items": [
            "推出限时折扣/买赠活动",
            "早餐/午餐/夜宵时段差异化促销",
            "热销商品做组合套餐"
        ]
    },
    "老品消费升级影响": {
        "name": "消费升级影响",
        "icon": "📈",
        "category": "📦 陈列/季节性",
        "color": "#9c27b0",
        "description": "顾客消费升级带来的销售影响（客单价/品类转移）",
        "positive_advice": "消费升级趋势明显，增加中高端商品占比",
        "negative_advice": "消费升级趋势不明显，维持现有价格带",
        "action_items": [
            "增加5-10%中高端商品进行测试",
            "高客单商品陈列在黄金位置",
            "推出品质升级版替换低端款"
        ]
    }
}

DRIVER_FIELDS = ["汰品影响", "新品影响", "老品价格变动影响", "老品销量影响", "老品消费升级影响"]


def load_driver_data() -> pd.DataFrame:
    """加载驱动因素数据"""
    data = pd.read_csv('data/driver_data.csv')
    return data


def load_product_list() -> pd.DataFrame:
    """加载商品清单（新品/调价商品）"""
    data = pd.DataFrame({
        '品类名称': ['熟食&饮品', '熟食&饮品', '熟食&饮品', '烘焙糕点', '烘焙糕点', '熟食&饮品', '熟食&饮品', '烘焙糕点'],
        '商品名称': ['厚乳拿铁', '生椰丝绒拿铁', '冰吸黑咖', '生巧熔岩蛋糕', '海盐芝士卷', '经典美式', '拿铁咖啡', '原味吐司'],
        '商品类型': ['新品', '新品', '新品', '新品', '新品', '调价', '调价', '调价'],
        '当前售价': [None, None, None, None, None, 15.0, 18.0, 12.0],
        '建议售价': [18.0, 19.0, 15.0, 22.0, 16.0, 12.0, 16.0, 10.0],
        '毛利率': [45, 46, 42, 48, 44, 35, 36, 33],
        '推荐理由': [
            '竞品热销款，咖啡风味升级',
            '小红书爆款，年轻客群偏好',
            '夏季清凉饮品补充',
            '甜品站热销款，客群匹配',
            '网红单品，适合下午茶',
            '价格敏感型商品，降价冲量',
            '对标竞品价格，提升竞争力',
            '早餐刚需，降价扩大份额'
        ],
        '预期效果': [
            '月销预计300杯',
            '月销预计280杯',
            '月销预计350杯',
            '月销预计200个',
            '月销预计250个',
            '预计销量+25%',
            '预计销量+20%',
            '预计销量+30%'
        ]
    })
    return data


def load_shelf_position_data() -> pd.DataFrame:
    """加载陈列位置建议数据"""
    data = pd.DataFrame({
        '品类名称': ['烘焙糕点', '烘焙糕点', '熟食&饮品', '熟食&饮品', '熟食&饮品', '方便食品'],
        '商品名称': ['生巧熔岩蛋糕', '海盐芝士卷', '厚乳拿铁', '经典美式', '拿铁咖啡', '自热小火锅'],
        '当前陈列位置': ['未上架', '未上架', '未上架', 'C区底层', 'B区中层', 'D区底层'],
        '建议陈列位置': ['收银台端架', 'B区黄金层', 'A区主通道', 'A区黄金层', 'A区黄金层', '门口端架'],
        '调整理由': [
            '网红爆品，促进冲动消费',
            '下午茶场景，搭配饮品销售',
            '新品主打，高曝光位置',
            '高频商品，提升购买便利性',
            '核心单品，强化品牌形象',
            '季节性爆品，吸引进店'
        ],
        '预期效果': [
            '月销预计200个',
            '连带率+15%',
            '月销预计300杯',
            '销量+25%',
            '销量+20%',
            '销量+40%'
        ]
    })
    return data


def create_waterfall_chart(category_data: pd.Series) -> go.Figure:
    """
    创建瀑布图
    参数:
        category_data: 该大类的数据行
    返回:
        plotly瀑布图
    """
    category_name = category_data['大类名称']
    start_value = category_data['上期销售额']
    end_value = category_data['本期销售额']
    
    # 驱动因素值
    drivers = {
        "汰品影响": category_data['汰品影响'],
        "新品影响": category_data['新品影响'],
        "老品价格变动影响": category_data['老品价格变动影响'],
        "老品销量影响": category_data['老品销量影响'],
        "老品消费升级影响": category_data['老品消费升级影响']
    }
    
    # 构建瀑布图数据（固定顺序）
    labels = ["同期销售额"]
    values = [100]  # 基准设为100%

    # 累计百分比
    cumulative = 100

    # 固定顺序：汰品影响、新品影响、老品价格变动、老品销量、老品消费升级
    driver_order = ["汰品影响", "新品影响", "老品价格变动影响", "老品销量影响", "老品消费升级影响"]

    # 添加各因素子项
    for driver_name in driver_order:
        impact = drivers[driver_name] * 100
        labels.append(driver_name)
        values.append(impact)
        cumulative += impact

    # 添加本年销售额
    labels.append("本期销售额")
    values.append(cumulative - 100)  # 计算差额

    # 创建瀑布图（使用百分比）
    fig = go.Figure(go.Waterfall(
        name="驱动因素分解",
        orientation="v",
        measure=["absolute"] + ["relative"] * (len(values) - 2) + ["total"],
        x=labels,
        y=values,
        textposition="outside",
        text=[f"{v:+.1f}%" if i > 0 else f"{v:.0f}%" for i, v in enumerate(values)],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#4caf50"}},
        decreasing={"marker": {"color": "#f44336"}},
        totals={"marker": {"color": "#2A5C9A"}}
    ))

    # 计算增长率
    growth_rate = (end_value - start_value) / start_value * 100

    # 根据增长率设置箭头颜色和方向
    if growth_rate > 0:
        arrow_color = "#4caf50"  # 绿色
        arrow_symbol = "↑"
    elif growth_rate < 0:
        arrow_color = "#f44336"  # 红色
        arrow_symbol = "↓"
    else:
        arrow_color = "#666666"  # 灰色
        arrow_symbol = "→"

    fig.update_layout(
        title=dict(
            text=f"<span style='font-size:16px'>同期: ¥{start_value:.1f} → 本期: ¥{end_value:.1f}</span><br><span style='font-size:16px; color:{arrow_color}'>增长率: {growth_rate:+.2f}% {arrow_symbol}</span>",
            font=dict(size=14)
        ),
        yaxis_title="影响百分比（%）",
        xaxis_title="",
        height=500,
        template="plotly_white",
        showlegend=False
    )
    
    return fig


def analyze_category_drivers(category_data: pd.Series) -> Dict[str, Any]:
    """
    分析单个大类的驱动因素
    返回:
        分析结果字典
    """
    category_name = category_data['大类名称']
    growth_rate = category_data['销售额增长率']
    current_sales = category_data['本期销售额']
    prev_sales = category_data['上期销售额']
    
    # 整体表现评级
    if growth_rate > 10:
        performance = "优秀"
        performance_icon = "🟢"
    elif growth_rate > 0:
        performance = "良好"
        performance_icon = "🟡"
    elif growth_rate > -10:
        performance = "一般"
        performance_icon = "🟠"
    else:
        performance = "较差"
        performance_icon = "🔴"
    
    # 分析各驱动因素
    drivers = []
    for field in DRIVER_FIELDS:
        value = category_data[field]
        config = DRIVER_CONFIG.get(field, {})
        
        drivers.append({
            "field": field,
            "name": config.get("name", field),
            "icon": config.get("icon", "📌"),
            "value": value,
            "is_positive": value > 0,
            "abs_value": abs(value)
        })
    
    # 按绝对值排序
    drivers_sorted = sorted(drivers, key=lambda x: x['abs_value'], reverse=True)
    
    return {
        "category_name": category_name,
        "current_sales": current_sales,
        "prev_sales": prev_sales,
        "growth_rate": growth_rate,
        "performance": performance,
        "performance_icon": performance_icon,
        "drivers": drivers_sorted
    }


def get_waterfall_analysis(category_data: pd.Series) -> Dict[str, Any]:
    """
    生成瀑布图下方的拆解分析
    """
    category_name = category_data['大类名称']
    start_value = category_data['上期销售额']
    end_value = category_data['本期销售额']
    growth_rate = category_data['销售额增长率']
    
    drivers = {
        "汰品影响": category_data['汰品影响'],
        "新品影响": category_data['新品影响'],
        "老品价格变动影响": category_data['老品价格变动影响'],
        "老品销量影响": category_data['老品销量影响'],
        "老品消费升级影响": category_data['老品消费升级影响']
    }
    
    # 计算品类结构调整影响（汰品+新品）
    category_structure_impact = drivers["汰品影响"] + drivers["新品影响"]
    
    # 计算老品影响（价格+销量+消费升级）
    old_product_impact = drivers["老品价格变动影响"] + drivers["老品销量影响"] + drivers["老品消费升级影响"]
    
    # 计算各子项影响
    sub_impacts = {
        "汰品影响": drivers["汰品影响"],
        "新品影响": drivers["新品影响"],
        "老品价格变动影响": drivers["老品价格变动影响"],
        "老品销量影响": drivers["老品销量影响"],
        "老品消费升级影响": drivers["老品消费升级影响"]
    }
    
    # 找出影响最大的子项
    max_impact_sub = max(sub_impacts.items(), key=lambda x: abs(x[1])) if sub_impacts else None
    
    return {
        "category_name": category_name,
        "start_value": start_value,
        "end_value": end_value,
        "growth_rate": growth_rate,
        "category_structure_impact": category_structure_impact,
        "old_product_impact": old_product_impact,
        "sub_impacts": sub_impacts,
        "max_impact_sub": (max_impact_sub[0], max_impact_sub[1]) if max_impact_sub else None,
        "total_impact": category_structure_impact + old_product_impact
    }