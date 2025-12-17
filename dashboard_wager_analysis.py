from pathlib import Path
from volta_stats import calc_volta_stats
import streamlit as st
import streamlit.components.v1 as components
import base64
import pandas as pd
import requests
import json
import platform
from datetime import datetime
from tqdm import tqdm
from pathlib import Path

# ================================
#  기본 설정 & 경로
# ================================
API_KEY = "live_7a611a04eeb1ac043f43a92245935f274608d65acac4fcb584f1baad81aa8bd7efe8d04e6d233bd35cf2fabdeb93fb0d"
HEADERS = {"x-nxopen-api-key": API_KEY}

# OS별 BASE_DIR (세준 환경 기준)


#if platform.system() == "Windows":
#    BASE_DIR = Path("C:/Users/junab/OneDrive/py/FC ONLINE")
#else:
#    BASE_DIR = Path("/Users/kimsejune/OneDrive/py/FC ONLINE")


BASE_DIR = Path(__file__).resolve().parent

WORLDCUP_DETAIL_JSON_PATH = BASE_DIR / "worldcup_detailed.json"
NICKNAME_MAP_PATH = BASE_DIR / "nickname_map.json"


st.set_page_config(
    page_title="FC ONLINE 월드컵 결과 대시보드",
    layout="wide",
)

st.title("FC ONLINE 월드컵 결과 대시보드 Presented by Sejune PC")
st.caption("2026년 월드컵 경기부터 공식적으로 반영합니다.")


# ================================
#  데이터 로딩 함수
# ================================
@st.cache_data(ttl=3600)
def load_worldcup_matches():
    if not WORLDCUP_DETAIL_JSON_PATH.exists():
        st.error("❌ worldcup_detailed.json 파일이 없습니다. 먼저 run.py로 월드컵 경기를 저장해주세요.")
        return []
    with open(WORLDCUP_DETAIL_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=3600)
def load_nickname_map():
    if not NICKNAME_MAP_PATH.exists():
        st.error("❌ nickname_map.json 파일이 없습니다. 먼저 refresh_nickname_map.py를 실행해주세요.")
        return {}
    with open(NICKNAME_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=3600)
def load_division_meta():
    """
    등급 메타데이터 조회
    """
    url = "https://open.api.nexon.com/static/fconline/meta/division.json"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        items = res.json()

        division_map = {}
        for item in items:
            div_id = item.get("divisionId") or item.get("division")
            div_name = item.get("divisionName") or item.get("name")
            if div_id and div_name:
                division_map[div_id] = div_name
        return division_map
    except Exception as e:
        st.warning(f"⚠️ 등급 메타데이터 조회 실패: {e}")
        return {}

@st.cache_data(ttl=3600)
def fetch_match_detail(match_id: str):
    url = f"https://open.api.nexon.com/fconline/v1/match-detail?matchid={match_id}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json()
    else:
        st.warning(f"⚠️ matchId {match_id} 조회 실패: {res.status_code}")
        return None

@st.cache_data(ttl=3600)
def fetch_official_max_division(ouid: str):
    """
    특정 유저(ouid)의 '역대 최고 공식경기 등급' 조회
    """
    url = "https://open.api.nexon.com/fconline/v1/user/maxdivision"
    try:
        res = requests.get(url, headers=HEADERS, params={"ouid": ouid}, timeout=5)
        if res.status_code != 200:
            st.warning(f"⚠️ 최고 등급 조회 실패 (ouid={ouid}): {res.status_code} {res.text}")
            return None

        items = res.json()
        if not isinstance(items, list):
            return None

        official = [d for d in items if d.get("matchType") == 50]
        if not official:
            return None

        best = official[0]
        return {
            "division": best.get("division"),
            "achievementDate": best.get("achievementDate"),
        }
    except Exception as e:
        st.warning(f"⚠️ 최고 등급 조회 중 오류 (ouid={ouid}): {e}")
        return None

def extract_player_stats(detail_data: dict):
    """match-detail 응답에서 유저별 주요 스탯 추출"""
    records = []
    for player in detail_data.get("matchInfo", []):
        try:
            records.append(
                {
                    "ouid": player.get("ouid"),
                    "matchResult": player.get("matchDetail", {}).get("matchResult"),
                    "goals": player.get("shoot", {}).get("goalTotal", 0),
                    "shots": player.get("shoot", {}).get("shootTotal", 0),
                    "fouls": player.get("matchDetail", {}).get("foul", 0),
                    "possession": player.get("pass", {}).get("possession", 0),
                }
            )
        except:
            continue
    return records


# ================================
#  1. RAW 데이터 로딩
# ================================
raw_matches = load_worldcup_matches()
nickname_map = load_nickname_map()

if not raw_matches or not nickname_map:
    st.stop()

all_records = []

with st.spinner("어차피 우승은 들을엉..."):
    for m in tqdm(raw_matches):
        match_id = m["matchId"]
        detail = fetch_match_detail(match_id)
        if detail:
            match_time = m["date"]
            for rec in extract_player_stats(detail):
                rec["matchId"] = match_id
                rec["date"] = match_time
                all_records.append(rec)

if not all_records:
    st.error("❗ 매치 상세 데이터가 없습니다.")
    st.stop()

data = pd.DataFrame(all_records)
data["nickname"] = data["ouid"].map(nickname_map).fillna(data["ouid"])

data["date"] = pd.to_datetime(data["date"], errors="coerce")

filtered = data.copy()

# ================================
#  3. 요약 통계 계산
# ================================
def win_count(series):
    return series.isin(["승", "WINNER"]).sum()

summary = (
    filtered.groupby("nickname")
    .agg(
        games_played=("matchId", "count"),
        wins=("matchResult", win_count),
        total_goals=("goals", "sum"),
        total_shots=("shots", "sum"),
        total_fouls=("fouls", "sum"),
        avg_possession=("possession", "mean"),
    )
).reset_index()

summary["win_rate"] = summary["wins"] / summary["games_played"] * 100


# ================================
#  유저별 최고 공식경기 등급 조회
# ================================

OUR_OUID_MAP = {
    "40260d503f67f41c85ad1fbb6bf97fae": "들을엉",
    "2fe7767c06e059a2593e2ec5747ca28b": "희미한연기",
    "970686025f32d1af9205cb93cce0ed0e": "호랑이소굴로들가",
    "abdee2cf7166a82cc746fe903ba131d9": "서울의환호",
    "8ae71939629a719da141318475d8f1da": "서울시마포구",
    "6fcf2b3f3ac52bf388e3cc9a1bba1f68": "200000000"
}

division_meta = load_division_meta()
nickname_to_ouid = {nick: ouid for ouid, nick in nickname_map.items()}

max_division_rows = []

for nick in summary["nickname"]:
    ouid = nickname_to_ouid.get(nick)
    if not ouid:
        continue

    info = fetch_official_max_division(ouid)
    if not info:
        continue

    div_code = info["division"]
    div_name = division_meta.get(div_code, str(div_code))

    max_division_rows.append({
        "nickname": nick,
        "division_code": div_code,
        "division_name": div_name,
        "achievementDate": info.get("achievementDate")
    })

    # 고정 6명 기준 DF
base_df = pd.DataFrame({
    "nickname": list(OUR_OUID_MAP.values())
})

# 공식경기 기록 DF
division_df = pd.DataFrame(
    max_division_rows,
    columns=["nickname", "division_code", "division_name", "achievementDate"]
)

# LEFT JOIN → 6명 고정
max_division_df = base_df.merge(
    division_df,
    on="nickname",
    how="left"
)

# 공식경기 없는 유저 처리
max_division_df["division_name"] = max_division_df["division_name"].fillna("공식경기 기록 없음")
max_division_df["division_code"] = max_division_df["division_code"].fillna(999)
max_division_df["achievementDate"] = max_division_df["achievementDate"].fillna("N/A")

# ================================
#  월드컵 KPI
# ================================
WORLD_CUP_FIRST_WINNER = "들을엉"
WORLD_CUP_RECENT_WINNER = None
WORLD_CUP_MOST_WINNER = None

k1, k2, k3 = st.columns(3)

k1.metric(
    label="🏆 월드컵 초대 우승자 & 웹 개발자",
    value=WORLD_CUP_FIRST_WINNER
)

k2.metric(
    label="최근 월드컵 우승자",
    value=WORLD_CUP_RECENT_WINNER or "미정 (26년도 개최)"
)

k3.metric(
    label="최다 월드컵 우승자",
    value=WORLD_CUP_MOST_WINNER or "미정 (26년도 개최)"
)

# ================================
#  탭 구성
# ================================
tab_overview, tab_compare, tab_volta, tab_matches = st.tabs(
    [" 1vs1 공식경기 등급", " 1vs1 월드컵 비교", " Volta 공식경기 지표", " Raw Data"]
)


# ---------- 탭 1: 공경 명예의 전장 ----------
with tab_overview:

    st.subheader("1vs1 공식경기 명예의 전당 Presented by Sejune inc.")
    st.caption("공식경기 기록이 없는 유저는 증명사진으로 대체됩니다")


    TIER_ICON_DIR = BASE_DIR / "assets" / "tier_icons"

    # -------------------------------
    # 이미지 → base64 변환
    # -------------------------------
    def image_to_base64(img_path: Path):
        if img_path is None or not img_path.exists():
            return None
        with open(img_path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()

    # -------------------------------
    # 티어 → 아이콘 경로
    # -------------------------------
    def get_tier_icon_path(name: str, nickname: str = None):
        if name == "공식경기 기록 없음":
            if nickname == "희미한연기":
                return TIER_ICON_DIR / "no.jpg"
            if nickname == "호랑이소굴로들가":
                return TIER_ICON_DIR / "ahn.jpg"
            return None  # 혹시 모를 예외
    
        if "챔피언스" in name:
            return TIER_ICON_DIR / "champions.png"
        if "슈퍼챌린지" in name:
            return TIER_ICON_DIR / "super_challenger.png"
        if "월드클래스1" in name:
            return TIER_ICON_DIR / "worldclass_1.png"
        if "월드클래스2" in name:
            return TIER_ICON_DIR / "worldclass_2.png"
        if "월드클래스3" in name:
            return TIER_ICON_DIR / "worldclass_3.png"
        if "프로1" in name:
            return TIER_ICON_DIR / "pro_1.png"
        if "프로2" in name:
            return TIER_ICON_DIR / "pro_2.png"
        return None

    # -------------------------------
    # 티어 → 컬러
    # -------------------------------
    def get_tier_color(name: str):
        if "챔피언스" in name:
            return "#ff4d4f"
        if "슈퍼챌린지" in name:
            return "#00e5d4"
        if "챌린저" in name:
            return "#00c2b3"
        if "월드클래스" in name:
            return "#8a5cff"
        if "프로" in name:
            return "#f5b041"
        return "#5f6368"  # 기록 없음

    # -------------------------------
    # 데이터 없을 경우
    # -------------------------------
    if max_division_df.empty:
        st.info("최고 공식경기 등급 데이터를 불러올 수 없습니다.")
        st.stop()

    # -------------------------------
    # 공식경기 보유 여부 + 정렬
    # -------------------------------
    max_division_df["has_official"] = max_division_df["division_code"] != 999

    hall_df = (
        max_division_df
        .sort_values(
            by=["has_official", "division_code"],
            ascending=[False, True]
        )
        .reset_index(drop=True)
    )

    # -------------------------------
    # 카드 렌더링
    # -------------------------------
    cards_html = ""
    official_rank = 0

    for _, row in hall_df.iterrows():

        # 랭킹 표시
        if row["division_code"] == 999:
            rank_label = "#NULL"
        else:
            official_rank += 1
            rank_label = f"#{official_rank}"

        color = get_tier_color(row["division_name"])

        icon_path = get_tier_icon_path(row["division_name"],row["nickname"])
        icon_base64 = image_to_base64(icon_path)

        icon_html = ""
        if icon_base64:
            icon_html = f"""
            <img src="{icon_base64}"
                width="56"
                style="margin-right:16px;">
            """

        cards_html += f"""
        <div style="
            background:#0e1117;
            border-left:6px solid {color};
            padding:16px;
            margin-bottom:14px;
            border-radius:14px;
            box-shadow:0 0 10px rgba(0,0,0,.4);
            transition:transform .2s, box-shadow .2s;
        " onmouseover="
            this.style.transform='scale(1.02)';
            this.style.boxShadow='0 0 18px rgba(255,255,255,0.15)';
        "
        onmouseout="
            this.style.transform='scale(1)';
            this.style.boxShadow='0 0 10px rgba(0,0,0,.4)';
        ">
            <div style="display:flex;align-items:center;">
                {icon_html}
                <div>
                    <div style="color:white;font-weight:700;font-size:16px;">
                        {rank_label} {row['nickname']}
                    </div>
                    <div style="color:{color};font-weight:700;">
                        {row['division_name']}
                    </div>
                    <div style="color:#9aa0a6;font-size:12px;">
                        달성일: {row['achievementDate']}
                    </div>
                </div>
            </div>
        </div>
        """

    components.html(cards_html, height=650, scrolling=False)

    st.markdown("---")

  
    # =============================
    # 요약 테이블
    # =============================
    st.subheader(" 유저별 요약 통계")
    st.dataframe(summary, use_container_width=True)

# ---------- 탭 2: 월드컵 유저 비교 ----------
with tab_compare:
    st.subheader("월드컵 지표 비교")
    st.caption("누가 더 잘했나 비교해봅시다.")

    if len(summary) < 2:
        st.info("비교 가능한 유저가 2명 이상 필요합니다.")
    else:
        left, right = st.columns(2)
        user1 = left.selectbox("플레이어 1", summary["nickname"])
        user2 = right.selectbox("플레이어 2", summary["nickname"])

        s1 = summary[summary["nickname"] == user1].iloc[0]
        s2 = summary[summary["nickname"] == user2].iloc[0]

        c1, c2 = st.columns(2)
        c1.metric(f"{user1} 승률", f"{s1['win_rate']:.1f}%")
        c1.metric(f"{user1} 평균 득점", f"{s1['total_goals'] / s1['games_played']:.2f}")

        c2.metric(f"{user2} 승률", f"{s2['win_rate']:.1f}%")
        c2.metric(f"{user2} 평균 득점", f"{s2['total_goals'] / s2['games_played']:.2f}")

        st.markdown("##### RAW DATA")
        comp = filtered[filtered["nickname"].isin([user1, user2])]
        st.dataframe(comp, use_container_width=True)

# ---------- 탭 3: 볼타 공식 ----------
with tab_volta:

    st.subheader("Volta 공식경기 명예의 전당 Presented by Sejune inc.")
    st.caption("최근 2개월, 50경기 기준입니다.")

    import json
    import pandas as pd
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent
    VOLTA_JSON_PATH = BASE_DIR / "volta_matches.json"

    # ------------------------------
    # 데이터 로드
    # ------------------------------
    if not VOLTA_JSON_PATH.exists():
        st.error("❌ volta_matches.json 파일이 없습니다. 먼저 volta_run.py를 실행하세요.")
        st.stop()

    raw = json.load(open(VOLTA_JSON_PATH, encoding="utf-8"))
    df = pd.DataFrame(raw)

    if df.empty:
        st.info("표시할 볼타 공식경기 데이터가 없습니다.")
        st.stop()

    # ------------------------------
    # 타입 정리
    # ------------------------------
    df["date"] = pd.to_datetime(df["date"])

    numeric_cols = ["goal", "assist", "block", "rating"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # =====================================================
    # 1. 개인별 누적 스탯
    # =====================================================
    stats_df = (
        df
        .groupby(["ouid", "nickname"], as_index=False)
        .agg(
            games=("matchId", "count"),
            win=("matchResult", lambda x: (x == "승").sum()),
            draw=("matchResult", lambda x: (x == "무").sum()),
            lose=("matchResult", lambda x: (x == "패").sum()),
            goal=("goal", "sum"),
            assist=("assist", "sum"),
            block=("block", "sum"),
            avg_rating=("rating", "mean"),
        )
    )

    stats_df["win_rate"] = (stats_df["win"] / stats_df["games"] * 100).round(1)
    stats_df["avg_rating"] = stats_df["avg_rating"].round(2)

    # ------------------------------
    # 평균 스탯 (KPI용)
    # ------------------------------
        
    # ---------- 평균 스탯 계산 ----------
    stats_df["avg_goal"] = (stats_df["goal"] / stats_df["games"]).round(2)
    stats_df["avg_assist"] = (stats_df["assist"] / stats_df["games"]).round(2)
    stats_df["avg_block"] = (stats_df["block"] / stats_df["games"]).round(2)

    # ---------- MVP / 패배범인 ----------
    mvp = stats_df.sort_values("avg_rating", ascending=False).iloc[0]
    win_king = stats_df.sort_values("win_rate", ascending=False).iloc[0]
    loser = stats_df.sort_values("avg_rating", ascending=True).iloc[0]

    # ---------- 평균 스탯 TOP ----------
    top_goal = stats_df.sort_values("avg_goal", ascending=False).iloc[0]
    top_assist = stats_df.sort_values("avg_assist", ascending=False).iloc[0]
    top_block = stats_df.sort_values("avg_block", ascending=False).iloc[0]

    # =====================================================
    # 🥇 1줄 KPI : MVP / 패배 범인
    # =====================================================
    k1, k2, k3 = st.columns(3)

    k1.metric(
        "⭐ 평점 MVP",
        f"{mvp['avg_rating']}",
        mvp["nickname"]
    )

    k2.metric(
        "승률 KING",
        f"{win_king['win_rate']}",
        win_king["nickname"]
    )

    k3.metric(
        "패배 요인 (평점 최저)",
        f"{loser['avg_rating']}",
        loser["nickname"]
    )

    # =====================================================
    # 2줄 KPI : 평균 득점 / 도움 / 차단
    # =====================================================
    k4, k5, k6 = st.columns(3)

    k4.metric(
        "평균 득점",
        f"{top_goal['avg_goal']}",
        top_goal["nickname"]
    )

    k5.metric(
        "평균 도움",
        f"{top_assist['avg_assist']}",
        top_assist["nickname"]
    )

    k6.metric(
        "평균 차단",
        f"{top_block['avg_block']}",
        top_block["nickname"]
    )

    st.markdown("---")
    

    # =====================================================
    # 3. 개인별 누적 스탯 테이블
    # =====================================================
    st.subheader("개인별 누적 성적")

    stats_view = (
        stats_df[
            [
                "nickname", "games", "win", "draw", "lose",
                "win_rate", "goal", "assist", "block", "avg_rating"
            ]
        ]
        .rename(columns={
            "nickname": "닉네임",
            "games": "경기 수",
            "win": "승",
            "draw": "무",
            "lose": "패",
            "win_rate": "승률(%)",
            "goal": "득점",
            "assist": "도움",
            "block": "차단",
            "avg_rating": "평균 평점",
        })
        .sort_values("승률(%)", ascending=False)
    )

    st.dataframe(
        stats_view,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # =====================================================
    # 📋 4. 개인별 상세 경기 테이블
    # =====================================================
    st.subheader("개인별 상세 경기 기록")

    all_names = sorted(df["nickname"].unique().tolist())
    selected_name = st.selectbox(
        "유저 선택",
        all_names
    )

    detail_df = df[df["nickname"] == selected_name].copy()
    detail_df = detail_df.sort_values("date", ascending=False)

    # KPI (선택 유저 기준)
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("경기 수", len(detail_df))
    c2.metric("총 득점", int(detail_df["goal"].sum()))
    c3.metric("총 도움", int(detail_df["assist"].sum()))
    c4.metric(
        "평균 평점",
        round(detail_df["rating"].mean(), 2)
        if detail_df["rating"].notna().any()
        else "-"
    )

    st.markdown("#### 경기 상세")

    detail_view = detail_df[
        [
            "date", "matchResult", "goal",
            "assist", "block", "rating", "matchId"
        ]
    ].rename(columns={
        "date": "경기일시",
        "matchResult": "결과",
        "goal": "득점",
        "assist": "도움",
        "block": "차단",
        "rating": "평점",
        "matchId": "매치 ID"
    })

    st.dataframe(
        detail_view,
        use_container_width=True,
        hide_index=True
    )

# ---------- 탭 4: 경기 리스트 ----------
with tab_matches:
    st.subheader("RAW DATA 1vs1 worldcup")
    view = filtered.copy()
    view = view.sort_values("date", ascending=False)
    view["date_str"] = view["date"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(view, use_container_width=True)

    #streamlit run dashboard_wager_analysis.py