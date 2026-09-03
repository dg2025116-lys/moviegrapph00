import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

    # 날짜에서 쓸 만한 조각들을 미리 뽑아 둔다
    df["year"] = df["openDt"].dt.year
    df["month"] = df["openDt"].dt.month
    df["ym"] = df["openDt"].dt.to_period("M").astype(str)   # 예: '2023-07'
    df["weekday"] = df["openDt"].dt.dayofweek               # 월=0 ... 일=6

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


# ============================================================
# 그래프 5 — 장르별 총 관객 상자 그림 (10편 이상 장르만)
# ============================================================
st.header("5️⃣ 장르별 관객 수의 허리와 꼬리")
st.write(
    "상자 하나가 장르 하나입니다. "
    "**상자 안쪽**에 그 장르 영화의 절반이 들어 있고, "
    "**상자 밖으로 튀어나온 점**은 유난히 관객이 많거나 적었던 영화입니다."
)

box_base = df[df["total_audi"].notna()].copy()

# 편수가 적은 장르는 상자가 신뢰하기 어려우므로 걸러 낸다
MIN_COUNT = 10
genre_size = box_base["genre"].value_counts()
kept_genres = genre_size[genre_size >= MIN_COUNT].index.tolist()

box_df = box_base[box_base["genre"].isin(kept_genres)].copy()

# 중앙값이 큰 장르부터 왼쪽에 놓기 (읽기 쉽게)
order = (
    box_df.groupby("genre")["total_audi"]
    .median()
    .sort_values(ascending=False)
    .index.tolist()
)

fig5 = px.box(
    box_df,
    x="genre",
    y="total_audi",
    color="genre",
    category_orders={"genre": order},
    points="outliers",                  # 튀는 점만 찍기
    hover_name="movieNm",               # 점에 마우스를 올리면 영화명
    hover_data={
        "genre": False,
        "nation": True,
        "total_audi": ":,",
        "days_in_top10": True,
    },
    labels={
        "genre": "장르",
        "total_audi": "총 관객 수(명)",
        "nation": "제작 국가",
        "days_in_top10": "10위권 머문 날수",
    },
    color_discrete_sequence=px.colors.qualitative.Pastel,
)

fig5.update_traces(
    marker=dict(size=9, line=dict(color="#444", width=1)),
    line=dict(width=2),
)

fig5.update_layout(
    title=f"장르별 총 관객 수 분포 (영화 {MIN_COUNT}편 이상인 장르만)",
    xaxis_title="장르",
    yaxis_title="총 관객 수(명)",
    height=620,
    showlegend=False,
)

st.plotly_chart(fig5, use_container_width=True)

st.caption(
    "🖱️ 상자 밖에 홀로 떨어진 점에 마우스를 올려 보세요. 그 장르의 '유별난 영화'가 누구인지 알 수 있습니다."
)


# ------------------------------------------------------------
# 상자 그림에서 읽어 낸 사실을 문구로 정리
# ------------------------------------------------------------

# 걸러진 장르 안내
dropped = genre_size[genre_size < MIN_COUNT]
c1, c2, c3 = st.columns(3)
c1.metric("그린 장르 수", f"{len(kept_genres)} 개")
c2.metric("그린 영화 편수", f"{len(box_df):,} 편")
c3.metric("제외된 장르 수", f"{len(dropped)} 개")

# 중앙값이 가장 큰 장르 / 가장 작은 장르
med_by_genre = box_df.groupby("genre")["total_audi"].median().sort_values()
low_g, low_v = med_by_genre.index[0], med_by_genre.iloc[0]
high_g, high_v = med_by_genre.index[-1], med_by_genre.iloc[-1]

st.success(
    f"📌 가운뎃값(중앙값)이 가장 높은 장르는 **{high_g}**({high_v:,.0f}명), "
    f"가장 낮은 장르는 **{low_g}**({low_v:,.0f}명)입니다. "
    f"두 장르의 '보통 영화'는 관객 수가 약 **{high_v / low_v:.1f}배** 차이 납니다."
)


# 각 장르에서 위쪽으로 튀어나온 영화(상단 이상치)를 직접 찾아보기
def find_upper_outliers(group: pd.DataFrame) -> pd.DataFrame:
    """상자 위쪽 수염을 넘어선 영화들을 골라낸다."""
    q1 = group["total_audi"].quantile(0.25)
    q3 = group["total_audi"].quantile(0.75)
    iqr = q3 - q1                       # 상자의 높이
    fence = q3 + 1.5 * iqr              # 위쪽 수염의 끝
    return group[group["total_audi"] > fence]


outlier_rows = []
for g in order:
    part = box_df[box_df["genre"] == g]
    outs = find_upper_outliers(part)
    for _, r in outs.iterrows():
        outlier_rows.append(
            {
                "장르": g,
                "영화명": r["movieNm"],
                "총 관객": int(r["total_audi"]),
                "제작 국가": r["nation"],
                "10위권 머문 날수": int(r["days_in_top10"])
                if pd.notna(r["days_in_top10"])
                else None,
            }
        )

if outlier_rows:
    outlier_df = pd.DataFrame(outlier_rows).sort_values(
        "총 관객", ascending=False
    )
    st.info(
        f"🔍 상자 위쪽으로 튀어나온 영화가 모두 **{len(outlier_df)}편** 있습니다. "
        "같은 장르 안에서도 유독 크게 성공한 영화들입니다."
    )
    st.dataframe(
        outlier_df.style.format({"총 관객": "{:,}"}),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("🔍 상자 밖으로 크게 튀어나온 영화가 없습니다.")

if len(dropped) > 0:
    st.caption(
        f"💭 영화가 {MIN_COUNT}편 미만이라 제외한 장르: "
        + ", ".join(f"{g}({n}편)" for g, n in dropped.items())
        + " — 표본이 적으면 상자 모양을 믿기 어렵기 때문입니다."
    )

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 장르마다 '보통 영화'의 관객 수가 다르고, 어떤 장르는 몇몇 대박작이 위로 크게 튀어나와 있다.",
    key="insight_5",
    height=80,
)

st.divider()


# ============================================================
# 그래프 6 — 버블 그래프 (점 크기 = 첫 주 관객)
# ============================================================
st.header("6️⃣ 같은 산점도에 '첫 주 성적'을 얹으면")
st.write(
    "4번 그래프와 가로·세로축은 똑같습니다. "
    "다만 **점의 크기가 개봉 첫 주 관객 수**입니다. "
    "축 두 개 + 색 + 크기, 네 가지 정보를 한 화면에서 봅니다."
)

bubble_df = df[
    df["first_scrn"].notna()
    & df["total_audi"].notna()
    & df["first_week_audi"].notna()
    & (df["first_week_audi"] > 0)      # 크기가 0이면 점이 사라져서 제외
].copy()

bc1, bc2 = st.columns(2)

with bc1:
    bubble_genres = st.multiselect(
        "보고 싶은 장르 고르기 (비워 두면 전체)",
        options=sorted(bubble_df["genre"].unique()),
        default=[],
        key="bubble_genre_pick",
    )

with bc2:
    max_bubble = st.slider(
        "가장 큰 점의 크기",
        min_value=20,
        max_value=90,
        value=55,
        step=5,
        help="점이 서로 겹쳐 답답하면 작게, 크기 차이를 크게 보고 싶으면 크게 조절하세요.",
        key="bubble_size",
    )

if bubble_genres:
    bub_plot = bubble_df[bubble_df["genre"].isin(bubble_genres)]
else:
    bub_plot = bubble_df

fig6 = px.scatter(
    bub_plot,
    x="first_scrn",
    y="total_audi",
    size="first_week_audi",              # ← 점 크기 = 첫 주 관객
    size_max=max_bubble,
    color="genre",
    hover_name="movieNm",
    hover_data={
        "genre": True,
        "nation": True,
        "first_scrn": ":,",
        "first_week_audi": ":,",
        "total_audi": ":,",
        "days_in_top10": True,
    },
    labels={
        "first_scrn": "개봉일 스크린 수(개)",
        "total_audi": "총 관객 수(명)",
        "first_week_audi": "개봉 첫 주 관객(명)",
        "genre": "장르",
        "nation": "제작 국가",
        "days_in_top10": "10위권 머문 날수",
    },
    color_discrete_sequence=px.colors.qualitative.Set2,
    opacity=0.65,
)

fig6.update_traces(marker=dict(line=dict(color="white", width=1)))

fig6.update_layout(
    title="스크린 수 · 총 관객 · 첫 주 관객을 한눈에 (점이 클수록 첫 주 관객이 많음)",
    xaxis_title="개봉일 스크린 수(개)",
    yaxis_title="총 관객 수(명)",
    height=640,
    legend_title_text="장르",
)

st.plotly_chart(fig6, use_container_width=True)


# ------------------------------------------------------------
# 버블 그래프에서 읽어 낸 사실을 문구로 정리
# ------------------------------------------------------------

# '첫 주 이후에 얼마나 더 벌었나'를 나타내는 값 (배수)
bub_calc = bub_plot.copy()
bub_calc["후반_배수"] = bub_calc["total_audi"] / bub_calc["first_week_audi"]

mc1, mc2, mc3 = st.columns(3)
mc1.metric("그린 영화 편수", f"{len(bub_plot):,} 편")
mc2.metric(
    "첫 주 관객 ↔ 총 관객",
    f"{bub_plot['first_week_audi'].corr(bub_plot['total_audi']):.2f}",
)
mc3.metric(
    "첫 주 이후 배수의 중앙값",
    f"{bub_calc['후반_배수'].median():.1f} 배",
)

if len(bub_calc) >= 5:
    # 첫 주는 작았는데 끝까지 오래 간 영화 (점이 작은데 위에 있는 영화)
    slow_burn = bub_calc.loc[bub_calc["후반_배수"].idxmax()]
    # 첫 주에 몰렸다가 금방 식은 영화 (점이 큰데 생각보다 낮은 영화)
    front_load = bub_calc.loc[bub_calc["후반_배수"].idxmin()]

    st.success(
        f"📌 **{slow_burn['movieNm']}**는 첫 주에 {slow_burn['first_week_audi']:,.0f}명이었지만 "
        f"최종 {slow_burn['total_audi']:,.0f}명까지 늘어 **{slow_burn['후반_배수']:.1f}배**가 되었습니다. "
        f"작은 점이 높이 올라간, 입소문으로 오래 간 영화입니다."
    )
    st.info(
        f"🔍 반대로 **{front_load['movieNm']}**는 첫 주 {front_load['first_week_audi']:,.0f}명에서 "
        f"최종 {front_load['total_audi']:,.0f}명으로 **{front_load['후반_배수']:.1f}배**에 그쳤습니다. "
        f"초반에 관객이 몰렸다가 빠르게 식은 쪽입니다."
    )

st.caption(
    "💭 **큰 점이 아래쪽에 있으면** 첫 주에 반짝했다가 식은 영화, "
    "**작은 점이 위쪽에 있으면** 조용히 시작해 길게 간 영화입니다. 그런 점을 찾아보세요."
)

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 첫 주 관객이 많은 영화가 대체로 총 관객도 많지만, 작게 출발해 크게 자란 영화도 있다.",
    key="insight_6",
    height=80,
)

st.divider()


# ============================================================
# 그래프 7 — 제작 국가 → 장르 선버스트 (크기 = 영화 편수)
# ============================================================
st.header("7️⃣ 나라에서 장르로 내려가 보기")
st.write(
    "가운데가 **제작 국가**, 바깥 고리가 그 나라의 **장르**입니다. "
    "조각의 크기는 **영화 편수**입니다."
)

sun_df = df[df["nation"].notna() & df["genre"].notna()].copy()

# 국가-장르 조합별 편수를 미리 세어 둔다
sun_count = (
    sun_df.groupby(["nation", "genre"])
    .size()
    .reset_index(name="편수")
)

fig7 = px.sunburst(
    sun_count,
    path=["nation", "genre"],           # 안쪽 → 바깥쪽
    values="편수",                       # 조각의 크기
    color="nation",
    color_discrete_sequence=px.colors.qualitative.Pastel1,
    labels={"nation": "제작 국가", "genre": "장르", "편수": "영화 편수"},
)

fig7.update_traces(
    textinfo="label+percent parent",     # 부모 조각 대비 비율
    insidetextorientation="radial",
    hovertemplate=(
        "<b>%{label}</b><br>"
        "영화 편수: %{value}편<br>"
        "전체에서 차지하는 비율: %{percentRoot:.1%}<br>"
        "한 단계 위 대비: %{percentParent:.1%}"
        "<extra></extra>"
    ),
    marker=dict(line=dict(color="white", width=2)),
)

fig7.update_layout(
    title="제작 국가 → 장르별 영화 편수",
    height=680,
    margin=dict(t=60, l=10, r=10, b=10),
)

st.plotly_chart(fig7, use_container_width=True)

st.caption("🖱️ 안쪽 국가 조각을 클릭하면 그 나라만 펼쳐 볼 수 있고, 가운데를 누르면 되돌아옵니다.")


# ------------------------------------------------------------
# 선버스트에서 읽어 낸 사실을 문구로 정리
# ------------------------------------------------------------

nation_count = sun_df["nation"].value_counts()
top_nation = nation_count.index[0]
top_nation_n = int(nation_count.iloc[0])

sc1, sc2, sc3 = st.columns(3)
sc1.metric("제작 국가 수", f"{sun_df['nation'].nunique()} 개")
sc2.metric("가장 많은 나라", f"{top_nation}")
sc3.metric(
    f"{top_nation} 비중",
    f"{top_nation_n / len(sun_df) * 100:.1f}%",
)

st.success(
    f"📌 216편 가운데 **{top_nation}** 영화가 **{top_nation_n}편**"
    f"({top_nation_n / len(sun_df) * 100:.1f}%)으로 가장 많습니다."
)

# 편수가 많은 상위 나라들의 '대표 장르'를 뽑아 비교
main_nations = nation_count[nation_count >= 5].index.tolist()
if len(main_nations) >= 2:
    lines = []
    for n in main_nations[:5]:
        part = sun_df[sun_df["nation"] == n]
        g = part["genre"].value_counts()
        lines.append(
            f"- **{n}** ({len(part)}편) → 가장 많은 장르는 "
            f"**{g.index[0]}** ({int(g.iloc[0])}편, {g.iloc[0] / len(part) * 100:.0f}%)"
        )
    st.info("🔍 나라마다 주력 장르가 다릅니다.\n\n" + "\n".join(lines))

st.caption(
    "💭 1번 도넛은 장르만, 이 선버스트는 '나라 안의 장르'를 봅니다. "
    "같은 장르라도 어느 나라 작품이 많은지 확인해 보세요."
)

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 한국 영화는 장르가 고르게 퍼져 있는 반면, 어떤 나라는 특정 장르에 몰려 있다.",
    key="insight_7",
    height=80,
)

st.divider()


# ============================================================
# 그래프 8 — 월별 개봉 편수와 관객 추이 (막대 + 선, 축 두 개)
# ============================================================
st.header("8️⃣ 언제 개봉하느냐가 중요할까?")
st.write(
    "드디어 **개봉일(openDt)** 을 씁니다. "
    "**막대는 그 달에 개봉한 편수**, **선은 그 달 개봉작들이 모은 총 관객 합계**입니다. "
    "두 값은 단위가 완전히 다르므로 **세로축을 왼쪽·오른쪽 두 개** 씁니다."
)

time_df = df[df["openDt"].notna() & df["total_audi"].notna()].copy()

# 시간을 어떤 단위로 묶을지 고르게 하기
unit = st.radio(
    "시간을 묶는 단위",
    options=["연-월 순서대로", "월(1~12월)로 합치기"],
    index=0,
    horizontal=True,
    help=(
        "'연-월'은 실제 흐른 시간 그대로 보고, "
        "'월로 합치기'는 여러 해의 같은 달을 한 칸에 모아 계절성을 봅니다."
    ),
    key="time_unit",
)

if unit == "연-월 순서대로":
    key_col = "ym"
    monthly = (
        time_df.groupby(key_col)
        .agg(편수=("movieCd", "count"), 총관객=("total_audi", "sum"))
        .reset_index()
        .sort_values(key_col)            # 문자열이지만 'YYYY-MM'이라 정렬이 맞음
    )
    x_vals = monthly[key_col]
    x_title = "개봉 연-월"
else:
    key_col = "month"
    monthly = (
        time_df.groupby(key_col)
        .agg(편수=("movieCd", "count"), 총관객=("total_audi", "sum"))
        .reset_index()
        .sort_values(key_col)
    )
    x_vals = monthly[key_col].astype(str) + "월"
    x_title = "개봉 월"

# 편당 평균 관객도 함께 구해 둔다 (편수가 많아서 합계가 큰 건지 구분하려고)
monthly["편당평균"] = monthly["총관객"] / monthly["편수"]

# 축이 두 개인 그래프 만들기
fig8 = make_subplots(specs=[[{"secondary_y": True}]])

# (1) 막대 — 개봉 편수 (왼쪽 축)
fig8.add_trace(
    go.Bar(
        x=x_vals,
        y=monthly["편수"],
        name="개봉 편수",
        marker=dict(color="#A8C5DD", line=dict(color="white", width=1)),
        hovertemplate="<b>%{x}</b><br>개봉 편수: %{y}편<extra></extra>",
    ),
    secondary_y=False,
)

# (2) 선 — 총 관객 합계 (오른쪽 축)
fig8.add_trace(
    go.Scatter(
        x=x_vals,
        y=monthly["총관객"],
        name="총 관객 합계",
        mode="lines+markers",
        line=dict(color="crimson", width=3),
        marker=dict(size=10, line=dict(color="white", width=1)),
        hovertemplate="<b>%{x}</b><br>총 관객 합계: %{y:,.0f}명<extra></extra>",
    ),
    secondary_y=True,
)

fig8.update_xaxes(title_text=x_title, tickangle=-45)
fig8.update_yaxes(title_text="개봉 편수(편)", secondary_y=False)
fig8.update_yaxes(
    title_text="총 관객 합계(명)", secondary_y=True, showgrid=False
)

fig8.update_layout(
    title="월별 개봉 편수(막대)와 총 관객 합계(선)",
    height=600,
    hovermode="x unified",              # 같은 x를 한꺼번에 보여 주기
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    bargap=0.25,
)

st.plotly_chart(fig8, use_container_width=True)


# ------------------------------------------------------------
# 월별 추이에서 읽어 낸 사실을 문구로 정리
# ------------------------------------------------------------

busiest = monthly.loc[monthly["편수"].idxmax()]        # 가장 많이 개봉한 달
richest = monthly.loc[monthly["총관객"].idxmax()]      # 관객이 가장 많았던 달
efficient = monthly.loc[monthly["편당평균"].idxmax()]  # 편당 평균이 가장 높은 달

label_col = key_col
def label_of(row):
    return f"{row[label_col]}월" if key_col == "month" else str(row[label_col])

t1, t2, t3 = st.columns(3)
t1.metric("가장 많이 개봉한 달", label_of(busiest), f"{int(busiest['편수'])}편")
t2.metric("관객이 가장 많았던 달", label_of(richest), f"{richest['총관객']:,.0f}명")
t3.metric("편당 평균이 가장 높은 달", label_of(efficient), f"{efficient['편당평균']:,.0f}명")

if label_of(busiest) == label_of(richest):
    st.success(
        f"📌 **{label_of(busiest)}**은 개봉 편수도({int(busiest['편수'])}편) "
        f"관객 합계도({busiest['총관객']:,.0f}명) 가장 높았습니다. "
        f"많이 개봉했고, 관객도 많이 들었던 달입니다."
    )
else:
    st.success(
        f"📌 가장 많이 개봉한 달은 **{label_of(busiest)}**({int(busiest['편수'])}편)이지만, "
        f"관객이 가장 많았던 달은 **{label_of(richest)}**"
        f"({richest['총관객']:,.0f}명)로 서로 다릅니다. "
        f"**많이 개봉한다고 관객이 많아지는 것은 아니라는 뜻**입니다."
    )

st.info(
    f"🔍 편당 평균 관객이 가장 높은 달은 **{label_of(efficient)}**로, "
    f"영화 한 편이 평균 **{efficient['편당평균']:,.0f}명**을 모았습니다. "
    f"(개봉 {int(efficient['편수'])}편) "
    f"막대는 낮은데 선이 높은 달이 있다면, 그달엔 소수의 큰 흥행작이 있었다는 신호입니다."
)

with st.expander("📊 월별 숫자 표로 보기"):
    show_tbl = monthly.copy()
    show_tbl = show_tbl.rename(columns={key_col: x_title})
    show_tbl["편당평균"] = show_tbl["편당평균"].round(0)
    st.dataframe(
        show_tbl.style.format({"총관객": "{:,.0f}", "편당평균": "{:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "💭 축이 두 개인 그래프는 편리하지만 조심해야 합니다. "
    "오른쪽 축의 범위를 어떻게 잡느냐에 따라 선이 막대보다 높아 보이거나 낮아 보이거든요. "
    "**두 축의 눈금은 서로 비교할 수 있는 것이 아닙니다.**"
)

# --- 이 그래프로 알 수 있는 것 ---
st.subheader("💡 이 그래프로 알 수 있는 것")
st.text_area(
    "한 문장으로 정리해 보세요.",
    placeholder="예) 개봉 편수가 많은 달과 관객이 많은 달이 항상 같지는 않고, 특정 달에 흥행작이 몰려 있다.",
    key="insight_8",
    height=80,
)

st.divider()

st.caption("데이터 출처: 영화진흥위원회(KOBIS) 박스오피스 자료 재가공")
