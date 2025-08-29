#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

#######################
# Page configuration
st.set_page_config(
    page_title="해양사고 대시보드",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("default")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

/* KPI 카드 스타일 */
[data-testid="stMetric"] {
    background-color: #f5f5f5;  /* 밝은 회색 배경 */
    color: #000000;             /* 검은 텍스트 */
    text-align: center;
    padding: 15px 0;
    border-radius: 8px;         /* 둥근 모서리 */
    border: 1px solid #ddd;     /* 연한 테두리 */
    margin-bottom: 10px;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
  color: #333333;
}

[data-testid="stMetricValue"] {
  font-size: 1.2rem;
  font-weight: 700;
  color: #000000;
}

</style>
""", unsafe_allow_html=True)

#######################
# Load data
df = pd.read_csv("2024선박사고.csv", encoding="cp949")

# ---- 위도·경도 전처리 함수 (도|분|초 → 십진수) ----
def dms_to_decimal(val):
    try:
        parts = [p.strip() for p in val.split("|")]
        deg, minute, sec = map(float, parts)
        return deg + minute/60 + sec/3600
    except:
        return None

df["lat"] = df["위도"].apply(dms_to_decimal)
df["lon"] = df["경도"].apply(dms_to_decimal)

# ---- Column Alias ----
COL_DATE = "발생일시"
COL_MONTH = "월별"
COL_HOUR = "시간대별"
COL_COAST = "관할해경서"
COL_AREA = "발생해역"
COL_WEATHER = "기상상태"
COL_CAUSE = "발생원인"
COL_TYPE = "발생유형"
COL_SHIP = "선 종"
COL_TON = "톤수"
COL_INJ = "부상"
COL_DEAD = "사망"
COL_MISS = "실종"

df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")

#######################
# Sidebar
with st.sidebar:
    st.title("🚢 2024년 해양사고 대시보드")
    st.caption("필터를 적용하면 전체 차트가 연동됩니다.")

    # ---- Date range filter ----
    min_d, max_d = df[COL_DATE].min(), df[COL_DATE].max()
    date_range = st.date_input(
        "📅 발생일시",
        value=(min_d.date(), max_d.date()),
        min_value=min_d.date(),
        max_value=max_d.date(),
        format="YYYY-MM-DD"
    )

    # ---- Category filters ----
    sel_ship = st.multiselect("⚓ 선종", sorted(df[COL_SHIP].dropna().unique()))
    sel_type = st.multiselect("⚠️ 사고유형", sorted(df[COL_TYPE].dropna().unique()))
    sel_cause = st.multiselect("🛠️ 발생원인", sorted(df[COL_CAUSE].dropna().unique()))
    sel_weather = st.multiselect("🌦️ 기상상태", sorted(df[COL_WEATHER].dropna().unique()))
    sel_coast = st.multiselect("🏛️ 관할해경서", sorted(df[COL_COAST].dropna().unique()))
    sel_area = st.multiselect("🌊 발생해역", sorted(df[COL_AREA].dropna().unique()))

    # ---- Numeric filters ----
    sel_month = st.slider("🗓️ 월", int(df[COL_MONTH].min()), int(df[COL_MONTH].max()),
                          (int(df[COL_MONTH].min()), int(df[COL_MONTH].max())))
    sel_hour = st.slider("⏰ 시간대", int(df[COL_HOUR].min()), int(df[COL_HOUR].max()),
                         (int(df[COL_HOUR].min()), int(df[COL_HOUR].max())))
    sel_ton = st.slider("⚖️ 톤수", float(df[COL_TON].min()), float(df[COL_TON].max()),
                        (float(df[COL_TON].min()), float(df[COL_TON].max())))

    # ---- Apply filters ----
    mask = (df[COL_DATE].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))) & \
           (df[COL_MONTH].between(sel_month[0], sel_month[1])) & \
           (df[COL_HOUR].between(sel_hour[0], sel_hour[1])) & \
           (df[COL_TON].between(sel_ton[0], sel_ton[1]))

    if sel_ship: mask &= df[COL_SHIP].isin(sel_ship)
    if sel_type: mask &= df[COL_TYPE].isin(sel_type)
    if sel_cause: mask &= df[COL_CAUSE].isin(sel_cause)
    if sel_weather: mask &= df[COL_WEATHER].isin(sel_weather)
    if sel_coast: mask &= df[COL_COAST].isin(sel_coast)
    if sel_area: mask &= df[COL_AREA].isin(sel_area)

    df_f = df[mask].copy()

    # ---- KPI ----
    st.subheader("📌 요약 KPI")
    kpi1, kpi2 = st.columns(2)
    kpi3, kpi4 = st.columns(2)

    kpi1.metric("사고 건수", f"{len(df_f):,}")
    kpi2.metric("부상자 수", f"{int(df_f[COL_INJ].sum()):,}")
    kpi3.metric("사망자 수", f"{int(df_f[COL_DEAD].sum()):,}")
    kpi4.metric("실종자 수", f"{int(df_f[COL_MISS].sum()):,}")

#######################
# Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap="medium")

# ---- col[0] : 시계열 ----
with col[0]:
    st.markdown("### 📅 시계열 사고 추세")

    monthly_count = df_f.groupby(COL_MONTH).size().reset_index(name="사고건수")
    chart_month = alt.Chart(monthly_count).mark_bar().encode(
        x=alt.X(COL_MONTH, title="월"),
        y=alt.Y("사고건수", title="사고 건수"),
        tooltip=[COL_MONTH, "사고건수"]
    )
    st.altair_chart(chart_month, use_container_width=True)

    hourly_count = df_f.groupby(COL_HOUR).size().reset_index(name="사고건수")
    chart_hour = alt.Chart(hourly_count).mark_area(interpolate="monotone", color="#1f77b4").encode(
        x=alt.X(COL_HOUR, title="시간대"),
        y=alt.Y("사고건수", title="사고 건수"),
        tooltip=[COL_HOUR, "사고건수"]
    )
    st.altair_chart(chart_hour, use_container_width=True)

# ---- col[1] : 지도 / 지역 분석 ----
with col[1]:
    st.markdown("### 🌍 지역별 해양사고 분석")

    fig_map = px.density_mapbox(
        df_f,
        lat="lat", lon="lon",
        radius=10,
        center=dict(lat=36.5, lon=128),
        zoom=5,
        mapbox_style="open-street-map",
        height=600,
        color_continuous_scale="YlOrRd"
    )
    st.plotly_chart(fig_map, use_container_width=True)

    coast_count = df_f[COL_COAST].value_counts().reset_index()
    coast_count.columns = ["관할해경서", "사고건수"]
    chart_coast = alt.Chart(coast_count).mark_bar().encode(
        x=alt.X("사고건수:Q", title="사고 건수"),
        y=alt.Y("관할해경서:N", sort="-x"),
        color=alt.Color("사고건수:Q", scale=alt.Scale(scheme="reds")),
        tooltip=["관할해경서", "사고건수"]
    ).properties(height=350)
    st.altair_chart(chart_coast, use_container_width=True)

    area_count = df_f[COL_AREA].value_counts().reset_index()
    area_count.columns = ["발생해역", "사고건수"]
    fig_area = px.bar(
        area_count, x="발생해역", y="사고건수",
        color="사고건수", color_continuous_scale="Blues", height=250
    )
    st.plotly_chart(fig_area, use_container_width=True)

# ---- col[2] : 사고유형 / 원인 분석 ----
with col[2]:
    st.markdown("### ⚠️ 사고유형 및 원인 분석")

    type_count = df_f[COL_TYPE].value_counts().reset_index()
    type_count.columns = ["발생유형", "사고건수"]
    fig_type = px.pie(type_count, names="발생유형", values="사고건수", hole=0.4,
                      color_discrete_sequence=px.colors.qualitative.Set3)
    fig_type.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_type, use_container_width=True)

    cause_count = df_f[COL_CAUSE].value_counts().reset_index()
    cause_count.columns = ["발생원인", "사고건수"]
    fig_cause = px.treemap(cause_count, path=["발생원인"], values="사고건수",
                           color="사고건수", color_continuous_scale="Blues")
    st.plotly_chart(fig_cause, use_container_width=True)

    ship_count = df_f[COL_SHIP].value_counts().reset_index()
    ship_count.columns = ["선 종", "사고건수"]
    chart_ship = alt.Chart(ship_count).mark_bar().encode(
        x=alt.X("사고건수:Q", title="사고 건수"),
        y=alt.Y("선 종:N", sort="-x"),
        color=alt.Color("사고건수:Q", scale=alt.Scale(scheme="blues")),
        tooltip=["선 종", "사고건수"]
    )
    st.altair_chart(chart_ship, use_container_width=True)

    # ---- 충돌 / 전복 사고 집중 분석 ----
    st.markdown("### 🔍 충돌·전복 사고 인사이트")

    df_focus = df_f[df_f[COL_TYPE].isin(["충돌", "전복"])]

    if len(df_focus) > 0:
        focus_cause = df_focus[COL_CAUSE].value_counts().reset_index()
        focus_cause.columns = ["발생원인", "사고건수"]

        chart_focus_cause = alt.Chart(focus_cause).mark_bar().encode(
            x=alt.X("사고건수:Q", title="사고 건수"),
            y=alt.Y("발생원인:N", sort="-x"),
            color=alt.Color("사고건수:Q", scale=alt.Scale(scheme="oranges")),
            tooltip=["발생원인", "사고건수"]
        ).properties(height=250, title="충돌·전복 사고 원인별 분포")
        st.altair_chart(chart_focus_cause, use_container_width=True)

        focus_month = df_focus.groupby([COL_MONTH, COL_TYPE]).size().reset_index(name="사고건수")
        chart_focus_month = alt.Chart(focus_month).mark_line(point=True).encode(
            x=alt.X(COL_MONTH, title="월"),
            y=alt.Y("사고건수", title="사고 건수"),
            color=alt.Color(COL_TYPE, title="사고유형"),
            tooltip=[COL_MONTH, COL_TYPE, "사고건수"]
        ).properties(height=250, title="충돌·전복 사고 월별 추세")
        st.altair_chart(chart_focus_month, use_container_width=True)
    else:
        st.info("현재 조건에서는 충돌·전복 사고 데이터가 없습니다.")
