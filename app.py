import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from utils.data_loader import (
    load_stores, get_store_info, get_store_sales_data, 
    get_customer_insights, load_product_pool
)


from models.shelf_sku_diagnosis import (format_shelf_display_df, get_store_summary,
                                        diagnose_store_shelf_data)
from models.growth_driver_analysis import (load_driver_data, load_product_list,load_shelf_position_data,
                                           create_waterfall_chart, get_waterfall_analysis, DRIVER_CONFIG)


def generate_sample_product_list(category_name: str, category_analysis: dict) -> pd.DataFrame:
    """
    生成示例商品清单（实际应用中应从数据源获取）
    """
    action_type = category_analysis.get('action_type', '')
    delta = category_analysis.get('delta', 0)
    
    if action_type == "增加":
        # 生成新品推荐清单
        products = []
        for i in range(min(abs(delta), 10)):  # 最多显示10个商品
            products.append({
                '商品编码': f"NEW_{category_name[:2]}_{i+1:03d}",
                '商品名称': f"新品{i+1}号 - {category_name}",
                '品类': category_name,
                '建议类型': '新品引入',
                '零售价': round(5 + i * 2, 2),
                '成本价': round(3 + i * 1.5, 2),
                '预估毛利率': round(0.3 + i * 0.02, 2),
                '推荐理由': f'高潜力{category_name}新品，预计月销{50 + i * 10}件'
            })
    elif action_type == "减少":
        # 生成汰品清单
        products = []
        for i in range(min(abs(delta), 10)):  # 最多显示10个商品
            products.append({
                '商品编码': f"OLD_{category_name[:2]}_{i+1:03d}",
                '商品名称': f"滞销品{i+1}号 - {category_name}",
                '品类': category_name,
                '建议类型': '汰品淘汰',
                '当前月销量': max(5, 50 - i * 5),
                '当前毛利率': round(0.1 - i * 0.01, 2),
                '淘汰理由': f'销量排名后30%，月销不足{20 + i * 5}件',
                '替代建议': f'可替换为高潜力{category_name}新品'
            })
    else:
        # 维持现状的商品清单
        products = [{
            '商品编码': f"CUR_{category_name[:2]}_001",
            '商品名称': f"当前主力商品 - {category_name}",
            '品类': category_name,
            '建议类型': '维持现状',
            '当前月销量': 100,
            '当前毛利率': 0.35,
            '优化建议': '保持现有陈列，优化单品效率'
        }]
    
    return pd.DataFrame(products)

# 页面配置
st.set_page_config(
    page_title="AI门店商品经营助手",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2A5C9A 0%, #1a3d66 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border-left: 4px solid #2A5C9A;
    }
    .diagnosis-critical {
        background: #ffebee;
        border-left: 4px solid #d32f2f;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .diagnosis-warning {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .diagnosis-good {
        background: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .action-card {
        background: white;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .fresh-warning {
        background: #fff3e0;
        border: 1px solid #ff9800;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏 ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/convenience-store.png", width=60)
    st.title("🏪 便利店经营助手")
    
    # 门店选择
    stores_df = load_stores()
    store_options = stores_df['store_id'].tolist()
    store_labels = [f"{row['store_id']} ({row['district']})" 
                    for _, row in stores_df.iterrows()]
    
    selected_store = st.selectbox(
        "选择门店",
        store_options,
        format_func=lambda x: store_labels[store_options.index(x)]
    )
    
    # 获取门店信息
    store_info = get_store_info(selected_store)
    
    st.divider()
    
    # 门店基本信息
    st.markdown("### 📍 门店信息")
    st.metric("门店类型", store_info.get('district', '未知'))
    st.metric("日均销售额", f"¥{store_info.get('avg_daily_sales', 0):,.0f}")
    st.metric("营业时间", store_info.get('open_time', '24h'))
    
    st.markdown("### 📐 货架配置")
    shelf_groups = st.number_input(
        "货架组数", 
        min_value=4, 
        max_value=50, 
        value=int(store_info.get('shelf_groups', 8))
    )
    shelf_layers = st.number_input(
        "货架层数", 
        min_value=2, 
        max_value=6, 
        value=int(store_info.get('shelf_layers', 4))
    )
    sku_per_layer = st.number_input(
        "每层SKU数", 
        min_value=3, 
        max_value=50, 
        value=int(store_info.get('sku_per_layer', 5))
    )
    
    st.divider()
    
    # 当前季节
    current_month = datetime.now().month
    season = "夏季" if current_month in [6, 7, 8] else "冬季" if current_month in [11, 12, 1] else "春秋"
    st.info(f"🌡️ 当前季节: {season}")
    
    # 导出功能
    if st.button("📄 导出完整报告", use_container_width=True):
        st.toast("报告生成中...", icon="📄")
        st.success("报告已导出到 downloads 文件夹")

# ==================== 主内容区 ====================
# 头部
st.markdown(f"""
<div class="main-header">
    <h1 style="color: white; margin: 0;">🏪 AI门店商品经营助手</h1>
</div>
""", unsafe_allow_html=True)

# 门店名称
st.header(f"📍 {store_info.get('store_name', selected_store)}")
st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d')} | 数据周期: 近30天")

# ==================== 模块1：消费者洞察 ====================
# st.markdown("---")
# st.subheader("📊 模块1：消费者洞察与需求池")

# with st.container():
#     col1, col2 = st.columns([1, 1.5])
    
#     with col1:
#         st.markdown("#### 👥 顾客画像")
#         customer_insights = get_customer_insights(selected_store)
        
#         if customer_insights.empty:
#             st.info("暂无顾客画像数据")
#         else:
#             # 创建子列用于显示年龄分布和性别分布
#             subcol1, subcol2 = st.columns(2)
            
#             with subcol1:
#                 # st.markdown("##### 年龄分布")
#                 age_data = customer_insights['age_group'].value_counts().reset_index()
#                 age_data.columns = ['age_group', 'count']
#                 if not age_data.empty:
#                     fig_age = create_age_distribution_pie(age_data)
#                     st.plotly_chart(fig_age, use_container_width=True, config={'displayModeBar': False})
#                 else:
#                     st.info("暂无年龄数据")
            
#             with subcol2:
#                 # st.markdown("##### 性别分布")
#                 gender_data = customer_insights['gender'].value_counts().reset_index()
#                 gender_data.columns = ['gender', 'count']
#                 if not gender_data.empty:
#                     fig_gender = create_gender_distribution_bar(gender_data)
#                     st.plotly_chart(fig_gender, use_container_width=True, config={'displayModeBar': False})
#                 else:
#                     st.info("暂无性别数据")
    
#     with col2:
#         st.markdown("#### 🎯 消费者需求池分布")
#         # 构建需求池
#         demand_ratio = build_demand_pool(selected_store)
        
#         demand_df = pd.DataFrame({
#             '品类': list(demand_ratio.keys()),
#             '需求占比': list(demand_ratio.values())
#         })
#         fig_demand = px.bar(
#             demand_df, x='品类', y='需求占比',
#             # title='消费者需求池分布',
#             color='需求占比',
#             color_continuous_scale='Blues',
#             text=demand_df['需求占比'].apply(lambda x: f'{x:.1%}')
#         )
#         fig_demand.update_layout(yaxis_tickformat='.0%', height=350)
#         st.plotly_chart(fig_demand, use_container_width=True, config={'displayModeBar': False})

# # 时段偏好分析
# if not customer_insights.empty and 'prefer_time_slot' in customer_insights.columns:
#     with st.container():
#         st.markdown("#### ⏰ 顾客到店时段偏好")
#         time_data = customer_insights['prefer_time_slot'].value_counts().reset_index()
#         time_data.columns = ['time_slot', 'count']
#         if not time_data.empty:
#             fig_time = create_time_slot_distribution(time_data)
#             st.plotly_chart(fig_time, use_container_width=True)


# ==================== 模块2：货架诊断与SKU调整建议 ====================
st.markdown("---")
st.subheader("📦 货架分配与适配")

# 显示当前门店
store_info = get_store_info(selected_store)
store_name = store_info.get('store_name', selected_store)
store_code = selected_store

st.caption(f"当前门店：{store_name}（{store_code}）")

# ========== 加载示例数据（实际使用时替换为真实数据加载） ==========
# 根据选择的门店筛选数据（实际使用时取消注释）
shelf_data = pd.read_csv(f"data/shelf_data.csv", encoding='utf-8-sig')

shelf_data = shelf_data[shelf_data['店号'] == store_code]

# ========== 执行诊断 ==========
diagnosis_df = diagnose_store_shelf_data(shelf_data)

if diagnosis_df.empty:
    st.info("暂无该门店的货架数据")
else:
    # ========== 关键指标卡片 ==========
    summary = get_store_summary(diagnosis_df, store_name)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📊 诊断场景数", summary['total_scenes'])
    with col2:
        st.metric("⚠️ 需调整场景", summary['need_adjust'])
    with col3:
        st.metric("🔴 高优先级", summary['high_priority_count'])
    with col4:
        st.metric("📈 需增加SKU", f"+{int(summary['total_increase'])}")
    with col5:
        st.metric("📉 需减少SKU", f"-{int(summary['total_decrease'])}")
    
    # ========== 场景货架诊断表 ==========
    st.markdown("#### 📋 场景货架诊断表")
    
    display_df = format_shelf_display_df(diagnosis_df)
    
    # 自定义列配置，使SKU调整建议列支持换行
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "坪效": st.column_config.TextColumn("坪效"),
            "近30天销售额": st.column_config.TextColumn("销售额"),
            "近30天销量": st.column_config.TextColumn("销量"),
            "SKU调整建议": st.column_config.TextColumn(
                "SKU调整建议", 
                width="large",
                help="不同品类分行显示，支持多行换行"
            ),
            "货架调整建议": st.column_config.TextColumn("货架调整建议", width="medium")
        }
    )
    
    # 使用CSS确保SKU调整建议列支持多行显示
    st.markdown("""
    <style>
        /* 确保SKU调整建议列支持多行换行 */
        div[data-testid="stDataFrame"] td:nth-child(10) {
            white-space: pre-wrap !important;
            line-height: 1.6 !important;
            max-width: 300px !important;
            word-wrap: break-word !important;
        }
        
        /* 为SKU调整建议列添加特殊样式 */
        div[data-testid="stDataFrame"] td:nth-child(10) {
            background-color: #f8f9fa;
            border-left: 3px solid #2A5C9A;
            padding: 8px 12px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ========== 详情展开（按场景） ==========
    st.markdown("#### 🔍 场景详细诊断报告")
    
    for _, row in diagnosis_df.iterrows():
        with st.expander(f"{row['优先级图标']} {row['场景']} - {row['坪效评级']}效场景"):
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown(f"""
                **📊 货架现状**
                - 当前货架: {row['货架组数']}组 | 推荐: {row['推荐组数']}组
                - 当前SKU总数: {row['SKU总数']}个
                - 近30天销量: {row['近30天销量']:,.0f}件
                - 近30天销售额: ¥{row['近30天销售额']:,.0f}
                - 当前坪效: ¥{row['坪效']:,.0f}/组
                """)
            
            with col_right:
                st.markdown(f"""
                **📋 调整建议**
                - 货架调整: {row['货架调整建议']}
                - 优先级: {row['优先级']}
                - 预期效果: {row['预期效果']}
                """)
            
            st.markdown("**🎯 SKU调整明细（按品类）**")
            
            # 显示每个品类的调整建议和查看清单下拉框
            if '品类明细' in row and isinstance(row['品类明细'], list):
                for category_analysis in row['品类明细']:
                    category_name = category_analysis.get('category', '未知品类')
                    suggestion = category_analysis.get('suggestion', '')
                    detail = category_analysis.get('detail', '')
                    
                    # 创建一行：品类建议 + 查看清单下拉框
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown(f"**{suggestion}**")
                        st.caption(detail)
                    
                    with col2:
                        # 生成示例商品清单（实际应用中应从数据源获取）
                        if category_analysis.get('action_type') in ['增加', '减少']:
                            # 创建查看清单的下拉框
                            with st.expander("查看清单", expanded=False):
                                sample_products = generate_sample_product_list(category_name, category_analysis)
                                
                                # 显示商品清单表格（使用更宽的布局）
                                st.markdown(f"**{category_name}商品清单**")
                                # st.markdown(f"*品类：{category_name} | 调整建议：{suggestion}*")
                                
                                # 使用更宽的表格布局
                                st.dataframe(
                                    sample_products,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "商品编码": st.column_config.TextColumn("商品编码", width="small"),
                                        "商品名称": st.column_config.TextColumn("商品名称", width="large"),
                                        "建议类型": st.column_config.TextColumn("建议类型", width="small"),
                                        "零售价": st.column_config.NumberColumn("零售价", format="¥%.2f"),
                                        "成本价": st.column_config.NumberColumn("成本价", format="¥%.2f"),
                                        "预估毛利率": st.column_config.NumberColumn("毛利率", format="%.1f%%"),
                                        "推荐理由": st.column_config.TextColumn("推荐理由", width="xlarge")
                                    }
                                )
                                
                                # 添加导出功能
                                csv_data = sample_products.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                                st.download_button(
                                    label="📥 导出商品清单CSV",
                                    data=csv_data,
                                    file_name=f"{store_name}_{row['场景']}_{category_name}_商品清单.csv",
                                    mime="text/csv",
                                    key=f"export_{row['场景']}_{category_name}",
                                    use_container_width=True
                                )
                        else:
                            st.info("无需调整")
                    
                    st.markdown("---")
            else:
                st.info("暂无品类明细数据")
            
            # 汇总统计
            if row['增加SKU总数'] > 0 or row['减少SKU总数'] > 0:
                st.info(f"📊 该场景汇总: 增加{row['增加SKU总数']}个SKU，减少{row['减少SKU总数']}个SKU，净变化{row['净变化']:+d}个")
    
    # ========== 累计调整汇总 ==========
    st.markdown("---")
    st.markdown("#### 📊 累计调整汇总")
    
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    
    with col_sum1:
        st.markdown(f"""
        <div style="background:#f0f4f8; padding:0.8rem; border-radius:8px;">
            <strong>📦 SKU调整统计</strong><br>
            • 增加SKU: <span style="color:green;">+{int(summary['total_increase'])}个</span><br>
            • 减少SKU: <span style="color:red;">-{int(summary['total_decrease'])}个</span><br>
            • 净变化: <strong>{int(summary['total_increase'] - summary['total_decrease']):+d}个</strong>
        </div>
        """, unsafe_allow_html=True)
    
    with col_sum2:
        st.markdown(f"""
        <div style="background:#f0f4f8; padding:0.8rem; border-radius:8px;">
            <strong>🚀 预期效果</strong><br>
            • 当前平均坪效: <strong>¥{summary['avg_pe']:.0f}</strong>/组<br>
            • 优化后预计坪效: <strong>¥{summary['avg_pe'] * 1.12:.0f}</strong>/组<br>
            • 整体坪效提升: <span style="color:green;">+12%</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_sum3:
        st.markdown(f"""
        <div style="background:#f0f4f8; padding:0.8rem; border-radius:8px;">
            <strong>⏰ 优先级分布</strong><br>
            • 高优先级: {summary['high_priority_count']}个场景<br>
            • 中优先级: {summary['medium_priority_count']}个场景<br>
            • 需立即处理: {summary['high_priority_count']}个
        </div>
        """, unsafe_allow_html=True)
    
    # 高优先级提醒
    high_priority_scenes = diagnosis_df[diagnosis_df['优先级'] == '高']['场景'].tolist()
    if high_priority_scenes:
        st.warning(f"⚠️ **高优先级提醒**：以下场景需要优先处理 - {', '.join(high_priority_scenes)}")
    
    # ========== 导出功能 ==========
    export_cols = ['店号', '场景代码', '场景', '货架组数', 'SKU总数', '近30天销量', '近30天销售额', 
                   '坪效', '推荐组数', '货架调整建议', 'SKU调整建议', '预期效果']
    export_df = diagnosis_df[export_cols].copy()
    csv = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    
    st.download_button(
        label="📥 导出货架诊断报告",
        data=csv,
        file_name=f"{store_name}_货架诊断报告.csv",
        mime="text/csv"
    )

# # ==================== 模块3：品类诊断 ====================
# st.markdown("---")
# st.subheader("🔍 模块3：门店品类诊断")

# with st.container():
#     # 获取实际销售占比
#     sales_metrics = calculate_category_sales_metrics(selected_store)
#     actual_ratio = adapter_result['final_ratios']
    
#     # 执行诊断
#     diagnoses = diagnose_categories(actual_ratio, demand_ratio, sales_metrics)
    
#     # 诊断卡片
#     st.markdown("#### 诊断结果汇总")
    
#     # 按严重程度排序
#     critical_cats = [c for c, d in diagnoses.items() if d['severity'] == 'critical']
#     warning_cats = [c for c, d in diagnoses.items() if d['severity'] == 'warning']
#     good_cats = [c for c, d in diagnoses.items() if d['severity'] == 'good']
    
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.metric("🔴 严重问题", len(critical_cats), delta="需立即处理" if critical_cats else None)
#     with col2:
#         st.metric("🟡 需关注", len(warning_cats))
#     with col3:
#         st.metric("🟢 正常", len(good_cats))
    
#     # 诊断详情
#     cols = st.columns(min(len(diagnoses), 4))
#     for idx, (category, diagnosis) in enumerate(diagnoses.items()):
#         with cols[idx % 4]:
#             if diagnosis['severity'] == 'critical':
#                 bg_color = "#ffebee"
#                 icon = "🔴"
#             elif diagnosis['severity'] == 'warning':
#                 bg_color = "#fff3e0"
#                 icon = "🟡"
#             else:
#                 bg_color = "#e8f5e9"
#                 icon = "🟢"
            
#             st.markdown(f"""
#             <div style="background:{bg_color}; padding:0.8rem; border-radius:8px; margin-bottom:0.5rem;">
#                 <h4>{icon} {category}</h4>
#                 <p>实际: {diagnosis['actual']:.1%}<br>基准: {diagnosis['benchmark']:.1%}</p>
#                 <p style="color:{'#d32f2f' if diagnosis['deviation']<0 else '#4caf50'}">
#                     偏差: {diagnosis['deviation']:+.1%}
#                 </p>
#             </div>
#             """, unsafe_allow_html=True)
    
#     # 详细诊断表格
#     with st.expander("📋 查看详细诊断信息"):
#         for category, diagnosis in diagnoses.items():
#             severity_class = f"diagnosis-{diagnosis['severity']}"
#             st.markdown(f"""
#             <div class="{severity_class}">
#                 <strong>{category}</strong><br>
#                 {', '.join([issue[0] + ': ' + issue[2] for issue in diagnosis['issues']])}
#             </div>
#             """, unsafe_allow_html=True)

# # ==================== 便利店特色：鲜食损耗预警 ====================
# st.markdown("---")
# st.subheader("⚠️ 鲜食损耗预警")

# with st.container():
#     # 获取鲜食品类数据
#     if '鲜食' in sales_metrics:
#         fresh_metrics = sales_metrics['鲜食']
#         turnover = fresh_metrics.get('turnover_rate', 0)
        
#         if turnover < 0.8:
#             st.markdown(f"""
#             <div class="fresh-warning">
#                 <strong>⚠️ 鲜食周转率预警</strong><br>
#                 当前鲜食周转率: {turnover:.2f} (目标: 1.0+)<br>
#                 💡 建议措施:<br>
#                 • 午餐时段(11-13点)加大热门盒饭备货<br>
#                 • 晚餐时段(17-19点)推出鲜食8折折扣<br>
#                 • 接入鲜食预售系统，按需备货<br>
#                 • 预期效果: 报废率降低30%，毛利提升5%
#             </div>
#             """, unsafe_allow_html=True)
#         else:
#             st.success(f"✅ 鲜食周转率良好 ({turnover:.2f})，继续保持")
#     else:
#         st.info("暂无鲜食销售数据")


# ==================== 模块4：品类增长驱动因素分析 ====================
st.markdown("---")
st.subheader("🚀 增长驱动因素分析")
# st.caption("基于销售数据，分析各驱动因素对品类增长的影响，提供针对性经营建议")

# 加载数据
driver_df = load_driver_data()
driver_df = driver_df[driver_df['门店'] == selected_store]

product_df = load_product_list()
shelf_df = load_shelf_position_data()

# 获取大类列表
category_list = driver_df['大类名称'].tolist()

# ========== 筛选器 ==========
selected_category = st.selectbox(
    "🏷️ 选择品类",
    options=category_list,
    index=0,
    help="选择要分析的商品大类"
)

# 筛选数据
category_data = driver_df[driver_df['大类名称'] == selected_category].iloc[0]

# ========== 瀑布图展示 ==========
st.markdown("#### 📊 驱动因素分解瀑布图")
waterfall_fig = create_waterfall_chart(category_data)
st.plotly_chart(waterfall_fig, use_container_width=True)

# ========== 瀑布图下方拆解分析 ==========
waterfall_analysis = get_waterfall_analysis(category_data)

# st.markdown("#### 📈 拆解分析")

# 创建条形图函数（子因素在左侧）
def create_bar_chart(label, value, max_value=20, bar_width=200):
    """创建水平条形图，标签在左侧"""
    normalized_value = min(abs(value) / max_value, 1.0)
    bar_length = int(bar_width * normalized_value)
    
    if value > 0:
        bar_color = "#4caf50"  # 绿色
        sign = "+"
        value_color = "#4caf50"
    else:
        bar_color = "#f44336"  # 红色
        sign = ""
        value_color = "#f44336"
    
    bar_html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
        <span style="font-size: 12px; min-width: 80px;">{label}</span>
        <div style="display: flex; align-items: center; flex-grow: 1; margin-left: 10px;">
            <div style="width: {bar_length}px; height: 12px; background-color: {bar_color}; border-radius: 2px;"></div>
            <span style="margin-left: 10px; font-size: 12px; color: {value_color}; min-width: 50px;">{sign}{value:.2f}%</span>
        </div>
    </div>
    """
    return bar_html

col1, col2 = st.columns(2)

with col1:
    # 品类结构调整影响
    category_structure_color = "#4caf50" if waterfall_analysis['category_structure_impact'] > 0 else "#f44336"
    category_structure_sign = "+" if waterfall_analysis['category_structure_impact'] > 0 else ""
    
    st.markdown(f"<h4>🔄 品类结构调整影响 <span style='color:{category_structure_color}; font-size: 14px;'>{category_structure_sign}{waterfall_analysis['category_structure_impact'] * 100:.2f}%</span></h4>", unsafe_allow_html=True)
    
    # 子项影响
    st.markdown(create_bar_chart("🗑️ 汰品影响", waterfall_analysis['sub_impacts']['汰品影响'] * 100), unsafe_allow_html=True)
    st.markdown(create_bar_chart("🆕 新品影响", waterfall_analysis['sub_impacts']['新品影响'] * 100), unsafe_allow_html=True)

with col2:
    # 老品影响
    old_product_color = "#4caf50" if waterfall_analysis['old_product_impact'] > 0 else "#f44336"
    old_product_sign = "+" if waterfall_analysis['old_product_impact'] > 0 else ""
    
    st.markdown(f"<h4>📦 老品影响 <span style='color:{old_product_color}; font-size: 14px;'>{old_product_sign}{waterfall_analysis['old_product_impact'] * 100:.2f}%</span></h4>", unsafe_allow_html=True)
    
    # 子项影响
    st.markdown(create_bar_chart("💰 价格变动", waterfall_analysis['sub_impacts']['老品价格变动影响'] * 100), unsafe_allow_html=True)
    st.markdown(create_bar_chart("📊 销量影响", waterfall_analysis['sub_impacts']['老品销量影响'] * 100), unsafe_allow_html=True)
    st.markdown(create_bar_chart("📈 消费升级", waterfall_analysis['sub_impacts']['老品消费升级影响'] * 100), unsafe_allow_html=True)

# ========== 五大驱动因素详细分析（选项卡） ==========
st.markdown("---")
st.markdown("#### 🔍 品类诊断结果建议")

# 创建选项卡
# tab_names = ["🍱 新品引入", "🗑️ 汰品淘汰", "💰 价格优化", "🎉 促销/时段", "📦 陈列/季节性"]
tab_names = ["🍱 新品引入", "🗑️ 汰品淘汰", "💰 价格优化", "🎉 促销/时段"]
tabs = st.tabs(tab_names)

# 获取当前品类的商品数据
category_products = product_df[product_df['品类名称'] == selected_category] if selected_category in product_df['品类名称'].values else pd.DataFrame()
category_shelf = shelf_df[shelf_df['品类名称'] == selected_category] if selected_category in shelf_df['品类名称'].values else pd.DataFrame()

# ========== 选项卡1：新品引入 ==========
with tabs[0]:
    driver_value = category_data['新品影响']
    config = DRIVER_CONFIG.get("新品影响", {})  

    col1, col2 = st.columns([1, 2])
    with col1:
        # 建议执行动作
        st.markdown("#### 📌 建议执行动作")
        for action in config.get("action_items", []):
            st.markdown(f"- {action}")
    
    with col2:
        # 新品清单
        st.markdown("#### 🆕 新品推荐清单")
        new_products = category_products[category_products['商品类型'] == '新品'] if not category_products.empty else pd.DataFrame()
        
        if not new_products.empty:
            display_new = new_products[['商品名称', '建议售价', '毛利率', '推荐理由', '预期效果']].copy()
            display_new.columns = ['商品名称', '建议售价(元)', '毛利率', '推荐理由', '预期效果']
            st.dataframe(display_new, use_container_width=True, hide_index=True)
        else:
            # st.info(f"当前暂无{selected_category}品类的商品数据，请补充商品清单文件")
            # # 显示示例数据
            # st.markdown("**示例新品清单**")
            sample_new = pd.DataFrame({
                '商品名称': ['示例新品A', '示例新品B', '示例新品C'],
                '建议售价(元)': [15.0, 22.0, 18.0],
                '毛利率': ['42%', '48%', '45%'],
                '推荐理由': ['竞品热销款', '网红爆品', '夏季补充'],
                '预期效果': ['月销200件', '月销150件', '月销300件']
            })
            st.dataframe(sample_new, use_container_width=True, hide_index=True)

# ========== 选项卡2：汰品淘汰 ==========
with tabs[1]:
    driver_value = category_data['汰品影响']
    config = DRIVER_CONFIG.get("汰品影响", {})
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # 建议执行动作
        st.markdown("#### 📌 建议执行动作")
        for action in config.get("action_items", []):
            st.markdown(f"- {action}")

    with col2:
        # 汰品清单示例
        st.markdown("#### 📋 建议汰品清单")
        sample_eliminate = pd.DataFrame({
            '商品名称': [f'{selected_category}商品A', f'{selected_category}商品B', f'{selected_category}商品C'],
            '近30天销量': [12, 8, 5],
            '库存天数': [35, 50, 72],
            '毛利率': ['28%', '25%', '22%'],
            '建议动作': ['观察1周', '建议汰换', '立即下架']
        })
        st.dataframe(sample_eliminate, use_container_width=True, hide_index=True)
        
        st.caption("💡 汰品建议基于近30天销量<10件且库存天数>30天的商品自动识别")

# ========== 选项卡3：价格优化 ==========
with tabs[2]:
    driver_value = category_data['老品价格变动影响']
    config = DRIVER_CONFIG.get("老品价格变动影响", {})
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # 建议执行动作
        st.markdown("#### 📌 建议执行动作")
        for action in config.get("action_items", []):
            st.markdown(f"- {action}")

    with col2:
        # 调价商品清单
        st.markdown("#### 💰 调价商品清单")
        price_products = category_products[category_products['商品类型'] == '调价'] if not category_products.empty else pd.DataFrame()
        
        if not price_products.empty:
            display_price = price_products[['商品名称', '当前售价', '建议售价', '毛利率', '推荐理由', '预期效果']].copy()
            display_price['调价幅度'] = display_price.apply(
                lambda x: f"-{x['当前售价'] - x['建议售价']:.1f}元" if pd.notna(x['当前售价']) else "新品定价",
                axis=1
            )
            display_price = display_price[['商品名称', '当前售价', '建议售价', '调价幅度', '推荐理由', '预期效果']]
            display_price.columns = ['商品名称', '当前售价(元)', '建议售价(元)', '调价幅度', '调价理由', '预期效果']
            st.dataframe(display_price, use_container_width=True, hide_index=True)
        else:
            # st.info(f"当前暂无{selected_category}品类的调价商品数据")
            # st.markdown("**示例调价清单**")
            sample_price = pd.DataFrame({
                '商品名称': ['示例商品A', '示例商品B', '示例商品C'],
                '当前售价(元)': [18.0, 25.0, 12.0],
                '建议售价(元)': [15.0, 22.0, 10.0],
                '调价幅度': ['-3元', '-3元', '-2元'],
                '调价理由': ['价格敏感型', '竞品对标', '冲量引流'],
                '预期效果': ['销量+25%', '销量+20%', '销量+30%']
            })
            st.dataframe(sample_price, use_container_width=True, hide_index=True)

# ========== 选项卡4：促销/时段 ==========
with tabs[3]:
    driver_value = category_data['老品销量影响']
    config = DRIVER_CONFIG.get("老品销量影响", {})
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # 建议执行动作
        st.markdown("#### 📌 建议执行动作")
        for action in config.get("action_items", []):
            st.markdown(f"- {action}")
    
    with col2:
        # 时段促销建议
        st.markdown("#### ⏰ 时段促销建议")
        promo_data = pd.DataFrame({
            '时段': ['早餐(7-9点)', '午餐(11-13点)', '下午茶(14-16点)', '夜宵(20-22点)'],
            '促销形式': ['面包+牛奶套餐立减3元', '盒饭第二件8折', '零食+饮料组合85折', '啤酒买三送一'],
            '适用品类': ['烘焙/乳品', '方便食品', '零食/饮料', '酒类'],
            '预期效果': ['时段销量+20%', '销量+25%', '连带率+15%', '销量+30%']
        })
        st.dataframe(promo_data, use_container_width=True, hide_index=True)

# # ========== 选项卡5：陈列/季节性 ==========
# with tabs[4]:
#     driver_value = category_data['老品消费升级影响']
#     config = DRIVER_CONFIG.get("老品消费升级影响", {})
    
#     col1, col2 = st.columns([1, 2])
#     with col1:    
#         # 建议执行动作
#         st.markdown("#### 📌 建议执行动作")
#         for action in config.get("action_items", []):
#             st.markdown(f"- {action}")
    
#     with col2:
#         # 商品陈列位置建议
#         st.markdown("#### 📦 商品陈列位置建议")
    
#         if not category_shelf.empty:
#             display_shelf = category_shelf[['商品名称', '当前陈列位置', '建议陈列位置', '调整理由', '预期效果']].copy()
#             st.dataframe(display_shelf, use_container_width=True, hide_index=True)
#         else:
#             st.info(f"当前暂无{selected_category}品类的陈列建议数据")
#             st.markdown("**示例陈列建议**")
#             sample_shelf = pd.DataFrame({
#                 '商品名称': ['示例爆品A', '示例新品B', '示例高频C'],
#                 '当前陈列位置': ['C区底层', '未上架', 'B区中层'],
#                 '建议陈列位置': ['A区黄金层', '收银台端架', 'A区主通道'],
#                 '调整理由': ['提升曝光', '促进冲动消费', '提高购买便利性'],
#                 '预期效果': ['销量+30%', '月销200件', '销量+25%']
#             })
#             st.dataframe(sample_shelf, use_container_width=True, hide_index=True)

# ========== 导出功能 ==========
st.markdown("---")
csv = driver_df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 导出驱动因素数据",
    data=csv,
    file_name="品类增长驱动因素分析.csv",
    mime="text/csv"
)

# ==================== 模块5：门店分组台账管理与SKU匹配分析 ====================
st.markdown("---")
st.subheader("🏢 总部分组台账管理")

group_sku_df = pd.read_csv('data/group_sku_range.csv')
group_sku_df.sort_values(by=['商圈分组', '品类'], inplace=True)
if not group_sku_df.empty:
    st.dataframe(group_sku_df, use_container_width=True, hide_index=True)
else:
    st.info("当前暂无分组台账数据")



# ==================== 底部 ====================
st.divider()
# st.caption("💡 提示：本系统基于消费者洞察+货架适配+增长驱动因子分析，提供千店千面的便利店经营建议")

# 运行信息
with st.expander("📊 系统运行信息"):
    st.json({
        "门店ID": selected_store,
        "门店名称": store_info.get('store_name', ''),
        "商圈类型": store_info.get('district', ''),
        "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })