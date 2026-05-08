"""
5G 信号可视化看板 — Streamlit 入口。
基础关卡：pandas 读数、RSRP 配色地图、频段/终端统计图。
进阶关卡：侧边栏联动筛选、PyDeck 3D 柱层（高度∝下载速率）、科技感 UI。
"""

from __future__ import annotations

import streamlit as st
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go

from signal_processing import (
    DEFAULT_CSV_PATH,
    add_visual_columns,
    band_cell_counts,
    filter_signals,
    load_signal_data,
    terminal_type_ratio,
)

# -----------------------------------------------------------------------------
# 页面与全局样式
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="5G 信号孪生看板",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

TECH_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Orbitron:wght@500;700&display=swap');
  /* 侧栏：深色科技色板；主区：白底 + 深色正文（与侧栏分离） */
  :root {
    --nx-surface: #121a26;
    --nx-surface-2: #1a2433;
    --nx-text: #e8edf4;
    --nx-text-muted: #9fb0c3;
    --nx-accent: #22d3ee;
    --nx-accent-soft: rgba(34, 211, 238, 0.14);
    --nx-border: rgba(34, 211, 238, 0.22);
    --nx-violet-glow: rgba(129, 140, 248, 0.12);
    --main-bg: #ffffff;
    --main-fg: #0f172a;
    --main-fg-muted: #475569;
    --main-border: #e2e8f0;
  }
  html, body, [class*="css"]  { font-family: 'JetBrains Mono', monospace; }
  .stApp {
    background: var(--main-bg) !important;
    color: var(--main-fg);
  }
  [data-testid="stAppViewContainer"] {
    background: var(--main-bg) !important;
  }
  [data-testid="stHeader"] {
    background: var(--main-bg) !important;
    border-bottom: 1px solid var(--main-border);
  }
  [data-testid="stMain"] {
    background: var(--main-bg) !important;
    color: var(--main-fg) !important;
  }
  [data-testid="stMain"] .block-container {
    background: transparent !important;
  }
  [data-testid="stMain"] p,
  [data-testid="stMain"] .stMarkdown p,
  [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
  [data-testid="stMain"] h3 {
    color: var(--main-fg) !important;
  }
  [data-testid="stMain"] .stCaption,
  [data-testid="stMain"] [data-testid="stCaption"] {
    color: var(--main-fg-muted) !important;
  }
  [data-testid="stMain"] .stMetric label {
    color: var(--main-fg-muted) !important;
  }
  [data-testid="stMain"] .stMetric [data-testid="stMetricValue"] {
    color: var(--main-fg) !important;
  }
  .block-container { padding-top: 1.2rem; max-width: 100%; }
  h1 {
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 700;
    letter-spacing: 0.06em;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 48%, #34d399 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  /* —— 侧栏：深色底 + 高对比正文（主区为白底，二者独立） —— */
  [data-testid="stSidebar"],
  [data-testid="stSidebar"] > div:first-child,
  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0c1219 0%, #111a25 45%, #0e141c 100%) !important;
    border-right: 1px solid var(--nx-border);
    box-shadow: inset -8px 0 24px var(--nx-violet-glow);
  }
  [data-testid="stSidebarContent"] {
    background: transparent !important;
  }
  /* 侧栏内通用正文：避免默认灰字贴底看不清 */
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] li,
  [data-testid="stSidebar"] .stMarkdown,
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: var(--nx-text) !important;
  }
  [data-testid="stSidebar"] .sb-lead {
    color: var(--nx-text-muted) !important;
    font-size: 0.875rem;
    line-height: 1.55;
    margin: 0 0 1rem 0;
    letter-spacing: 0.02em;
  }
  [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] .stMarkdown h3 {
    color: #7dd3fc !important;
    font-family: 'Orbitron', 'JetBrains Mono', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase;
    margin: 0 0 0.75rem 0 !important;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--nx-accent-soft);
  }
  /* 控件标签（下拉 / 滑块 / 单选 / 多选） */
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
  [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
  [data-testid="stSidebar"] .stRadio label p,
  [data-testid="stSidebar"] .stCheckbox label p,
  [data-testid="stSidebar"] .stSelectbox label p,
  [data-testid="stSidebar"] .stSlider label p {
    color: var(--nx-text) !important;
    font-weight: 500 !important;
  }
  [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p,
  [data-testid="stSidebar"] .stRadio label span {
    color: var(--nx-text) !important;
  }
  /* 单选项次要说明保持可读 */
  [data-testid="stSidebar"] small,
  [data-testid="stSidebar"] .stCaption {
    color: var(--nx-text-muted) !important;
  }
  [data-testid="stSidebar"] hr {
    margin: 1rem 0;
    border: none;
    border-top: 1px solid rgba(148, 163, 184, 0.18);
  }
  /* 下拉框：浅色字 + 略亮面板，与侧栏区分 */
  [data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: var(--nx-surface-2) !important;
    border: 1px solid rgba(148, 163, 184, 0.28) !important;
    border-radius: 8px !important;
    color: var(--nx-text) !important;
  }
  [data-testid="stSidebar"] div[data-baseweb="select"] span {
    color: var(--nx-text) !important;
  }
  /* 滑块轨道与拇指：cyan 强调 */
  [data-testid="stSidebar"] div[data-testid="stSlider"] {
    padding-top: 0.25rem;
    padding-bottom: 0.5rem;
  }
  [data-testid="stSidebar"] div[data-baseweb="slider"] [role="slider"] {
    background-color: var(--nx-accent) !important;
    border: 2px solid #0c1219 !important;
    box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.45);
  }
  [data-testid="stSidebar"] div[data-baseweb="slider"] [data-baseweb="thumb"] {
    background-color: var(--nx-accent) !important;
  }
  [data-testid="stSidebar"] div[data-baseweb="slider"] div[data-testid="stTickBarMin"],
  [data-testid="stSidebar"] div[data-baseweb="slider"] div[data-testid="stTickBarMax"] {
    color: var(--nx-text-muted) !important;
  }
  /* 单选外圈：略提亮描边，不强制填充以免未选中态异常 */
  [data-testid="stSidebar"] [data-baseweb="radio"] circle {
    stroke: rgba(148, 163, 184, 0.55) !important;
  }
  /* 复选框容器与侧栏面板统一 */
  [data-testid="stSidebar"] [data-baseweb="checkbox"] div {
    border-color: rgba(148, 163, 184, 0.45) !important;
    background-color: var(--nx-surface-2) !important;
  }
  /* 主区信息卡片：浅底，与白色页面统一 */
  .tech-card {
    border: 1px solid var(--main-border);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    background: #f8fafc;
    color: var(--main-fg);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    margin-bottom: 1rem;
  }
  .tech-card strong { color: var(--main-fg); }
  .tech-card code {
    background: #e2e8f0;
    color: #0f172a;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    font-size: 0.9em;
  }
</style>
"""
st.markdown(TECH_CSS, unsafe_allow_html=True)

st.markdown(
    '<p style="color:#7dd3fc;letter-spacing:0.22em;font-size:0.72rem;margin:0 0 0.5rem 0;opacity:0.95;">'
    "NEXUS · 5G DRIVE-TEST VISUALIZATION"
    "</p>",
    unsafe_allow_html=True,
)
st.title("5G 信号孪生看板")
st.caption("基于 `data/signal_samples.csv` · RSRP 配色 · 频段/终端分析 · 3D 速率柱体")


@st.cache_data(show_spinner=False)
def _load_data():
    return load_signal_data(DEFAULT_CSV_PATH)


df_all = _load_data()
bands = ["全部"] + sorted(df_all["Band"].astype(str).unique().tolist())
rsrp_lo = float(df_all["RSRP_dBm"].min())
rsrp_hi = float(df_all["RSRP_dBm"].max())

# -----------------------------------------------------------------------------
# 侧边栏筛选（进阶：联动地图与图表）
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 控制面板")
    st.markdown(
        '<p class="sb-lead">筛选条件实时作用于地图与统计图。</p>',
        unsafe_allow_html=True,
    )
    band_sel = st.selectbox("频段 Band", bands, index=0)
    rsrp_range = st.slider(
        "RSRP 范围 (dBm)",
        min_value=-130.0,
        max_value=-50.0,
        value=(max(-130.0, rsrp_lo), min(-50.0, rsrp_hi)),
        step=1.0,
        help="仅保留 RSRP 落在区间内的采样点。",
    )
    st.divider()
    chart_choice = st.radio(
        "地图下方图表",
        ("各频段小区数量（柱状）", "终端类型占比（饼图）"),
        index=0,
    )
    show_legend = st.checkbox("显示 RSRP 图例说明", value=True)

df_view = filter_signals(
    df_all,
    band=None if band_sel == "全部" else band_sel,
    rsrp_min=rsrp_range[0],
    rsrp_max=rsrp_range[1],
)
vis_df = add_visual_columns(df_view)

# -----------------------------------------------------------------------------
# 指标条
# -----------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("当前点数", f"{len(df_view):,}")
c2.metric("RSRP 均值 (dBm)", f"{df_view['RSRP_dBm'].mean():.1f}" if len(df_view) else "—")
c3.metric("下载均值 (Mbps)", f"{df_view['Download_Mbps'].mean():.1f}" if len(df_view) else "—")
c4.metric("SINR 均值 (dB)", f"{df_view['SINR_dB'].mean():.1f}" if len(df_view) else "—")

if show_legend:
    st.markdown(
        '<div class="tech-card">'
        "<strong>RSRP 配色</strong>："
        "<span style='color:#34d399'>■</span> 强信号（≥ −90 dBm）　"
        "<span style='color:#fbbf24'>■</span> 中等（−110 ~ −90 dBm）　"
        "<span style='color:#fb7185'>■</span> 弱信号（≤ −110 dBm）"
        "<br/><strong>3D 视图</strong>：柱体高度正比于 <code>Download_Mbps</code>。"
        "</div>",
        unsafe_allow_html=True,
    )

if len(vis_df) == 0:
    st.warning("当前筛选条件下无数据，请放宽 RSRP 或频段条件。")
    st.stop()

center_lat = float(vis_df["Latitude"].mean())
center_lon = float(vis_df["Longitude"].mean())

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=vis_df,
    get_position=["Longitude", "Latitude"],
    get_fill_color="[color_r, color_g, color_b, color_a]",
    get_radius=120,
    pickable=True,
    auto_highlight=True,
)

column_layer = pdk.Layer(
    "ColumnLayer",
    data=vis_df,
    get_position=["Longitude", "Latitude"],
    get_elevation="bar_elevation",
    elevation_scale=1,
    radius=180,
    get_fill_color="[color_r, color_g, color_b, color_a]",
    pickable=True,
    auto_highlight=True,
)

view_2d = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=11,
    pitch=0,
    bearing=0,
)
view_3d = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=11,
    pitch=55,
    bearing=-15,
)

deck_2d = pdk.Deck(
    layers=[scatter_layer],
    initial_view_state=view_2d,
    map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    tooltip={
        "html": "<b>RSRP</b> {RSRP_dBm} dBm<br/><b>SINR</b> {SINR_dB} dB<br/>"
        "<b>Band</b> {Band}<br/><b>下行</b> {Download_Mbps} Mbps",
        "style": {"backgroundColor": "#0d1117", "color": "#e6edf3"},
    },
)

deck_3d = pdk.Deck(
    layers=[column_layer],
    initial_view_state=view_3d,
    map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    tooltip={
        "html": "<b>RSRP</b> {RSRP_dBm} dBm<br/><b>下行</b> {Download_Mbps} Mbps<br/>"
        "<b>Cell</b> {CellID}",
        "style": {"backgroundColor": "#0d1117", "color": "#e6edf3"},
    },
)

tab_2d, tab_3d = st.tabs(["2D 信号散点", "3D 下载速率柱图"])

with tab_2d:
    st.pydeck_chart(deck_2d)

with tab_3d:
    st.pydeck_chart(deck_3d)

# -----------------------------------------------------------------------------
# 统计图（基础关卡）
# -----------------------------------------------------------------------------
st.markdown("### 数据概览")
left, right = st.columns((1.1, 1))

plotly_layout = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(13,17,23,0.85)",
    font=dict(family="JetBrains Mono, monospace", color="#c9d1d9"),
    margin=dict(l=40, r=20, t=40, b=40),
)

if chart_choice.startswith("各频段"):
    bc = band_cell_counts(df_view).reset_index()
    bc.columns = ["Band", "cells"]
    fig_bar = px.bar(
        bc,
        x="Band",
        y="cells",
        color="Band",
        text="cells",
        title="各频段唯一小区数量（CellID 去重）",
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(**plotly_layout, showlegend=False, xaxis_title="频段", yaxis_title="小区数")
    left.plotly_chart(fig_bar)
else:
    tt = terminal_type_ratio(df_view).reset_index()
    tt.columns = ["TerminalType", "ratio"]
    fig_pie = px.pie(
        tt,
        names="TerminalType",
        values="ratio",
        hole=0.45,
        title="终端类型样本占比",
        color_discrete_sequence=px.colors.sequential.Teal_r,
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    fig_pie.update_layout(**plotly_layout)
    left.plotly_chart(fig_pie)

# 右侧补充：另一种图表，保持信息密度
if chart_choice.startswith("各频段"):
    tt2 = terminal_type_ratio(df_view).reset_index()
    tt2.columns = ["TerminalType", "ratio"]
    fig_pie2 = go.Figure(
        data=[
            go.Pie(
                labels=tt2["TerminalType"],
                values=tt2["ratio"],
                hole=0.5,
                marker=dict(line=dict(color="#0d1117", width=2)),
            )
        ]
    )
    fig_pie2.update_layout(**plotly_layout, title="终端类型占比（补充）", showlegend=True)
    right.plotly_chart(fig_pie2)
else:
    bc2 = band_cell_counts(df_view).reset_index()
    bc2.columns = ["Band", "cells"]
    fig_bar2 = px.bar(
        bc2,
        x="Band",
        y="cells",
        title="各频段小区数量（补充）",
        color="cells",
        color_continuous_scale="Viridis",
    )
    fig_bar2.update_layout(**plotly_layout, xaxis_title="频段", yaxis_title="小区数")
    right.plotly_chart(fig_bar2)

st.caption(f"数据文件：`{DEFAULT_CSV_PATH}` · 使用 `streamlit run app.py` 启动")
