import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="Advanced Logistics & Supply Chain Dashboard", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #007bff;
    }
    .chart-desc { font-size: 14px; color: #666; margin-bottom: 20px; font-style: italic; }
    .bcn-highlight {
        padding: 15px; background-color: #e3f2fd; border-radius: 8px;
        border: 1px solid #90caf9; margin-bottom: 20px; color: #0d47a1; font-weight: bold;
    }
    .section-header {
        padding: 10px; background-color: #262730; color: white;
        border-radius: 5px; margin-top: 25px; margin-bottom: 15px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


# --- 2. DATA ENGINE ---

@st.cache_data
def load_logistics_data():
    df = pd.read_excel("data.xlsx")
    m_order = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
               'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}
    df['Month_Num'] = df['MO'].map(m_order)
    df = df.sort_values(['YEAR', 'Month_Num'])
    df['Timeline'] = df['YEAR'].astype(str) + " " + df['MO']
    df['BCN_Total_TEU'] = df['BCN-20'] + (df['BCN-40'] * 2)
    df['PO_per_TEU'] = df['BCN-PO'] / df['BCN_Total_TEU']
    return df


@st.cache_data
def load_open_po_data():
    """解析 openpo.xlsx 数据"""
    df_raw = pd.read_excel("openpo.xlsx", header=None)
    # 定义周次所在列 (WK11:2, WK12:4, WK13:6)
    weeks = {2: "WK11", 4: "WK12", 6: "WK13"}
    # 定义区域起始行
    regions = {"Local": 2, "Overseas": 7}

    res = []
    for col, wk in weeks.items():
        for reg, start_row in regions.items():
            # 抓取关键指标
            prio_po = df_raw.iloc[start_row, col]
            prio_ln = df_raw.iloc[start_row, col + 1]
            oos_po = df_raw.iloc[start_row + 1, col]
            oos_it = df_raw.iloc[start_row + 1, col + 1]
            low_po = df_raw.iloc[start_row + 2, col]
            low_it = df_raw.iloc[start_row + 2, col + 1]
            open_po = df_raw.iloc[start_row + 3, col]
            open_ln = df_raw.iloc[start_row + 3, col + 1]

            res.append({
                "Week": wk, "Region": reg,
                "Priority_PO": prio_po, "Priority_Line": prio_ln,
                "Normal_PO": open_po, "Normal_Line": open_ln,
                "Total_PO": prio_po + open_po, "Total_Line": prio_ln + open_ln,
                "OOS_PO": oos_po, "OOS_Item": oos_it,
                "Low_PO": low_po, "Low_Item": low_it
            })
    return pd.DataFrame(res)


def apply_simple_slider(fig):
    fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.04, rangeslider_bgcolor="rgba(0,123,255,0.1)")
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=40), template="plotly_white", hovermode="x unified")
    return fig


# --- 3. CHART MODULES ---

def plot_volume_trend(df):
    st.subheader("🚢 Total Volume Distribution (CBM)")
    st.markdown('<p class="chart-desc">Cargo throughput across FCL, BCN, and LCL.</p>', unsafe_allow_html=True)
    fig = px.bar(df, x='Timeline', y=['FCL/CBM', 'BCN/CBM', 'LCL/CBM'], barmode='stack',
                 color_discrete_sequence=px.colors.qualitative.Safe)
    st.plotly_chart(apply_simple_slider(fig), use_container_width=True)


def plot_efficiency_analysis(df):
    st.subheader("📈 Efficiency Analysis: Density per Mode (CBM/PO)")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df['Timeline'], y=df['FCL-AVG CBM/PO'], name='FCL (CBM/PO)', line=dict(color='#FF4B4B', width=3)))
    fig.add_trace(go.Scatter(x=df['Timeline'], y=df['BCN-AVG CBM/PO'], name='BCN (CBM/PO)',
                             line=dict(color='#1C83E1', width=2, dash='dash')))
    fig.add_trace(go.Scatter(x=df['Timeline'], y=df['LCL-AVG CBM/PO'], name='LCL (CBM/PO)',
                             line=dict(color='#28A745', width=2, dash='dot')))
    st.plotly_chart(apply_simple_slider(fig), use_container_width=True)


def plot_po_vs_cbm_dual(df):
    st.subheader("🔗 Order Load Analysis: Workload (PO) vs Volume (CBM)")
    fig = go.Figure()
    total_po = df['FCL-PO'] + df['BCN-PO'] + df['LCL-PO']
    total_cbm = df['FCL/CBM'] + df['BCN/CBM'] + df['LCL/CBM']
    fig.add_trace(go.Bar(x=df['Timeline'], y=total_po, name='Total PO Count', marker_color='#D3D3D3', opacity=0.7))
    fig.add_trace(go.Scatter(x=df['Timeline'], y=total_cbm, name='Total CBM Volume', yaxis='y2',
                             line=dict(color='#007bff', width=4)))
    fig.update_layout(yaxis=dict(title="PO Count"), yaxis2=dict(title="CBM", overlaying='y', side='right'),
                      legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
    st.plotly_chart(apply_simple_slider(fig), use_container_width=True)


def plot_composition_pies(df):
    st.subheader("🍰 Portfolio Composition (Period-Specific)")
    c_f1, c_f2 = st.columns(2)
    with c_f1:
        p_year = st.selectbox("Pie Year Selection", options=sorted(df['YEAR'].unique(), reverse=True), key="pie_yr")
    with c_f2:
        p_months = st.multiselect("Pie Month Selection", options=df['MO'].unique(), default=df['MO'].unique(),
                                  key="pie_mo")
    pie_df = df[(df['YEAR'] == p_year) & (df['MO'].isin(p_months))]
    if not pie_df.empty:
        c1, c2 = st.columns(2)
        cbm_vals = [pie_df['FCL/CBM'].sum(), pie_df['BCN/CBM'].sum(), pie_df['LCL/CBM'].sum()]
        c1.plotly_chart(px.pie(values=cbm_vals, names=['FCL', 'BCN', 'LCL'], title="CBM Share"),
                        use_container_width=True)
        po_vals = [pie_df['FCL-PO'].sum(), pie_df['BCN-PO'].sum(), pie_df['LCL-PO'].sum()]
        c2.plotly_chart(px.pie(values=po_vals, names=['FCL', 'BCN', 'LCL'], title="PO Share"), use_container_width=True)


def plot_bcn_teu_analysis(df):
    st.subheader("🚛 BCN Loading Efficiency: PO per TEU")
    avg_val = df['BCN-PO'].sum() / df['BCN_Total_TEU'].sum() if df['BCN_Total_TEU'].sum() > 0 else 0
    st.markdown(f'<div class="bcn-highlight">📍 Average Efficiency: <b>{avg_val:.2f}</b> POs per TEU</div>',
                unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['Timeline'], y=df['BCN_Total_TEU'], name='Total TEU', marker_color='#1f77b4'))
    fig.add_trace(go.Scatter(x=df['Timeline'], y=df['PO_per_TEU'], name='PO per TEU', yaxis='y2',
                             line=dict(color='#ff7f0e', width=3), mode='lines+markers'))
    fig.update_layout(yaxis=dict(title="TEUs"), yaxis2=dict(title="Ratio", overlaying='y', side='right'),
                      barmode='group')
    st.plotly_chart(apply_simple_slider(fig), use_container_width=True)


def plot_regional_supply_chain(region_name, df_po):
    """为 Local/Overseas 展示 Open PO 内容"""
    st.markdown(f'<div class="section-header">📍 {region_name.upper()} Supply Chain Status</div>',
                unsafe_allow_html=True)
    sub = df_po[df_po['Region'] == region_name]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.write("**Weekly Trend: Priority + Normal PO**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=sub['Week'], y=sub['Priority_PO'], name="Priority PO", marker_color="#FF4B4B"))
        fig.add_trace(go.Bar(x=sub['Week'], y=sub['Normal_PO'], name="Normal PO", marker_color="#D3D3D3"))
        fig.add_trace(go.Scatter(x=sub['Week'], y=sub['Total_Line'], name="Total Lines", yaxis="y2",
                                 line=dict(color="#1C83E1", width=3)))
        fig.update_layout(barmode='stack', yaxis2=dict(overlaying='y', side='right', title="Lines Count"),
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("**OOS & Low Stock (Latest Week)**")
        latest = sub.iloc[-1]
        fig = go.Figure(data=[
            go.Bar(name='PO Count', x=['OOS', 'Low Stock'], y=[latest['OOS_PO'], latest['Low_PO']],
                   marker_color="#262730"),
            go.Bar(name='Item Count', x=['OOS', 'Low Stock'], y=[latest['OOS_Item'], latest['Low_Item']],
                   marker_color="#007bff")
        ])
        fig.update_layout(barmode='group', height=400, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)


# --- 4. MAIN LAYOUT ---
def main():
    try:
        data_log = load_logistics_data()
        data_po = load_open_po_data()

        with st.sidebar:
            st.title("🎛️ Control Panel")
            # 物流全局过滤
            sel_yrs = st.multiselect("1. Global Year Filter", options=sorted(data_log['YEAR'].unique(), reverse=True),
                                     default=sorted(data_log['YEAR'].unique()))
            sel_mos = st.multiselect("2. Global Month Filter", options=data_log['MO'].unique(),
                                     default=data_log['MO'].unique())

            st.markdown("---")
            # 图表选择
            log_opts = {"Total Volume (CBM)": plot_volume_trend, "Efficiency (CBM/PO)": plot_efficiency_analysis,
                        "Workload vs Volume": plot_po_vs_cbm_dual, "Composition (Pies)": plot_composition_pies,
                        "BCN TEU Efficiency": plot_bcn_teu_analysis}
            selected_log = st.multiselect("3. Logistics Charts", options=list(log_opts.keys()),
                                          default=list(log_opts.keys()))

            # 供应链区域选择
            po_regions = st.multiselect("4. Supply Chain Regions", options=["Local", "Overseas"],
                                        default=["Local", "Overseas"])

        st.title("Integrated Logistics & Supply Chain Dashboard")

        # 应用过滤
        filt_df = data_log[(data_log['YEAR'].isin(sel_yrs)) & (data_log['MO'].isin(sel_mos))]

        # KPI Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total CBM", f"{filt_df[['FCL/CBM', 'BCN/CBM', 'LCL/CBM']].sum().sum():,.0f}")
        c2.metric("PO Managed", f"{filt_df[['FCL-PO', 'BCN-PO', 'LCL-PO']].sum().sum():,.0f}")
        c3.metric("BL Issued", f"{filt_df[['FCL/BL', 'BCN/BL', 'LCL/BL']].sum().sum():,.0f}")
        c4.metric("Avg FCL Density", f"{filt_df['FCL-AVG CBM/PO'].mean():.2f}")
        st.markdown("---")

        # 渲染物流图表
        for chart in selected_log:
            log_opts[chart](filt_df)
            st.markdown("---")

        # 渲染供应链区域图表
        for region in po_regions:
            plot_regional_supply_chain(region, data_po)
            st.markdown("---")

    except Exception as e:
        st.error(f"Dashboard Error: {e}")


if __name__ == "__main__":
    main()