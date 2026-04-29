import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit.components.v1 import html
from utils.data_loader import (
    load_stores, get_store_info )

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="AI门店经营助手",
    page_icon="🏪",
    layout="wide"
)

st.markdown("""
<style>
    .stButton button { width: 100%; }
    .problem-card {
        background: #ffebee;
        border-left: 6px solid #f44336;
        padding: 0.8rem;
        margin-bottom: 0.8rem;
        border-radius: 8px;
    }
    .todo-high {
        background: #ffebee;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 6px;
        border-left: 4px solid #f44336;
    }
    .todo-mid {
        background: #fff3e0;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 6px;
        border-left: 4px solid #ff9800;
    }
    .todo-low {
        background: #e8f5e9;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-radius: 6px;
        border-left: 4px solid #4caf50;
    }
    .insight-box {
        background: #f0f4f8;
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化Session State ====================
if "step" not in st.session_state:
    st.session_state.step = 1
if "current_diagnosis_scene" not in st.session_state:
    st.session_state.current_diagnosis_scene = None

# ==================== 模拟基础数据 ====================
store_name = "杭州西湖店 (商务区)"
current_month_sales = 283000
mom_change = -3.2
yoy_change = 5.8

months = ["2025-04","2025-05","2025-06","2025-07","2025-08",
          "2025-09","2025-10","2025-11","2025-12","2026-01",
          "2026-02","2026-03","2026-04"]
sales_trend = [235000, 242000, 258000, 271000, 268000,
               262000, 275000, 281000, 279000, 265000,
               258000, 272000, 283000]

# ==================== 动态生成场景数据 ====================
def generate_scene_data():
    scenes = ["收银台端架", "A区饮品", "B区饼干", "C区方便食品", "冷柜乳品"]
    current_groups = [1, 3, 2, 2, 1]
    recommend_groups = [1, 2, 2, 2, 2]
    sales = [45200, 82300, 38900, 68200, 48400]
    pe = [45200, 27433, 19450, 34100, 48400]
    mom_changes = [2.3, -4.2, -12.8, 3.5, -1.2]
    yoy_changes = [5.2, -2.8, -15.3, 8.2, 2.1]
    
    total_sales = sum(sales)
    sales_ratio = [round(s / total_sales * 100, 1) for s in sales]
    
    shelf_suggestions = []
    for i in range(len(scenes)):
        if current_groups[i] > recommend_groups[i]:
            shelf_suggestions.append(f"压缩至{recommend_groups[i]}组")
        elif current_groups[i] < recommend_groups[i]:
            shelf_suggestions.append(f"扩充至{recommend_groups[i]}组")
        else:
            if pe[i] < 25000:
                shelf_suggestions.append("保持货架，需优化品类结构")
            elif mom_changes[i] < -5 or yoy_changes[i] < -5:
                shelf_suggestions.append("保持货架，需诊断销售下滑原因")
            else:
                shelf_suggestions.append("保持")
    
    return pd.DataFrame({
        "场景": scenes,
        "本月销售额": sales,
        "销售占比": sales_ratio,
        "环比变化": mom_changes,
        "同比变化": yoy_changes,
        "坪效": pe,
        "当前货架组数": current_groups,
        "推荐货架组数": recommend_groups,
        "货架调整建议": shelf_suggestions
    })

scene_full_data = generate_scene_data()

# ==================== 各场景的品类数据（包含增长驱动） ====================
def get_category_data_with_drivers(scene_name):
    if scene_name == "B区饼干":
        df = pd.DataFrame({
            "品类": ["饼干类", "曲奇类", "威化类", "蛋卷类", "膨化类"],
            "SKU数": [52, 18, 12, 8, 6],
            "目标SKU数": [40, 15, 15, 10, 8],
            "销售额占比": [52.1, 12.3, 6.8, 6.0, 3.4],
            "动销率": [68, 72, 88, 75, 55],
            "低效SKU占比": [32, 22, 8, 12, 33],
            "新品引入": [2.5, 1.2, 0.8, 0.5, 0.2],
            "汰品淘汰": [-5.2, -2.1, -0.5, -0.3, -0.3],
            "销量影响": [4.2, 2.5, 1.2, 0.8, 0.5],
            "价格影响": [-2.8, -0.5, -0.2, 0.1, 0.2],
            "消费升级": [1.2, 0.8, 0.3, 0.2, 0.1]
        })
        
        # 生成问题识别和主要关注点
        insights = []
        focus = []
        for _, row in df.iterrows():
            problems = []
            f = []
            if row["SKU数"] > row["目标SKU数"]:
                problems.append("🔴 SKU过多")
                f.append(f"⬇️ 减少{row['SKU数'] - row['目标SKU数']}个SKU")
            if row["低效SKU占比"] > 25:
                problems.append("🔴 低效SKU偏高")
                f.append("🗑️ 汰换滞销品")
            if row["动销率"] < 70:
                problems.append("🟡 动销率低")
                f.append("📢 加强促销")
            if not f:
                problems.append("✅ 正常")
                f.append("✓ 维持现状")
            insights.append(", ".join(problems))
            focus.append(", ".join(f))
        
        df["问题识别"] = insights
        df["主要关注点"] = focus
        return df
    elif scene_name == "A区饮品":
        df = pd.DataFrame({
            "品类": ["碳酸饮料", "茶饮料", "功能饮料", "包装水", "果汁"],
            "SKU数": [25, 18, 12, 10, 8],
            "目标SKU数": [20, 15, 12, 8, 10],
            "销售额占比": [44.2, 23.6, 15.2, 8.7, 6.5],
            "动销率": [72, 78, 82, 75, 65],
            "低效SKU占比": [28, 18, 12, 15, 25],
            "新品引入": [3.2, 2.5, 1.8, 0.5, 0.5],
            "汰品淘汰": [-3.5, -1.2, -0.3, -0.2, -0.2],
            "销量影响": [2.8, 3.2, 2.5, 1.2, 0.8],
            "价格影响": [-1.5, -0.5, -0.2, 0.1, -0.3],
            "消费升级": [1.5, 1.2, 0.8, 0.3, 0.2]
        })
        
        insights = []
        focus = []
        for _, row in df.iterrows():
            problems = []
            f = []
            if row["SKU数"] > row["目标SKU数"]:
                problems.append("🔴 SKU过多")
                f.append(f"⬇️ 减少{row['SKU数'] - row['目标SKU数']}个SKU")
            if row["低效SKU占比"] > 25:
                problems.append("🔴 低效SKU偏高")
                f.append("🗑️ 汰换滞销品")
            if row["动销率"] < 70:
                problems.append("🟡 动销率低")
                f.append("📢 加强促销")
            if not f:
                problems.append("✅ 正常")
                f.append("✓ 维持现状")
            insights.append(", ".join(problems))
            focus.append(", ".join(f))
        
        df["问题识别"] = insights
        df["主要关注点"] = focus
        return df
    else:
        return pd.DataFrame()

# ==================== 获取商品清单 ====================
def get_product_list(scene_name):
    """基于品类诊断结果生成商品调整清单，确保与问题点建议数量一致"""
    # 获取品类诊断数据
    category_data = get_category_data_with_drivers(scene_name)
    
    if category_data.empty:
        return pd.DataFrame()
    
    products = []
    
    for _, category in category_data.iterrows():
        # 解析主要关注点中的建议数量
        focus_actions = category["主要关注点"].split(", ")
        
        # 提取减少SKU数量
        reduce_sku_count = 0
        for action in focus_actions:
            if "减少" in action and "个SKU" in action:
                try:
                    reduce_sku_count = int(action.split("减少")[1].split("个SKU")[0])
                except:
                    reduce_sku_count = max(1, category["SKU数"] - category["目标SKU数"])
        
        # 汰换滞销品数量（根据低效SKU占比计算）
        remove_inefficient_count = max(1, int(category["SKU数"] * category["低效SKU占比"] / 100 * 0.6))
        
        # 新品引进数量（根据SKU缺口和新品引入影响）
        new_sku_count = max(1, int((category["目标SKU数"] - category["SKU数"]) * 0.8))
        
        # 根据品类诊断结果生成商品调整建议
        
        # 新品引进：确保与建议的引进数量一致
        if "补充" in category["主要关注点"] or category["新品引入"] > 0 or category["SKU数"] < category["目标SKU数"]:
            actual_new_count = max(1, min(new_sku_count, 5))  # 限制最大5个
            for i in range(actual_new_count):
                products.append({
                    "类型": "引入",
                    "品类": category["品类"],
                    "商品代码": f"{category['品类'][:2]}{len(products)+1:03d}",
                    "商品名": f"{category['品类']}新品{i+1}",
                    "原因": f"补充{category['品类']}品类，目标SKU{category['目标SKU数']}个"
                })
        
        # 汰品淘汰：确保与建议的淘汰数量一致
        if "汰换" in category["主要关注点"] or category["汰品淘汰"] < 0 or category["SKU数"] > category["目标SKU数"] or category["低效SKU占比"] > 25:
            # 优先使用建议中的减少数量，如果没有则使用计算值
            actual_remove_count = reduce_sku_count if reduce_sku_count > 0 else max(1, remove_inefficient_count)
            actual_remove_count = min(actual_remove_count, category["SKU数"] - 5)  # 保留至少5个SKU
            
            for i in range(actual_remove_count):
                products.append({
                    "类型": "下架",
                    "品类": category["品类"],
                    "商品代码": f"{category['品类'][:2]}{len(products)+1:03d}",
                    "商品名": f"{category['品类']}淘汰品{i+1}",
                    "原因": f"优化{category['品类']}结构，建议减少{reduce_sku_count if reduce_sku_count>0 else actual_remove_count}个SKU"
                })
        
        # 价格优化：基于价格影响和动销率
        if "加强促销" in category["主要关注点"] or abs(category["价格影响"]) > 0.5 or category["动销率"] < 70:
            price_count = 2 if abs(category["价格影响"]) > 1.0 else 1
            for i in range(price_count):
                products.append({
                    "类型": "调价",
                    "品类": category["品类"],
                })
        
        # 时段促销：基于消费升级和销量影响
        if category["消费升级"] > 0.3 or category["销量影响"] > 1.0:
            promo_count = 1
            for i in range(promo_count):
                products.append({
                    "类型": "促销",
                    "品类": category["品类"],
                    "商品代码": f"{category['品类'][:2]}{len(products)+1:03d}",
                    "商品名": f"{category['品类']}促销品{i+1}",
                    "原因": f"消费升级{category['消费升级']:+.1f}%，销量影响{category['销量影响']:+.1f}%"
                })
    
    return pd.DataFrame(products)

# ==================== 函数：销售趋势图 ====================
def plot_sales_trend():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months, y=sales_trend, mode='lines+markers', name='月销售额'))
    fig.update_layout(height=300, title="近1年销售趋势", yaxis_title="销售额(元)")
    fig.update_xaxes(
        tickangle=0,
        tickformat="%Y-%m"  # 设置x轴标签格式为 2025-01
    )
    return fig

# ==================== 识别问题场景 ====================
def identify_problem_scenes(df):
    problems = []
    for _, row in df.iterrows():
        issues = []
        if row["环比变化"] < -5 or row["同比变化"] < -5:
            issues.append(f"销售下降（环比{row['环比变化']:.1f}%/同比{row['同比变化']:.1f}%）")
        if row["坪效"] < 25000:
            issues.append(f"坪效偏低（¥{row['坪效']:,.0f}/组）")
        if row["货架调整建议"] != "保持":
            issues.append(f"货架需{row['货架调整建议']}")
        
        if issues:
            problems.append({
                "场景": row["场景"],
                "问题": " / ".join(issues),
                "优先级": "高" if any(k in issues[0] for k in ["销售下降", "坪效偏低"]) else "中"
            })
    return problems

# ==================== 渲染品类表格（使用streamlit组件） ====================
def render_category_table_with_component(df):
    """使用 st.components.v1.html 渲染表格，避免转义问题"""
    
    # 构建完整的HTML表格字符串
    html_code = """
    <div style="width:100%; overflow-x:auto;">
    <style>
        .category-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }
        .category-table th, .category-table td {
            border: 1px solid #ddd;
            padding: 8px 6px;
            vertical-align: middle;
        }
        .category-table th {
            background-color: #f0f4f8;
            font-weight: bold;
            text-align: center;
        }
        .category-table td {
            text-align: center;
        }
        .category-table td:first-child {
            text-align: left;
            font-weight: bold;
        }
        .problem-row {
            background-color: #ffebee;
        }
        .text-positive {
            color: #4caf50;
            font-weight: bold;
        }
        .text-negative {
            color: #f44336;
            font-weight: bold;
        }
        .text-warning {
            color: #f44336;
            font-weight: bold;
        }
    </style>
    
    <table class="category-table">
        <thead>
            <tr>
                <th rowspan="2">品类</th>
                <th colspan="6">品类诊断</th>
                <th colspan="6">增长驱动因素</th>
            </tr>
            <tr>
                <th>SKU数</th><th>目标SKU数</th><th>占比</th><th>动销率</th><th>低效SKU占比</th><th>问题识别</th>
                <th>新品引入</th><th>汰品淘汰</th><th>销量影响</th><th>价格影响</th><th>消费升级</th><th>主要关注点</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in df.iterrows():
        is_problem = row["问题识别"] != "✅ 正常"
        row_class = 'problem-row' if is_problem else ''
        
        # SKU数是否异常
        sku_class = 'text-warning' if row["SKU数"] > row["目标SKU数"] else ''
        # 动销率是否异常
        turnover_class = 'text-warning' if row["动销率"] < 70 else ''
        # 低效SKU占比是否异常
        low_sku_class = 'text-warning' if row["低效SKU占比"] > 25 else ''
        
        # 驱动因素样式
        new_class = 'text-positive' if row["新品引入"] > 0 else 'text-negative' if row["新品引入"] < 0 else ''
        eliminate_class = 'text-positive' if row["汰品淘汰"] > 0 else 'text-negative' if row["汰品淘汰"] < 0 else ''
        volume_class = 'text-positive' if row["销量影响"] > 0 else 'text-negative' if row["销量影响"] < 0 else ''
        price_class = 'text-positive' if row["价格影响"] > 0 else 'text-negative' if row["价格影响"] < 0 else ''
        upgrade_class = 'text-positive' if row["消费升级"] > 0 else 'text-negative' if row["消费升级"] < 0 else ''
        
        html_code += f"""
        <tr class="{row_class}">
            <td style="text-align:left;"><strong>{row['品类']}</strong></td>
            <td class="{sku_class}">{row['SKU数']}</td>
            <td>{row['目标SKU数']}</td>
            <td>{row['销售额占比']:.1f}%</td>
            <td class="{turnover_class}">{row['动销率']:.0f}%</td>
            <td class="{low_sku_class}">{row['低效SKU占比']:.0f}%</td>
            <td style="text-align:left;">{row['问题识别']}</td>
            <td class="{new_class}">{row['新品引入']:+.1f}%</td>
            <td class="{eliminate_class}">{row['汰品淘汰']:+.1f}%</td>
            <td class="{volume_class}">{row['销量影响']:+.1f}%</td>
            <td class="{price_class}">{row['价格影响']:+.1f}%</td>
            <td class="{upgrade_class}">{row['消费升级']:+.1f}%</td>
            <td style="text-align:left;">{row['主要关注点']}</td>
        </tr>
        """
    
    html_code += """
        </tbody>
    </table>
    </div>
    """
    
    # 使用streamlit组件渲染HTML
    html(html_code, height=280, scrolling=True)


# ==================== 侧边栏 ====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/convenience-store.png", width=60)
    st.title("🏪 AI门店经营助手")
    
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
    st.metric("营业时间", store_info.get('open_time', '24h'))
    st.divider()
       
    
    # 待办清单
    st.markdown("## 📋 重要事项")
    

    # 动态生成待办事项（基于主界面的重点关注场景）
    focus_scenes = identify_problem_scenes(scene_full_data)
    # 根据问题场景生成待办
    todos = []
    for fs in focus_scenes:
        scene_row = scene_full_data[scene_full_data["场景"] == fs["场景"]].iloc[0]
        if scene_row["货架调整建议"] != "保持":
            todos.append({"动作": f"{fs['场景']}货架：{scene_row['货架调整建议']}", "优先级": fs["优先级"], "类型": "货架"})

    # 按优先级排序（高 > 中 > 低）
    priority_order = {"高": 1, "中": 2, "低": 3}
    todos_sorted = sorted(todos, key=lambda x: priority_order[x["优先级"]])


    # 待办事项统计
    high_priority = len([t for t in todos_sorted if t["优先级"] == "高"])
    medium_priority = len([t for t in todos_sorted if t["优先级"] == "中"])
    total_todos = len(todos_sorted)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("待处理", total_todos)
    with col2:
        st.metric("高优先级", high_priority)
    with col3:
        st.metric("中优先级", medium_priority)
 
    if todos_sorted:
        for todo in todos_sorted:
            cls = "todo-high" if todo["优先级"] == "高" else "todo-mid" if todo["优先级"] == "中" else "todo-low"
            st.markdown(f"""
            <div class="{cls}">
                <strong>{'🔴' if todo['优先级']=='高' else '🟡' if todo['优先级']=='中' else '🟢'} {todo['动作']}</strong>
            </div>
            """, unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✅ 一键执行", use_container_width=True):
                st.success("所有待办已提交至门店系统")
                # st.balloons()
        with col_btn2:
            if st.button("📋 导出清单", use_container_width=True):
                st.success("待办清单已导出")
    else:
        st.success("🎉 暂无待办，所有场景表现良好")

    st.markdown("---")
    

# ==================== 主界面（Step 1） ====================
if st.session_state.step == 1:
    st.title(f"🏪 {store_info.get('store_name', '未知')}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("本月销售额", f"¥{current_month_sales:,}")
    with col2:
        st.metric("上月销售额", f"¥{current_month_sales/(1+mom_change/100):,.0f}", delta=f"{mom_change:+.1f}%")
    with col3:
        st.metric("去年同期销售额", f"¥{current_month_sales/(1+yoy_change/100):,.0f}", delta=f"{yoy_change:+.1f}%")

    st.plotly_chart(plot_sales_trend(), use_container_width=True)
    st.markdown("---")

    # 场景销售表格
    st.markdown("#### 📊 分场景诊断分析")

    # 参考品类销售表现样式，使用HTML表格渲染
    def render_scene_table_with_component(df):
        """使用HTML表格渲染场景销售数据，参考品类表格样式"""
        
        # 构建完整的HTML表格字符串
        html_code = """
        <div style="width:100%; overflow-x:auto;">
        <style>
            .scene-table {
                width: 100%;
                border-collapse: collapse;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            .scene-table th, .scene-table td {
                border: 1px solid #ddd;
                padding: 8px 6px;
                vertical-align: middle;
                text-align: center;
            }
            .scene-table th {
                background-color: #f0f4f8;
                font-weight: bold;
            }
            .scene-table td:first-child {
                text-align: left;
                font-weight: bold;
            }
            .problem-row {
                background-color: #ffebee;
            }
            .text-negative {
                color: #f44336;
                font-weight: bold;
            }
            .text-warning {
                color: #ff9800;
                font-weight: bold;
            }
            .text-adjust {
                color: #2196f3;
                font-weight: bold;
            }
        </style>
        
        <table class="scene-table">
            <thead>
                <tr>
                    <th>场景</th>
                    <th>销售额</th>
                    <th>占比</th>
                    <th>环比</th>
                    <th>同比</th>
                    <th>坪效</th>
                    <th>当前货架</th>
                    <th>推荐货架</th>
                    <th>货架调整建议</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for _, row in df.iterrows():
            # 判断是否为问题行
            is_problem = (row["环比变化"] < -5 or row["同比变化"] < -5 or 
                         row["坪效"] < 25000 or row["货架调整建议"] != "保持")
            row_class = 'problem-row' if is_problem else ''
            
            # 环比样式
            mom_class = 'text-negative' if row["环比变化"] < -5 else ''
            # 同比样式
            yoy_class = 'text-negative' if row["同比变化"] < -5 else ''
            # 坪效样式
            pe_class = 'text-warning' if row["坪效"] < 25000 else ''
            # 货架调整样式
            shelf_class = 'text-adjust' if row["货架调整建议"] != "保持" else ''
            
            # 场景名称添加问题标识
            scene_name = row["场景"]
            
            html_code += f"""
            <tr class="{row_class}">
                <td style="text-align:left;"><strong>{scene_name}</strong></td>
                <td>¥{row['本月销售额']:,.0f}</td>
                <td>{row['销售占比']:.1f}%</td>
                <td class="{mom_class}">{row['环比变化']:.1f}%</td>
                <td class="{yoy_class}">{row['同比变化']:.1f}%</td>
                <td class="{pe_class}">¥{row['坪效']:,.0f}</td>
                <td>{row['当前货架组数']}</td>
                <td>{row['推荐货架组数']}</td>
                <td class="{shelf_class}">{row['货架调整建议']}</td>
            </tr>
            """
        
        html_code += """
            </tbody>
        </table>
        </div>
        
        """
        
        return html_code

    # 使用HTML组件渲染表格
    scene_table_html = render_scene_table_with_component(scene_full_data)
    st.components.v1.html(scene_table_html, height=250, scrolling=True)
    

    # 重点关注场景
    st.markdown("#### ⚠️ 重点关注场景")
    problem_scenes = identify_problem_scenes(scene_full_data)

    # 按优先级从高到低排序
    priority_order = {"高": 1, "中": 2}
    problem_scenes_sorted = sorted(problem_scenes, key=lambda x: priority_order[x["优先级"]])
    
    if problem_scenes_sorted:
        for ps in problem_scenes_sorted:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                <div class="problem-card">
                    <strong>📍 {ps['场景']}</strong><br>
                    🔴 问题: {ps['问题']}<br>
                    🎯 优先级: {ps['优先级']}
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button(f"🔍 查看详情", key=f"diag_{ps['场景']}", use_container_width=True):
                    st.session_state.current_diagnosis_scene = ps["场景"]
                    st.session_state.step = 3
                    st.rerun()

                # 一键优化按钮
                if st.button(f"⚡ 一键优化", key=f"optimize_{ps['场景']}", use_container_width=True, type="secondary"):
                    # 获取对应场景的商品数据
                    scene_products = get_product_list(ps["场景"])

                    if not scene_products.empty:
                        # 统计各类型商品数量
                        new_count = len(scene_products[scene_products["类型"] == "引入"])
                        remove_count = len(scene_products[scene_products["类型"] == "下架"])
                        price_count = len(scene_products[scene_products["原因"].str.contains("价格|调价|定价", na=False)])
                        promo_count = len(scene_products[scene_products["原因"].str.contains("促销|活动|时段", na=False)])
                        
                        total_actions = new_count + remove_count + price_count + promo_count
                        
                        if total_actions > 0:
                            st.success(f"✅ {ps['场景']}一键优化完成")
                            st.info(f"""
                            💡 已执行以下优化操作：\n
                            • 完成{new_count}个商品报货\n
                            • 完成{remove_count}个商品下架\n
                            • 完成{price_count}个商品调价\n
                            • 完成{promo_count}个时段促销
                            
                            📊 总计：{total_actions}项优化操作已提交
                            """)
                        else:
                            st.info(f"ℹ️ {ps['场景']}暂无需要优化的商品项目")
                    else:
                        st.info(f"ℹ️ {ps['场景']}暂无需要优化的项目")
    else:
        st.success("✅ 所有场景表现正常")

    # ==================== 最优商品组合清单 ====================
    st.markdown("---")
    st.markdown("## 🎯 推荐商品组合清单")
    
    # 模拟最优商品组合数据
    optimal_products_data = pd.DataFrame({
        "场景": ["B区饼干", "B区饼干", "A区饮品", "A区饮品", "C区方便食品"],
        "商品代码": ["B001", "B002", "D004", "F003", "C001"],
        "商品名称": ["乐事黄瓜味", "奥利奥轻甜", "北冰洋", "外星人电解质水", "康师傅红烧牛肉面"],
        "品类": ["饼干类", "饼干类", "碳酸饮料", "功能饮料", "方便面"],
        "执行动作": ["下架", "下架", "下架", "引进", "保留"],
        "当前价格": ["¥8.5", "¥12.0", "¥6.0", "¥0.0", "¥5.5"],
        "建议价格": ["-", "-", "-", "¥8.5", "¥5.5"]
    })
    
    # 创建两列布局
    col_left, col_right = st.columns([3, 1])
    
    with col_left:
        # 显示商品清单
        # st.markdown("### 📋 商品清单")

        if not optimal_products_data.empty:
            st.dataframe(optimal_products_data, use_container_width=True, hide_index=True)
        else:
            st.info("当前暂无最优商品组合数据")
        
        # 统计信息
        total_products = len(optimal_products_data)
        remove_count = len(optimal_products_data[optimal_products_data["执行动作"] == "下架"])
        add_count = len(optimal_products_data[optimal_products_data["执行动作"] == "引进"])
        price_change_count = len(optimal_products_data[(optimal_products_data["建议价格"] != '-') & 
                                                       (optimal_products_data["建议价格"] != optimal_products_data["当前价格"])])
        
        st.markdown(f"""
        <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-top: 10px;">
        <strong>📊 统计信息：</strong> 共{total_products}个商品 | 
        <span style="color: #f44336;">下架：{remove_count}个</span> | 
        <span style="color: #4caf50;">引进：{add_count}个</span> | 
        <span style="color: #2196f3;">调价：{price_change_count}个</span>
        </div>
        """, unsafe_allow_html=True)
       
    with col_right:
        st.markdown("### ⚡ 快速操作")
        st.markdown("")
        
        # 统计操作数量
        remove_count = len(optimal_products_data[optimal_products_data["执行动作"] == "下架"])
        add_count = len(optimal_products_data[optimal_products_data["执行动作"] == "引进"])
        price_change_count = len(optimal_products_data[(optimal_products_data["建议价格"] != '-') & 
                                                       (optimal_products_data["建议价格"] != optimal_products_data["当前价格"])])
        total_actions = remove_count + add_count + price_change_count

        # 一键执行按钮
        if st.button("🚀 一键执行", use_container_width=True, type="primary"):
            if total_actions > 0:
                st.success(f"✅ 已提交全部{total_actions}项操作申请")
            else:
                st.info("ℹ️ 当前没有需要执行的操作")

        # 导出清单按钮
        if st.button("📋 导出清单", use_container_width=True, type="secondary"):
            st.success("📄 商品清单已导出为Excel文件")
            st.info("💡 文件已保存到下载目录")
        
        # st.markdown("---")
               


# ==================== 品类诊断页面（Step 3） ====================
elif st.session_state.step == 3:
    scene_name = st.session_state.current_diagnosis_scene
    st.title(f"🔍 场景品类分析")
    st.markdown(f"### 📍 {scene_name}")

    category_df = get_category_data_with_drivers(scene_name)
    product_data = get_product_list(scene_name)

    if category_df.empty:
        st.warning(f"暂无 {scene_name} 的品类数据")
        if st.button("← 返回首页", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    else:
        # 使用组件渲染品类表格（解决HTML转义问题）
        # st.markdown("#### 📊 品类销售表现与增长驱动分析")
        render_category_table_with_component(category_df)


        # 统计问题品类
        problem_categories = category_df[category_df["问题识别"] != "✅ 正常"]
        total_categories = len(category_df)
        problem_count = len(problem_categories)

        # 获取当前场景的货架调整建议
        scene_shelf_suggestion = scene_full_data[scene_full_data["场景"] == scene_name]["货架调整建议"].iloc[0] if not scene_full_data[scene_full_data["场景"] == scene_name].empty else "保持"
        
        # 分左右两个板块
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown("#### 📊 问题诊断")
            
            if problem_count > 0:
                # 分析主要问题类型
                sku_problems = problem_categories[problem_categories["SKU数"] > problem_categories["目标SKU数"]]
                turnover_problems = problem_categories[problem_categories["动销率"] < 70]
                low_efficiency_problems = problem_categories[problem_categories["低效SKU占比"] > 25]
                
                summary_text = f"""
                **🔍 诊断发现**：在{total_categories}个品类中，**{problem_count}个品类**存在经营问题。
                
                • **SKU数量问题**：{len(sku_problems)}个品类SKU过多，超出标准配置\n
                • **动销率偏低**：{len(turnover_problems)}个品类动销率低于70%，需加强促销\n
                • **低效SKU偏高**：{len(low_efficiency_problems)}个品类低效SKU占比超过25%
                """
            else:
                summary_text = """
                **✅ 经营状况良好**：所有品类均处于正常状态，无需大规模调整。
                """
            st.markdown(summary_text)
        
        with col_right:
            st.markdown("#### 🎯 关键结论")
            
            # 根据货架调整建议生成关键结论
            if scene_shelf_suggestion == "保持":
                conclusion_text = """
                **🏪 货架配置合理**
                
                • 当前货架组数与推荐配置一致\n
                • 无需进行货架结构调整\n
                • 重点优化品类内部商品组合
                """
            elif "压缩" in scene_shelf_suggestion:
                conclusion_text = """
                **📦 货架配置过剩**
                
                • 当前货架组数超出推荐配置\n
                • 建议压缩货架释放空间\n
                • 优化坪效和空间利用率
                """
            elif "扩充" in scene_shelf_suggestion:
                conclusion_text = """
                **📈 货架配置不足**
                
                • 当前货架组数低于推荐配置\n
                • 建议扩充货架增加容量\n
                • 满足顾客多样化需求
                """
            else:
                conclusion_text = """
                **🔄 货架需优化**
                
                • 当前货架配置需要调整\n
                • 建议根据销售表现优化\n
                • 提升整体经营效率
                """
            
            st.markdown(conclusion_text)

        st.markdown("---")

        # 下方左右布局
        st.markdown("#### 🎯 重点关注事项")

        col_left, col_right = st.columns([1, 1.5])

        with col_left:
            st.markdown("**📌 问题点与建议**")
            
            problem_cats = category_df[category_df["问题识别"] != "✅ 正常"]
            
            if not problem_cats.empty:
                for _, row in problem_cats.iterrows():
                    st.markdown(f"""
                    <div class="insight-box">
                        <strong>🔴 {row['品类']}</strong><br>
                        • 问题: {row['问题识别']}<br>
                        • 动销率: {row['动销率']:.0f}% | 低效SKU占比: {row['低效SKU占比']:.0f}%<br>
                        • 建议: {row['主要关注点']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("所有品类结构正常")
            

        with col_right:           
            st.markdown("**📋 商品调整清单**")

            if not product_data.empty:
                # 初始化选择状态（为每个调整类型单独管理）
                if 'selected_products_by_type' not in st.session_state:
                    st.session_state.selected_products_by_type = {
                        "新品引进": {},
                        "汰品淘汰": {},
                        "价格优化": {},
                        "时段促销": {}
                    }
                
                # 初始化当前选中的调整类型
                if 'current_adjustment_type' not in st.session_state:
                    st.session_state.current_adjustment_type = "新品引进"
                
                # 添加全局CSS样式
                st.markdown("""
                <style>
                .adjustment-tabs {
                    display: flex;
                    margin: 16px 0;
                    gap: 8px;
                }
                .product-container {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    margin: 12px 0;
                    background: #fafafa;
                }
                .product-panel {
                    max-height: 200px;
                    overflow-y: auto;
                    padding: 12px;
                }
                .product-panel::-webkit-scrollbar { width: 6px; }
                .product-panel::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
                .product-panel::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 3px; }
                .product-panel::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
                
                .stButton > button {
                    height: 28px !important;
                    padding: 0px 8px !important;
                    font-size: 12px !important;
                    margin: 2px 0px !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # 四个调整选项按钮
                adjustment_types = ["新品引进", "汰品淘汰", "价格优化", "时段促销"]
                
                # 创建选项卡
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("🆕 新品引进", use_container_width=True, 
                            type="primary" if st.session_state.current_adjustment_type == "新品引进" else "secondary"):
                        st.session_state.current_adjustment_type = "新品引进"
                        st.rerun()
                with col2:
                    if st.button("🗑️ 汰品淘汰", use_container_width=True,
                            type="primary" if st.session_state.current_adjustment_type == "汰品淘汰" else "secondary"):
                        st.session_state.current_adjustment_type = "汰品淘汰"
                        st.rerun()
                with col3:
                    if st.button("💰 价格优化", use_container_width=True,
                            type="primary" if st.session_state.current_adjustment_type == "价格优化" else "secondary"):
                        st.session_state.current_adjustment_type = "价格优化"
                        st.rerun()
                with col4:
                    if st.button("⏰ 时段促销", use_container_width=True,
                            type="primary" if st.session_state.current_adjustment_type == "时段促销" else "secondary"):
                        st.session_state.current_adjustment_type = "时段促销"
                        st.rerun()
                
                # 根据选中的类型显示对应的商品清单
                current_type = st.session_state.current_adjustment_type
                
                # 根据类型过滤商品数据
                if current_type == "新品引进":
                    filtered_data = product_data[product_data["类型"] == "引入"]
                    action_name = "报货"
                elif current_type == "汰品淘汰":
                    filtered_data = product_data[product_data["类型"] == "下架"]
                    action_name = "下架"
                elif current_type == "价格优化":
                    # 假设价格优化的商品有特定标识
                    filtered_data = product_data[product_data["原因"].str.contains("价格|调价|定价", na=False)]
                    action_name = "调价"
                else:  # 时段促销
                    # 假设促销的商品有特定标识
                    filtered_data = product_data[product_data["原因"].str.contains("促销|活动|时段", na=False)]
                    action_name = "调整"
                
                if not filtered_data.empty:
                    # 创建商品容器
                    st.markdown(f"""
                    <div class="product-container">
                        <div class="product-panel">
                    """, unsafe_allow_html=True)
                    
                    # 显示表头（品类-商品代码-商品名称-原因-操作-选择-状态）
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.5, 2, 2.5, 1, 1, 1])
                    with col1:
                        st.markdown("**品类**")
                    with col2:
                        st.markdown("**商品代码**")
                    with col3:
                        st.markdown("**商品名称**")
                    with col4:
                        st.markdown("**原因**")
                    with col5:
                        st.markdown("**操作**")
                    with col6:
                        st.markdown("**选择**")
                    with col7:
                        st.markdown("**状态**")
                    
                    # 显示商品列表
                    for _, row in filtered_data.iterrows():
                        product_code = row["商品代码"]
                        product_name = row["商品名"]
                        
                        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.5, 2, 2.5, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"{row['品类']}")
                        with col2:
                            st.markdown(f"`{product_code}`")
                        with col3:
                            st.markdown(f"**{product_name}**")
                        with col4:
                            st.markdown(f"{row['原因']}")
                        with col5:
                            # 显示操作文字（非按钮）
                            st.markdown(f"<span style='color: #2A5C9A; font-weight: bold;'>{action_name}</span>", unsafe_allow_html=True)
                        with col6:
                            is_selected = st.session_state.selected_products_by_type[current_type].get(product_code, False)
                            if st.button(f"{'取消' if is_selected else '选择'}", key=f"select_{current_type}_{product_code}"):
                                st.session_state.selected_products_by_type[current_type][product_code] = not is_selected
                                st.rerun()
                        with col7:
                            is_selected = st.session_state.selected_products_by_type[current_type].get(product_code, False)
                            if is_selected:
                                st.markdown("<span style='color: #4caf50; font-weight: bold;'>✓</span>", unsafe_allow_html=True)
                            else:
                                st.markdown("<span style='color: #999;'>○</span>", unsafe_allow_html=True)
                    
                    # 关闭容器
                    st.markdown("""
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 显示已选择的商品和数量（仅当前类型）
                    selected_count = sum(st.session_state.selected_products_by_type[current_type].values())
                    
                    # 操作按钮区域 - 默认呈现
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🔄 全选", use_container_width=True):
                            # 选择当前类型的所有商品
                            for _, row in filtered_data.iterrows():
                                st.session_state.selected_products_by_type[current_type][row["商品代码"]] = True
                            st.rerun()
                    with col_btn2:
                        # 根据当前类型设置按钮名称
                        if current_type == "新品引进":
                            button_name = "🚀 一键报货"
                        elif current_type == "汰品淘汰":
                            button_name = "🚀 一键下架"
                        elif current_type == "价格优化":
                            button_name = "🚀 一键调价"
                        else:  # 时段促销
                            button_name = "🚀 一键促销"
                        
                        if st.button(button_name, use_container_width=True, type="primary"):
                            if selected_count > 0:
                                st.success(f"✅ 已提交{selected_count}个{current_type}商品调整至门店经营平台")
                                # st.info(f"💡 {action_name}操作已记录，门店运营平台将处理您的请求")
                                # st.balloons()
                            else:
                                st.info("ℹ️ 请先选择需要调整的商品")
                    
                    # 显示已选商品列表
                    if selected_count > 0:
                        st.markdown(f"**📦 {current_type}已选择商品 ({selected_count}个)**")
                        
                        selected_items = []
                        for _, row in filtered_data.iterrows():
                            if st.session_state.selected_products_by_type[current_type].get(row["商品代码"], False):
                                selected_items.append(f"• {row['商品名']} ({row['品类']}) - {action_name}")
                        
                        if selected_items:
                            st.markdown("\n".join(selected_items))
                    else:
                        st.info("👆 点击上方选择按钮标记需要调整的商品")
                else:
                    st.info(f"暂无{current_type}相关的商品调整建议")
                
                st.markdown("---")
            else:
                st.info("暂无商品调整建议")

        st.markdown("---")

        if st.button("← 返回首页", use_container_width=True):
            st.session_state.step = 1
            st.rerun()

        st.markdown("---")
    st.caption("💡 红色行为问题品类 | 红色数字为异常指标")