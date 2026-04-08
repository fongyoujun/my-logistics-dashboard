import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ================= 全局配置（仅一次） =================
st.set_page_config(page_title="Logistics Intelligence Dashboard", layout="wide")

# ================= 样式定义 =================
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    section[data-testid="stSidebar"] { width: 320px !important; }
    .stCheckbox { margin-bottom: -10px; }
    .chart-title { font-size: 22px; font-weight: bold; color: #262730; margin-top: 25px; }
    .chart-desc { font-size: 14px; color: #555; margin-bottom: 5px; }
    .usage-note { font-size: 13px; color: #007bff; margin-bottom: 15px; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# ================= 辅助函数 =================
def apply_standard_layout(fig, y1_title, height=500):
    fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.04)
    fig.update_layout(
        height=height, yaxis=dict(title=y1_title),
        margin=dict(l=10, r=10, t=50, b=80),
        template="plotly_white", hovermode="x unified"
    )
    return fig

def sidebar_checkbox_group(title, options, default=True):
    st.write(f"**{title}**")
    selected = []
    cols = st.columns(2) if len(options) > 4 else [st.container()]
    for i, opt in enumerate(options):
        col = cols[i % len(cols)]
        if col.checkbox(str(opt), value=default, key=f"f_{title}_{opt}"):
            selected.append(opt)
    return selected

# ================= 仪表板 1: Logistics Performance =================
def show_logistics_dashboard():
    @st.cache_data
    def load_logistics_data():
        df = pd.read_excel("data.xlsx")
        m_order = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,
                   'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
        df['Month_Num'] = df['MO'].map(m_order)
        def get_quarter(m):
            if m in [1,2,3]: return 'Q1'
            if m in [4,5,6]: return 'Q2'
            if m in [7,8,9]: return 'Q3'
            return 'Q4'
        df['Quarter'] = df['Month_Num'].apply(get_quarter)
        df = df.sort_values(['YEAR','Month_Num'])
        df['Timeline'] = df['YEAR'].astype(str) + " " + df['MO']

        df['Total_CBM'] = df['FCL/CBM'] + df['BCN/CBM'] + df['LCL/CBM']
        df['Total_PO'] = df['FCL-PO'] + df['BCN-PO'] + df['LCL-PO']
        df['Total_BL'] = df['FCL-BL'] + df['BCN-BL'] + df['LCL-BL']
        df['Total_Item'] = df['FCL-ITEM'] + df['BCN-ITEM'] + df['LCL-ITEM']

        df['FCL_Cost_Sum'] = df['FCL-20 COST'] + df['FCL-40 COST']
        df['BCN_Cost_Sum'] = df['BCN-20 COST'] + df['BCN-40 COST']
        df['LCL_Cost_Sum'] = df['LCL-COST']
        df['Grand_Total_Cost'] = df['FCL_Cost_Sum'] + df['BCN_Cost_Sum'] + df['LCL_Cost_Sum']

        for mode in ['FCL','BCN','LCL','Total']:
            cost_col = 'Grand_Total_Cost' if mode=='Total' else f'{mode}_Cost_Sum'
            cbm_col = 'Total_CBM' if mode=='Total' else f'{mode}/CBM'
            po_col = 'Total_PO' if mode=='Total' else f'{mode}-PO'
            item_col = 'Total_Item' if mode=='Total' else f'{mode}-ITEM'
            bl_col = 'Total_BL' if mode=='Total' else f'{mode}-BL'

            df[f'{mode}_Cost_per_CBM'] = df[cost_col] / df[cbm_col]
            df[f'{mode}_Cost_per_PO'] = df[cost_col] / df[po_col]
            df[f'{mode}_Items_per_PO'] = df[item_col] / df[po_col]
            df[f'{mode}_POs_per_BL'] = df[po_col] / df[bl_col]

        df['BCN_Total_TEU'] = df['BCN-20'] + (df['BCN-40'] * 2)
        df['PO_per_TEU'] = df['BCN-PO'] / df['BCN_Total_TEU']
        return df

    try:
        df = load_logistics_data()
    except FileNotFoundError:
        st.error("未找到 data.xlsx 文件，请确保文件存在于当前目录。")
        return

    # 侧边栏过滤器
    with st.sidebar:
        st.title("🎛️ Dashboard Filters")
        sel_yrs = sidebar_checkbox_group("Years", sorted(df['YEAR'].unique(), reverse=True))
        st.markdown("---")
        sel_qtrs = sidebar_checkbox_group("Quarters", ['Q1','Q2','Q3','Q4'])
        st.markdown("---")
        sel_mos = sidebar_checkbox_group("Months",
                                         ['JAN','FEB','MAR','APR','MAY','JUN',
                                          'JUL','AUG','SEP','OCT','NOV','DEC'])
        st.markdown("---")
        st.write("**Active Charts**")
        charts_config = {
            "Deep Dive: CBM, PO & Cost Correlation": module_deep_dive_correlation,
            "LC(BL) & PO & ITEM Density Analysis": module_documentation_efficiency,
            "🚢 Total Volume Distribution (CBM)": module_volume_trend,
            "🍰 Portfolio Composition": module_portfolio_composition_pies,
            "📈 Efficiency Analysis (CBM/PO)": module_efficiency_analysis,
            "🚛 BCN Loading Efficiency": module_bcn_performance
        }
        active_list = []
        for name in charts_config.keys():
            if st.checkbox(name, value=True, key=f"active_{name}"):
                active_list.append(name)

        # ... 你原有的过滤器代码 ...
        active_list = []
        for name in charts_config.keys():
            if st.checkbox(name, value=True, key=f"active_{name}"):
                active_list.append(name)

        # --- 在这里添加刷新功能 ---
        st.markdown("---")  # 添加一条分割线
        st.write("🔄 **Data Controls**")
        if st.button("Refresh Data Now", help="点击此按钮将清除缓存并从 GitHub 重新读取最新的 Excel 文件"):
            # 1. 清除所有数据缓存
            st.cache_data.clear()
            # 2. 打印提示并重启应用
            st.toast("Refreshing data from GitHub...")
            st.rerun()

    # 主区域
    st.title("Logistics Intelligence Dashboard")
    f_df = df[(df['YEAR'].isin(sel_yrs)) & (df['Quarter'].isin(sel_qtrs)) & (df['MO'].isin(sel_mos))]
    if f_df.empty:
        st.warning("没有符合筛选条件的数据。")
        return

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total CBM", f"{f_df['Total_CBM'].sum():,.0f}")
    c2.metric("PO Managed", f"{f_df['Total_PO'].sum():,.0f}")
    c3.metric("Grand Cost", f"${f_df['Grand_Total_Cost'].sum():,.0f}")
    c4.metric("Items SKU", f"{f_df['Total_Item'].sum():,.0f}")
    st.markdown("---")

    for name in active_list:
        charts_config[name](f_df)
        st.markdown("---")

# ================= 仪表板 2: Open PO 分析 =================
def show_openpo_dashboard():
    st.title("📊 Supply Chain Priorities Analysis")
    try:
        df = pd.read_excel("openpo.xlsx", header=[0,1])
    except FileNotFoundError:
        st.error("未找到 openpo.xlsx 文件，请确保文件存在于当前目录。")
        return

    df.iloc[:,0] = df.iloc[:,0].ffill()
    regions = df.iloc[:,0].unique()
    sel_region = st.sidebar.selectbox("Select Region", regions)
    plot_df = df[df.iloc[:,0] == sel_region]

    wk_cols = [col for col in df.columns if 'WK' in str(col[0]) and col[1] == 'PO']
    fig = go.Figure()
    for wk in wk_cols:
        fig.add_bar(x=plot_df.iloc[:,1], y=plot_df[wk], name=wk[0])
    fig.update_layout(title=f"Open PO Status - {sel_region}", barmode='group', template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View Raw Data"):
        st.dataframe(plot_df)

# ================= 图表模块（从原 Part 1.txt 移过来，无改动） =================
def module_deep_dive_correlation(df):
    st.markdown('<div class="chart-title">Deep Dive: CBM, PO & Cost Correlation</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-desc">Analyzes detailed relationship between Cargo Volume, Order Count, and Expenditure.</div>', unsafe_allow_html=True)
    st.markdown('<div class="usage-note">Usage: Solid lines with markers represent Cost/CBM. Dotted lines represent Cost/PO. Both are hidden by default.</div>', unsafe_allow_html=True)
    fig = go.Figure()
    groups = [
        ('TOTAL', '#333333', 'circle', df['Grand_Total_Cost'], df['Total_CBM'], df['Total_PO'], df['Total_Cost_per_CBM'], df['Total_Cost_per_PO'], True),
        ('FCL', '#1f77b4', 'square', df['FCL_Cost_Sum'], df['FCL/CBM'], df['FCL-PO'], df['FCL_Cost_per_CBM'], df['FCL_Cost_per_PO'], False),
        ('BCN', '#ff7f0e', 'diamond', df['BCN_Cost_Sum'], df['BCN/CBM'], df['BCN-PO'], df['BCN_Cost_per_CBM'], df['BCN_Cost_per_PO'], False),
        ('LCL', '#2ca02c', 'triangle-up', df['LCL_Cost_Sum'], df['LCL/CBM'], df['LCL-PO'], df['LCL_Cost_per_CBM'], df['LCL_Cost_per_PO'], False)
    ]
    for label, color, symbol, cost, cbm, po, cp_cbm, cp_po, is_vis in groups:
        vis = True if is_vis else "legendonly"
        fig.add_trace(go.Scatter(x=df['Timeline'], y=cost, name=f"{label} COST", yaxis='y2', line=dict(color=color, width=4), visible=vis))
        fig.add_trace(go.Bar(x=df['Timeline'], y=cbm, name=f"{label} CBM", marker_color=color, opacity=0.3, visible=vis))
        fig.add_trace(go.Scatter(x=df['Timeline'], y=po, name=f"{label} PO", line=dict(color=color, width=2, dash='dash'), visible=vis))
        fig.add_trace(go.Scatter(x=df['Timeline'], y=cp_cbm, name=f"{label} AVG COST/CBM", yaxis='y2', visible="legendonly",
                                 mode='lines+markers', marker=dict(symbol=symbol, size=8), line=dict(color=color, width=2.5)))
        fig.add_trace(go.Scatter(x=df['Timeline'], y=cp_po, name=f"{label} AVG COST/PO", yaxis='y2', visible="legendonly",
                                 mode='lines', line=dict(color=color, width=1.5, dash='dot')))
    fig = apply_standard_layout(fig, "CBM & PO Scale", height=800)
    fig.update_layout(
        yaxis2=dict(title="Cost & Avg metrics ($)", overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", y=1.3, x=0.5, xanchor="center", yanchor="top", entrywidth=150, entrywidthmode="pixels"),
        margin=dict(t=250)
    )
    st.plotly_chart(fig, use_container_width=True)

def module_documentation_efficiency(df):
    st.markdown('<div class="chart-title">LC(BL) & PO & ITEM Density Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-desc">Tracks documentation efficiency and item-to-order density across shipping modes.</div>', unsafe_allow_html=True)
    st.markdown('<div class="usage-note">Usage: Multi-select modes to compare. Use the density lines (right axis) to evaluate consolidation efficiency.</div>', unsafe_allow_html=True)
    selected_modes = st.multiselect("Select Modes to Compare:", ["Total", "FCL", "BCN", "LCL"], default=["Total", "FCL"], key="doc_modes")
    if not selected_modes:
        st.info("Please select at least one mode.")
        return
    fig = go.Figure()
    color_map = {
        'Total': {'BL':'#333333','PO':'#555555','ITEM':'#777777','Line1':'#000000','Line2':'#444444'},
        'FCL':   {'BL':'#A6ACEC','PO':'#636EFA','ITEM':'#19D3F3','Line1':'#EF553B','Line2':'#00CC96'},
        'BCN':   {'BL':'#FECB52','PO':'#FFA15A','ITEM':'#FF6692','Line1':'#AB63FA','Line2':'#19D3F3'},
        'LCL':   {'BL':'#B6E880','PO':'#2CA02C','ITEM':'#FF97FF','Line1':'#FECB52','Line2':'#B6E880'}
    }
    for mode in selected_modes:
        item_col = 'Total_Item' if mode=='Total' else f'{mode}-ITEM'
        bl_col   = 'Total_BL' if mode=='Total' else f'{mode}-BL'
        po_col   = 'Total_PO' if mode=='Total' else f'{mode}-PO'
        fig.add_trace(go.Bar(x=df['Timeline'], y=df[item_col], name=f'{mode} ITEM', marker_color=color_map[mode]['ITEM'], opacity=0.5))
        fig.add_trace(go.Bar(x=df['Timeline'], y=df[bl_col], name=f'{mode} BL', marker_color=color_map[mode]['BL']))
        fig.add_trace(go.Bar(x=df['Timeline'], y=df[po_col], name=f'{mode} PO', marker_color=color_map[mode]['PO']))
        fig.add_trace(go.Scatter(x=df['Timeline'], y=df[f'{mode}_Items_per_PO'], name=f'{mode} Items/PO', yaxis='y2',
                                 line=dict(color=color_map[mode]['Line1'], width=3)))
        fig.add_trace(go.Scatter(x=df['Timeline'], y=df[f'{mode}_POs_per_BL'], name=f'{mode} POs/BL', yaxis='y2',
                                 line=dict(color=color_map[mode]['Line2'], width=2, dash='dot')))
    fig = apply_standard_layout(fig, "Volume Count", height=750)
    fig.update_layout(
        barmode='group', yaxis2=dict(title="Density Ratio", overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", y=1.22, x=0.5, xanchor="center", yanchor="top", entrywidth=140, entrywidthmode="pixels"),
        margin=dict(t=180)
    )
    st.plotly_chart(fig, use_container_width=True)

def module_volume_trend(df):
    st.markdown('<div class="chart-title">🚢 Total Volume Distribution (CBM)</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-desc">Visualizes the contribution of each shipping mode to total monthly CBM.</div>', unsafe_allow_html=True)
    st.markdown('<div class="usage-note">Usage: Hover over bars to see exact CBM per mode. Use the range slider below to zoom into specific periods.</div>', unsafe_allow_html=True)
    fig = px.bar(df, x='Timeline', y=['FCL/CBM','BCN/CBM','LCL/CBM'], barmode='stack',
                 color_discrete_sequence=['#1f77b4','#ff7f0e','#2ca02c'])
    st.plotly_chart(apply_standard_layout(fig, "CBM Volume"), use_container_width=True)

def module_portfolio_composition_pies(df):
    st.markdown('<div class="chart-title">🍰 Portfolio Composition</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-desc">Percentage breakdown of Volume and Order count for a selected period.</div>', unsafe_allow_html=True)
    st.markdown('<div class="usage-note">Usage: Change the Year or Months below to update the composition analysis.</div>', unsafe_allow_html=True)
    c_f1, c_f2 = st.columns(2)
    with c_f1: p_year = st.selectbox("Select Year", options=sorted(df['YEAR'].unique(), reverse=True), key="p_y")
    with c_f2: p_months = st.multiselect("Select Months", options=df['MO'].unique(), default=df['MO'].unique(), key="p_m")
    pie_df = df[(df['YEAR']==p_year) & (df['MO'].isin(p_months))]
    if not pie_df.empty:
        col1, col2 = st.columns(2)
        col1.plotly_chart(px.pie(values=[pie_df['FCL/CBM'].sum(), pie_df['BCN/CBM'].sum(), pie_df['LCL/CBM'].sum()],
                                 names=['FCL CBM','BCN CBM','LCL CBM'], title="CBM Share",
                                 color_discrete_sequence=['#1f77b4','#ff7f0e','#2ca02c']), use_container_width=True)
        col2.plotly_chart(px.pie(values=[pie_df['FCL-PO'].sum(), pie_df['BCN-PO'].sum(), pie_df['LCL-PO'].sum()],
                                 names=['FCL PO','BCN PO','LCL PO'], title="PO Share",
                                 color_discrete_sequence=['#1f77b4','#ff7f0e','#2ca02c']), use_container_width=True)

def module_efficiency_analysis(df):
    st.markdown('<div class="chart-title">📈 Efficiency Analysis (CBM/PO)</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-desc">Measures how much cargo (CBM) is packed into each PO on average. Higher is usually more efficient.</div>', unsafe_allow_html=True)
    st.markdown('<div class="usage-note">Usage: Compare the stability of FCL vs BCN/LCL packing efficiency over time.</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Timeline'], y=df['FCL-AVG CBM/PO'], name='FCL Density', line=dict(color='#FF4B4B', width=3)))
    fig.add_trace(go.Scatter(x=df['Timeline'], y=df['BCN-AVG CBM/PO'], name='BCN Density', line=dict(color='#1C83E1', width=2, dash='dash')))
    fig.add_trace(go.Scatter(x=df['Timeline'], y=df['LCL-AVG CBM/PO'], name='LCL Density', line=dict(color='#28A745', width=2, dash='dot')))
    st.plotly_chart(apply_standard_layout(fig, "CBM per PO"), use_container_width=True)

def module_bcn_performance(df):
    st.markdown('<div class="chart-title">🚛 BCN Loading Efficiency</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-desc">Analyzes BCN performance by measuring PO count per TEU.</div>', unsafe_allow_html=True)
    st.markdown('<div class="usage-note">Usage: Monitor the orange line; an upward trend indicates more orders are consolidated into fewer containers.</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['Timeline'], y=df['BCN_Total_TEU'], name='Total TEU', marker_color='#1f77b4'))
    fig.add_trace(go.Scatter(x=df['Timeline'], y=df['PO_per_TEU'], name='PO/TEU Ratio', yaxis='y2',
                             line=dict(color='#ff7f0e', width=3)))
    fig = apply_standard_layout(fig, "TEU Count")
    fig.update_layout(yaxis2=dict(title="PO/TEU Ratio", overlaying='y', side='right', showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

# ================= 主入口 =================
def main():
    st.sidebar.title("Main Navigation")
    dashboard = st.sidebar.radio(
        "Select Dashboard:",
        ["Logistics Performance (data.xlsx)", "Supply Chain Priorities (openpo.xlsx)"]
    )
    if dashboard == "Logistics Performance (data.xlsx)":
        show_logistics_dashboard()
    else:
        show_openpo_dashboard()

if __name__ == "__main__":
    main()