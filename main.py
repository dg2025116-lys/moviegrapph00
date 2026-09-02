import streamlit as st
import pandas as pd
import numpy as np
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
# 그래프 2 — 장르 안에 영화가 들어 있는 트리맵 (크기 = 총 관객)
# ============================================================
st.header("2️⃣ 장르 → 영화 트리맵")
st.write(
    "칸의 **넓이**가 총 관객 수입니다. "
    "큰 장르 칸 안에 그 장르에 속한 영화들이 다시 작은 칸으로 나뉘어 들어갑니다."
)

# 트리맵은 크기가 0이거나 비어 있으면 칸을 그릴 수 없으므로 걸러 냅니다.
tree_df = df[df["total_audi"].notna() & (df["total_audi"] > 0)].copy()

fig2 = px.treemap(
    tree_df,
    path=[px.Constant("전체"), "genre", "movieNm"],  # 전체 → 장르 → 영화
    values="total_audi",                             # 칸의 크기
    color="genre",                                   # 장르별로 색 구분
    color_discrete_sequence=px.colors.qualitative.Set3,
)

# 마우스를 올렸을 때 보여 줄 내용 (영화명 + 총 관객)
fig2.update_traces(
    textinfo="label",
    textfont_size=13,
    hovertemplate=(
        "<b>%{label}</b><br>"
        "총 관객: %{value:,.0f}명"
        "<extra></extra>"
    ),
    marker=dict(line=dict(color="white", width=1.5)),
    root_color="lightgrey",
)

fig2.update_layout(
    title="장르 안의 영화별 총 관객 수",
    height=650,
    margin=dict(t=60, l=10, r=10, b=10),
)

st.plotly_chart(fig2, use_container_width=True)

st.caption(
    "🖱️ 장르 칸을 클릭하면 그 장르만 확대해서 볼 수 있고, "
    "위쪽 회색 막대를 누르면 되돌아옵니다."
)

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 편수는 적어도 한두 편의 큰 흥행작이 장르 전체의 관객 수를 끌어올린 장르가 있다.",
    key="insight_2",
    height=80,
)

st.divider()


# ============================================================
# 그래프 3 — 총 관객 수 히스토그램
# ============================================================
st.header("3️⃣ 총 관객 수는 어떻게 흩어져 있을까?")
st.write(
    "가로축을 관객 수 구간으로 잘라, 각 구간에 몇 편의 영화가 들어가는지 세어 봅니다."
)

hist_df = df[df["total_audi"].notna()].copy()

# 구간 개수를 학생이 직접 바꿔 볼 수 있게
bin_count = st.slider(
    "구간(막대) 개수",
    min_value=10,
    max_value=60,
    value=30,
    step=5,
    help="막대를 잘게 나눌수록 세밀해지고, 넓게 나눌수록 큰 흐름이 보입니다.",
)

fig3 = px.histogram(
    hist_df,
    x="total_audi",
    nbins=bin_count,
    color_discrete_sequence=["#4C78A8"],
    labels={"total_audi": "총 관객 수(명)"},
)

fig3.update_traces(
    marker=dict(line=dict(color="white", width=1)),
    hovertemplate=(
        "관객 수 구간: %{x}<br>"
        "영화 편수: %{y}편"
        "<extra></extra>"
    ),
)

fig3.update_layout(
    title="총 관객 수 분포",
    xaxis_title="총 관객 수(명)",
    yaxis_title="영화 편수",
    bargap=0.05,
    height=520,
)

st.plotly_chart(fig3, use_container_width=True)


# ------------------------------------------------------------
# 히스토그램에서 읽어 낸 사실을 문구로 자동 정리
# ------------------------------------------------------------

# (1) 막대 폭을 직접 계산해, 편수가 가장 많은 구간을 찾는다
audi_min = hist_df["total_audi"].min()
audi_max = hist_df["total_audi"].max()
bin_width = (audi_max - audi_min) / bin_count

# 각 영화가 몇 번째 구간에 들어가는지 번호를 매긴다
bin_index = ((hist_df["total_audi"] - audi_min) / bin_width).astype(int)
bin_index = bin_index.clip(upper=bin_count - 1)   # 최댓값이 마지막 구간을 넘지 않게

top_bin = bin_index.value_counts().idxmax()       # 편수가 가장 많은 구간 번호
top_bin_n = int(bin_index.value_counts().max())   # 그 구간의 편수
bin_low = audi_min + top_bin * bin_width
bin_high = bin_low + bin_width

# (2) 관객이 가장 많은 영화
best = hist_df.loc[hist_df["total_audi"].idxmax()]

# (3) 중앙값과 평균 — 분포가 한쪽으로 쏠렸는지 보여 주는 단서
median_audi = hist_df["total_audi"].median()
mean_audi = hist_df["total_audi"].mean()

c1, c2, c3 = st.columns(3)
c1.metric("영화 편수", f"{len(hist_df):,} 편")
c2.metric("중앙값 관객", f"{median_audi:,.0f} 명")
c3.metric("평균 관객", f"{mean_audi:,.0f} 명")

st.success(
    f"📌 가장 많은 영화가 몰려 있는 구간은 "
    f"**{bin_low:,.0f}명 ~ {bin_high:,.0f}명**이고, "
    f"이 구간에만 **{top_bin_n}편**({top_bin_n / len(hist_df) * 100:.1f}%)이 들어 있습니다."
)

st.info(
    f"🏆 관객이 가장 많은 영화는 **{best['movieNm']}**"
    f"({best['genre']} · {best['nation']})으로, "
    f"총 **{best['total_audi']:,.0f}명**을 모았습니다. "
    f"이는 중앙값의 약 **{best['total_audi'] / median_audi:.0f}배**입니다."
)

st.caption(
    "💭 평균이 중앙값보다 훨씬 크다면, 몇몇 큰 흥행작이 평균을 끌어올리고 있다는 뜻입니다."
)

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 대부분의 영화는 관객이 적은 쪽에 몰려 있고, 아주 소수의 영화만 오른쪽으로 길게 뻗어 있다.",
    key="insight_3",
    height=80,
)

st.divider()


# ============================================================
# 그래프 4 — 개봉일 스크린수 vs 총 관객 (산점도)
# ============================================================
st.header("4️⃣ 스크린을 많이 잡으면 관객도 많을까?")
st.write(
    "점 하나가 영화 한 편입니다. "
    "가로축은 **개봉일에 확보한 스크린 수**, 세로축은 **최종 총 관객 수**입니다."
)

scatter_df = df[
    df["first_scrn"].notna() & df["total_audi"].notna()
].copy()

# 장르가 너무 많으면 색이 헷갈리므로, 보고 싶은 장르를 고를 수 있게
all_genres = sorted(scatter_df["genre"].unique())
picked_genres = st.multiselect(
    "보고 싶은 장르 고르기 (비워 두면 전체)",
    options=all_genres,
    default=[],
    help="특정 장르만 남겨 두고 보면 그 장르의 특징이 더 잘 보입니다.",
)

if picked_genres:
    plot_df = scatter_df[scatter_df["genre"].isin(picked_genres)]
else:
    plot_df = scatter_df

# 추세선을 얹을지 선택 (직선 하나로 전체 흐름 보기)
show_trend = st.checkbox("전체 흐름을 보여 주는 직선 함께 그리기", value=True)

fig4 = px.scatter(
    plot_df,
    x="first_scrn",
    y="total_audi",
    color="genre",                       # 장르별 색 구분
    hover_name="movieNm",                # 마우스를 올리면 영화명이 굵게
    hover_data={                         # 함께 보여 줄 값들
        "genre": True,
        "nation": True,
        "first_scrn": ":,",
        "total_audi": ":,",
        "days_in_top10": True,
    },
    labels={
        "first_scrn": "개봉일 스크린 수(개)",
        "total_audi": "총 관객 수(명)",
        "genre": "장르",
        "nation": "제작 국가",
        "days_in_top10": "10위권 머문 날수",
    },
    color_discrete_sequence=px.colors.qualitative.Set2,
    opacity=0.8,
)

fig4.update_traces(marker=dict(size=11, line=dict(color="white", width=1)))

# 전체 점을 대표하는 직선을 직접 계산해서 얹기
if show_trend and len(plot_df) >= 2:
    # y = a*x + b 형태의 직선 구하기 (최소제곱법)
    a, b = np.polyfit(plot_df["first_scrn"], plot_df["total_audi"], 1)
    x_line = np.linspace(
        plot_df["first_scrn"].min(), plot_df["first_scrn"].max(), 100
    )
    y_line = a * x_line + b

    fig4.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="전체 흐름",
            line=dict(color="crimson", width=3, dash="dash"),
            hovertemplate="전체 흐름을 나타낸 직선<extra></extra>",
        )
    )

fig4.update_layout(
    title="개봉일 스크린 수와 총 관객 수의 관계",
    xaxis_title="개봉일 스크린 수(개)",
    yaxis_title="총 관객 수(명)",
    height=620,
    legend_title_text="장르",
)

st.plotly_chart(fig4, use_container_width=True)


# ------------------------------------------------------------
# 산점도에서 읽어 낸 사실을 문구로 정리
# ------------------------------------------------------------

# 두 값이 함께 커지는 정도를 -1 ~ 1 사이 숫자로 나타낸 것
corr = plot_df["first_scrn"].corr(plot_df["total_audi"])

if pd.isna(corr):
    strength = "판단하기 어려운"
elif corr >= 0.7:
    strength = "매우 뚜렷하게 함께 커지는"
elif corr >= 0.4:
    strength = "어느 정도 함께 커지는"
elif corr >= 0.2:
    strength = "약하게 함께 커지는"
elif corr > -0.2:
    strength = "뚜렷한 관계가 보이지 않는"
else:
    strength = "반대로 움직이는"

c1, c2 = st.columns(2)
c1.metric("그래프에 그려진 영화", f"{len(plot_df):,} 편")
c2.metric(
    "두 값이 함께 움직이는 정도",
    "-" if pd.isna(corr) else f"{corr:.2f}",
)

st.success(
    f"📌 개봉일 스크린 수와 총 관객 수는 **{strength} 모습**을 보입니다. "
    + ("" if pd.isna(corr) else f"(함께 움직이는 정도 = {corr:.2f}, 1에 가까울수록 나란히 커진다는 뜻)")
)

# 스크린 수는 비슷한데 결과가 크게 갈린 영화 찾아보기
if len(plot_df) >= 10:
    # 스크린 수 상위 25%에 드는 영화들 중에서
    scrn_cut = plot_df["first_scrn"].quantile(0.75)
    big_scrn = plot_df[plot_df["first_scrn"] >= scrn_cut]

    if len(big_scrn) >= 2:
        win = big_scrn.loc[big_scrn["total_audi"].idxmax()]
        lose = big_scrn.loc[big_scrn["total_audi"].idxmin()]

        st.info(
            f"🔍 스크린을 많이 잡았다고 결과가 같지는 않습니다. "
            f"스크린 **{scrn_cut:,.0f}개 이상**으로 출발한 영화들 가운데 "
            f"**{win['movieNm']}**는 스크린 {win['first_scrn']:,.0f}개로 "
            f"{win['total_audi']:,.0f}명을 모은 반면, "
            f"**{lose['movieNm']}**는 스크린 {lose['first_scrn']:,.0f}개로 "
            f"{lose['total_audi']:,.0f}명에 그쳤습니다."
        )

st.caption(
    "💭 두 값이 함께 커진다고 해서 '스크린이 관객을 만들었다'고 단정할 수는 없습니다. "
    "기대작일수록 스크린을 많이 배정받는다는 점도 함께 생각해 보세요."
)

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 개봉일 스크린 수가 많은 영화일수록 총 관객도 많은 편이지만, 같은 스크린 수에서도 결과 차이가 크다.",
    key="insight_4",
    height=80,
)

st.divider()

st.caption("데이터 출처: 영화진흥위원회(KOBIS) 박스오피스 자료 재가공")
