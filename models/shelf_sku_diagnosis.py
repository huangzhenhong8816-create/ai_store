import pandas as pd
import numpy as np
from typing import List, Dict, Any

def calculate_target_sku_by_category(category_data: pd.DataFrame, current_sku: int, pe_level: str) -> int:
    """
    根据品类数据计算目标SKU数
    参数:
        category_data: 该品类的销售数据
        current_sku: 当前SKU数
        pe_level: 坪效等级 (high/medium/low)
    返回:
        目标SKU数
    """
    # 基准：每货架组建议40-50个SKU
    base_target = 20  # 中位数
    
    # 根据坪效调整
    if pe_level == "high":
        target = int(base_target * 1.1)  # 高效率可增加密度
    elif pe_level == "low":
        target = int(base_target * 0.85)  # 低效率降低密度
    else:
        target = base_target
    
    # 根据销量调整（销量高可适当增加SKU）
    avg_daily_sales = category_data['近30天销量'].sum() / 30 if not category_data.empty else 0
    if avg_daily_sales > 50:
        target = int(target * 1.05)
    elif avg_daily_sales < 10:
        target = int(target * 0.9)
    
    return max(10, min(target, 80))  # 限制在10-80之间


def analyze_category_sku_adjustment(category_data: pd.DataFrame, category_name: str, 
                                     current_sku: int, pe_level: str) -> Dict[str, Any]:
    """
    分析单个品类的SKU调整建议
    返回:
        {
            'category': 品类名称,
            'current_sku': 当前SKU数,
            'target_sku': 目标SKU数,
            'delta': 调整数量,
            'suggestion': 建议文本,
            'action_type': '增加'/'减少'/'维持'
        }
    """
    target_sku = calculate_target_sku_by_category(category_data, current_sku, pe_level)
    delta = target_sku - current_sku
    
    if delta > 0:
        action_type = "增加"
        suggestion = f"【{category_name}】增加{delta}个SKU"
    elif delta < 0:
        action_type = "减少"
        suggestion = f"【{category_name}】减少{abs(delta)}个SKU"
    else:
        action_type = "维持"
        suggestion = f"【{category_name}】维持现状"
    
    # 生成具体操作说明
    if abs(delta) > 0:
        if action_type == "增加":
            detail = f"从总部商品池中引入{delta}个高潜力{category_name}商品"
        else:
            detail = f"淘汰销量排名后{abs(delta)}位的{category_name}商品（建议参考近30天销量排序）"
    else:
        detail = f"优化现有{category_name}商品陈列位置，无需调整SKU数量"
    
    return {
        'category': category_name,
        'current_sku': current_sku,
        'target_sku': target_sku,
        'delta': delta,
        'suggestion': suggestion,
        'detail': detail,
        'action_type': action_type
    }


def diagnose_scene_with_multiple_categories(scene_data: pd.DataFrame) -> Dict[str, Any]:
    """
    诊断一个场景（可能包含多个品类）
    参数:
        scene_data: 该场景下所有品类的数据（包含单品级明细）
    返回:
        场景诊断结果字典
    """
    if scene_data.empty:
        return None
    
    # 基础信息
    store_id = scene_data['店号'].iloc[0]
    scene_code = scene_data['场景代码'].iloc[0]
    scene_name = scene_data['场景'].iloc[0]
    # 确保数值类型转换
    current_groups = pd.to_numeric(scene_data['货架组数'].iloc[0], errors='coerce')
    recommend_groups = pd.to_numeric(scene_data['推荐组数'].iloc[0], errors='coerce')

    
    # 计算场景整体指标
    total_sku = scene_data['SKU编码'].nunique() if 'SKU编码' in scene_data.columns else scene_data['sku数'].iloc[0]
    total_sales_qty = scene_data['近30天销量'].sum() if '近30天销量' in scene_data.columns else scene_data['近30天销量'].iloc[0]
    total_sales_amount = scene_data['近30天销售额'].sum() if '近30天销售额' in scene_data.columns else scene_data['近30天销售额'].iloc[0]
    
    # 计算场景坪效(总销售额/总sku数)
    pe = total_sales_amount / total_sku if total_sku > 0 else 0
    
    # 效率评级
    if pe >= 100:
        pe_level = "high"
        efficiency = "高"
    elif pe >= 40:
        pe_level = "medium"
        efficiency = "中"
    else:
        pe_level = "low"
        efficiency = "低"
    
    # 货架调整建议
    group_diff = current_groups - recommend_groups
    if group_diff > 0:
        shelf_suggestion = f"压缩至{recommend_groups}组（减少{group_diff}组）"
    elif group_diff < 0:
        shelf_suggestion = f"扩充至{recommend_groups}组（增加{abs(group_diff)}组）"
    else:
        if pe_level == "low":
            shelf_suggestion = f"保持{current_groups}组，需优化SKU结构"
        else:
            shelf_suggestion = f"保持{current_groups}组"
    
    # ========== 关键：按品类分析SKU调整建议 ==========
    category_analysis = []
    
    # 按大类分组分析
    if '大类' in scene_data.columns:
        for category, category_group in scene_data.groupby('大类'):
            current_cat_sku = category_group['SKU编码'].nunique() if 'SKU编码' in category_group.columns else category_group['sku数'].iloc[0]
            analysis = analyze_category_sku_adjustment(
                category_group, category, current_cat_sku, pe_level
            )
            category_analysis.append(analysis)
    else:
        # 如果没有大类字段，使用场景名称作为唯一品类
        current_cat_sku = total_sku
        analysis = analyze_category_sku_adjustment(scene_data, scene_name, current_cat_sku, pe_level)
        category_analysis.append(analysis)
    
    # 生成多行SKU调整建议文本（用换行符分隔）
    sku_suggestions_lines = [a['suggestion'] for a in category_analysis if a['action_type'] != '维持']
    if not sku_suggestions_lines:
        sku_suggestions_lines = [f"【{scene_name}】SKU结构合理，维持现状"]
    
    sku_suggestion_text = "\n".join(sku_suggestions_lines)
    
    # 生成详细操作说明（供展开查看）
    detail_lines = []
    for a in category_analysis:
        if a['action_type'] != '维持':
            detail_lines.append(f"• {a['suggestion']}：{a['detail']}")
    detail_text = "\n".join(detail_lines) if detail_lines else "无需调整"
    
    # 计算整体调整汇总
    total_increase = sum(a['delta'] for a in category_analysis if a['delta'] > 0)
    total_decrease = sum(abs(a['delta']) for a in category_analysis if a['delta'] < 0)
    
    # 优先级判断
    if pe_level == "low" or total_decrease > 20:
        priority = "高"
        priority_icon = "🔴"
    elif pe_level == "medium" and (total_increase > 10 or total_decrease > 10):
        priority = "中"
        priority_icon = "🟡"
    else:
        priority = "低"
        priority_icon = "🟢"
    
    # 预期效果
    if pe_level == "low":
        expected_pe = pe * 1.35
        expected = f"坪效从¥{pe:,.0f}提升至¥{expected_pe:,.0f}/组（+35%）"
    elif pe_level == "medium" and (total_increase > 0 or total_decrease > 0):
        expected_pe = pe * 1.12
        expected = f"坪效从¥{pe:,.0f}提升至¥{expected_pe:,.0f}/组（+12%）"
    else:
        expected = f"维持现有坪效¥{pe:,.0f}/组"
    
    return {
        '店号': store_id,
        '场景代码': scene_code,
        '场景': scene_name,
        '货架组数': current_groups,
        'SKU总数': total_sku,
        '近30天销量': total_sales_qty,
        '近30天销售额': total_sales_amount,
        '坪效': pe,
        '坪效评级': efficiency,
        '推荐组数': recommend_groups,
        '货架调整建议': shelf_suggestion,
        'SKU调整建议': sku_suggestion_text,  # 多行文本，包含多个品类
        'SKU调整详情': detail_text,
        '增加SKU总数': total_increase,
        '减少SKU总数': total_decrease,
        '净变化': total_increase - total_decrease,
        '优先级': priority,
        '优先级图标': priority_icon,
        '预期效果': expected,
        '品类明细': category_analysis  # 保留原始明细供展开使用
    }


def diagnose_store_shelf_data(shelf_detail_df: pd.DataFrame) -> pd.DataFrame:
    """
    诊断整个门店的货架数据
    参数:
        shelf_detail_df: 包含以下字段的DataFrame
            - 店号
            - 场景代码
            - 场景
            - 货架组数
            - 大类 (可选，用于多品类分析)
            - SKU编码 (可选，用于精确计数)
            - SKU名称 (可选)
            - 近30天销量
            - 近30天销售额
            - 坪效 (可选，会自动计算)
            - 推荐组数
    返回:
        诊断结果DataFrame
    """
    if shelf_detail_df.empty:
        return pd.DataFrame()
    
    # 确保必要字段存在
    required_fields = ['店号', '场景代码', '场景', '货架组数', '近30天销售额', '推荐组数']
    for field in required_fields:
        if field not in shelf_detail_df.columns:
            raise ValueError(f"缺少必要字段: {field}")
    
    # # 如果没有SKU编码字段，使用sku数字段
    # if 'SKU编码' not in shelf_detail_df.columns and 'sku数' in shelf_detail_df.columns:
    #     # 为每个品类生成模拟SKU编码
    #     shelf_detail_df['SKU编码'] = shelf_detail_df.apply(
    #         lambda x: f"{x['场景代码']}_{x.get('大类', x['场景'])}_SKU", axis=1
    #     )
    
    results = []
    
    # 按场景分组
    for (store_id, scene_code), scene_group in shelf_detail_df.groupby(['店号', '场景代码']):
        result = diagnose_scene_with_multiple_categories(scene_group)
        if result:
            results.append(result)
    
    return pd.DataFrame(results)


def get_store_summary(diagnosis_df: pd.DataFrame, store_name: str) -> Dict[str, Any]:
    """生成门店汇总信息"""
    if diagnosis_df.empty:
        return {
            'store_name': store_name,
            'total_scenes': 0,
            'need_adjust': 0,
            'high_priority_count': 0,
            'medium_priority_count': 0,
            'total_increase': 0,
            'total_decrease': 0,
            'avg_pe': 0
        }
    
    return {
        'store_name': store_name,
        'total_scenes': len(diagnosis_df),
        'need_adjust': len(diagnosis_df[diagnosis_df['增加SKU总数'] > 0]) + len(diagnosis_df[diagnosis_df['减少SKU总数'] > 0]),
        'high_priority_count': len(diagnosis_df[diagnosis_df['优先级'] == '高']),
        'medium_priority_count': len(diagnosis_df[diagnosis_df['优先级'] == '中']),
        'total_increase': diagnosis_df['增加SKU总数'].sum(),
        'total_decrease': diagnosis_df['减少SKU总数'].sum(),
        'avg_pe': diagnosis_df['坪效'].mean()
    }


def format_shelf_display_df(diagnosis_df: pd.DataFrame) -> pd.DataFrame:
    """格式化用于展示的DataFrame"""
    if diagnosis_df.empty:
        return pd.DataFrame()
    
    display_df = diagnosis_df[[
        '场景', '货架组数', 'SKU总数',
        '近30天销售额', '坪效', '坪效评级',
        '推荐组数', '货架调整建议', 'SKU调整建议'
    ]].copy()
    
    # 格式化数值
    display_df['坪效'] = display_df['坪效'].apply(lambda x: f"¥{x:,.0f}")
    display_df['近30天销售额'] = display_df['近30天销售额'].apply(lambda x: f"¥{x:,.0f}")
    # display_df['近30天销量'] = display_df['近30天销量'].apply(lambda x: f"{x:,.0f}")
    
    return display_df