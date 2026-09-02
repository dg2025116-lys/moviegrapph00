import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="영화 데이터 그래프 도감 2",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 영화 데이터 그래프 도감 2 - 분포와 관계")
st.caption(
    "1년간 박스오피스 10위권에 든 영화 가운데, 같은 기간에 개봉한 216편의 요약표입니다."
)

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/kobis_movies.csv"


# ------------------------------------------------------------
# 2. 데이터 불러오기 (캐시로 한 번만 읽기)
# ------------------------------------------------------------
@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)

    # openDt(여덟 자리 숫자) -> 날짜형으로 변환
    df["openDt"] = pd.to_datetime(
        df["openDt"].astype(str), format="%Y%m%d", errors="coerce"
    )

    # genre가 "액션|드라마|스릴러" 처럼 여러 개면 첫 번째 것만 사용
    df["genre"] = (
        df["genre"].astype(str).str.split("|").str[0].str.strip()
    )

    # nation도 혹시 여러 개일 수 있으니 첫 번째만 사용
    df["nation"] = (
        df["nation"].astype(str).str.split("|").str[0].str.strip()
    )

    # 숫자 열들은 숫자형으로 정리
    num_cols = [
        "first_scrn",
        "first_show",
        "first_week_audi",
        "total_audi",
        "days_in_top10",
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


df = load_data(DATA_URL)


# ------------------------------------------------------------
# 3. 데이터 미리보기
# ------------------------------------------------------------
with st.expander("📋 원본 데이터 살펴보기", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.metric("영화 편수", f"{len(df):,} 편")
    c2.metric("장르 수", f"{df['genre'].nunique()} 개")
    c3.metric("제작 국가 수", f"{df['nation'].nunique()} 개")

    st.dataframe(df, use_container_width=True)

    st.markdown(
        """
        **열 설명**
        - `movieCd` 영화코드 · `movieNm` 영화명 · `openDt` 개봉일
        - `genre` 장르(여러 개면 첫 번째만) · `nation` 제작 국가
        - `first_scrn` 개봉일 스크린수 · `first_show` 개봉일 상영횟수
        - `first_week_audi` 개봉 첫 주 관객 · `total_audi` 총 관객
        - `days_in_top10` 10위권에 머문 날수
        """
    )

st.divider()


# ============================================================
# 그래프 1 — 장르별 영화 편수 (도넛 그래프)
# ============================================================
st.header("1️⃣ 장르별 영화 편수")
st.write("어떤 장르의 영화가 박스오피스 10위권에 많이 올랐을까요?")

# 장르별 편수 세기
genre_count = (
    df["genre"]
    .value_counts()
    .rename_axis("장르")
    .reset_index(name="편수")
)
genre_count["비율"] = genre_count["편수"] / genre_count["편수"].sum() * 100

fig1 = go.Figure(
    data=[
        go.Pie(
            labels=genre_count["장르"],
            values=genre_count["편수"],
            hole=0.5,                      # 가운데 구멍 -> 도넛
            sort=False,
            textinfo="label+percent",
            textposition="inside",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "편수: %{value}편<br>"
                "비율: %{percent}"
                "<extra></extra>"
            ),
            marker=dict(line=dict(color="white", width=2)),
        )
    ]
)

fig1.update_layout(
    title="장르별 영화 편수 분포",
    annotations=[
        dict(
            text=f"총 {len(df)}편",
            x=0.5,
            y=0.5,
            font_size=20,
            showarrow=False,
        )
    ],
    height=560,
    legend_title_text="장르",
)

st.plotly_chart(fig1, use_container_width=True)

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 216편 가운데 ○○ 장르가 가장 많아, 흥행작의 장르가 한쪽으로 치우쳐 있음을 알 수 있다.",
    key="insight_1",
    height=80,
)

st.divider()


# ============================================================
# 그래프 2 — (직접 채워 넣을 자리)
# ============================================================
st.header("2️⃣ 두 번째 그래프")
st.info(
    "여기에 두 번째 그래프를 넣어 보세요. "
    "예: 총 관객 수의 **분포**를 보는 히스토그램은 어떨까요?"
)

# TODO: 여기에 그래프를 그리는 코드를 작성해 보세요.
# 힌트: fig2 = px.histogram(df, x="total_audi", nbins=30)
#       st.plotly_chart(fig2, use_container_width=True)

st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 대부분의 영화는 관객이 적고, 소수의 영화만 아주 많은 관객을 모았다.",
    key="insight_2",
    height=80,
)

st.divider()


# ============================================================
# 그래프 3 — (직접 채워 넣을 자리)
# ============================================================
st.header("3️⃣ 세 번째 그래프")
st.info(
    "여기에 세 번째 그래프를 넣어 보세요. "
    "예: 개봉 첫 주 관객과 총 관객의 **관계**를 보는 산점도는 어떨까요?"
)

# TODO: 여기에 그래프를 그리는 코드를 작성해 보세요.
# 힌트: fig3 = px.scatter(df, x="first_week_audi", y="total_audi",
#                        color="genre", hover_name="movieNm")
#       st.plotly_chart(fig3, use_container_width=True)

st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 개봉 첫 주 관객이 많을수록 총 관객도 많아지는 경향이 뚜렷하다.",
    key="insight_3",
    height=80,
)

st.divider()

st.caption("데이터 출처: 영화진흥위원회(KOBIS) 박스오피스 자료 재가공")
