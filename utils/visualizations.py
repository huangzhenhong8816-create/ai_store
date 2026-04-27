import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def create_ratio_comparison_chart(comparison_df):
    """创建理论占比vs落地占比对比图"""
    fig = px.bar(
        comparison_df, 
        x='category', 
        y=['theoretical_ratio', 'actual_ratio'],
        barmode='group',
        # title='便利店品类结构对比',
        labels={'value': '占比', 'category': '品类', 'variable': '类型'},
        color_discrete_map={
            'theoretical_ratio': '#2A5C9A',
            'actual_ratio': '#2E7D32'
        }
    )
    fig.update_layout(yaxis_tickformat='.0%', height=400)
    fig.update_traces(texttemplate='%{y:.1%}', textposition='outside')
    return fig

def create_demand_heatmap(demand_data):
    """创建需求热力图"""
    if isinstance(demand_data, dict):
        df = pd.DataFrame([demand_data])
    else:
        df = demand_data
    fig = px.imshow(
        df.values,
        text_auto='.1%',
        aspect='auto',
        color_continuous_scale='Blues',
        title='品类需求强度'
    )
    fig.update_layout(height=350)
    return fig

def create_diagnosis_gauge(actual, benchmark, category):
    """创建诊断仪表盘"""
    deviation = (actual - benchmark) / benchmark if benchmark > 0 else 0
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=actual * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"{category} 占比 (%)"},
        delta={'reference': benchmark * 100, 'relative': True},
        gauge={
            'axis': {'range': [None, 50]},
            'bar': {'color': "#2A5C9A"},
            'steps': [
                {'range': [0, benchmark*100], 'color': "#ffcccc"},
                {'range': [benchmark*100, 50], 'color': "#ccffcc"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': benchmark * 100
            }
        }
    ))
    fig.update_layout(height=250)
    return fig

def create_age_distribution_pie(age_data):
    """创建年龄分布饼图"""
    fig = px.pie(
        age_data, 
        values='count', 
        names='age_group',
        title='顾客年龄分布',
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

def create_gender_distribution_bar(gender_data):
    """创建性别分布柱状图"""
    fig = px.bar(
        gender_data,
        x='gender',
        y='count',
        title='顾客性别分布',
        color='gender',
        color_discrete_map={'男': '#2A5C9A', '女': '#FF6B6B'}
    )
    fig.update_layout(showlegend=False, height=300)
    return fig

def create_time_slot_distribution(time_data):
    """创建时段分布图"""
    fig = px.bar(
        time_data,
        x='time_slot',
        y='count',
        # title='顾客到店时段分布',
        color='time_slot',
        color_discrete_sequence=['#2A5C9A', '#2E7D32', '#FF6B6B', '#FF9800']
    )
    fig.update_layout(showlegend=False, height=300)
    return fig