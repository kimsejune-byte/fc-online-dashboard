from pathlib import Path
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

with st.spinner("📥 내기 경기 상세정보 불러오는 중..."):
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

# ================================
#  2. 🔍 사이드바 필터
# ================================
st.sidebar.header("필터")

all_nicknames = sorted(data["nickname"].unique().tolist())
selected_nicknames = st.sidebar.multiselect(
    "유저 선택",
    options=all_nicknames,
    default=all_nicknames
)

min_date = data["date"].min()
max_date = data["date"].max()

dr = st.sidebar.date_input(
    "경기 날짜 범위",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date(),
)

start_date, end_date = dr

result_options = sorted(data["matchResult"].dropna().unique().tolist())
selected_results = st.sidebar.multiselect(
    "경기 결과 필터",
    options=result_options,
    default=result_options,
)

# 필터링
filtered = data.copy()
filtered = filtered[filtered["nickname"].isin(selected_nicknames)]
filtered = filtered[(filtered["date"].dt.date >= start_date) & (filtered["date"].dt.date <= end_date)]
filtered = filtered[filtered["matchResult"].isin(selected_results)]

st.sidebar.markdown("---")
st.sidebar.write(f" 현재 필터 내기 경기 수: **{filtered['matchId'].nunique()} 경기**")

if filtered.empty:
    st.warning("⚠️ 필터 조건에 해당하는 데이터가 없습니다.")
    st.stop()


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

# (⭐ 핵심) DF가 없으면 빈 df 생성
max_division_df = pd.DataFrame(
    max_division_rows,
    columns=["nickname", "division_code", "division_name", "achievementDate"]
)


# ================================
#  상단 KPI
# ================================
total_matches = filtered["matchId"].nunique()
total_goals = filtered["goals"].sum()

avg_goals_per_game = total_goals / total_matches
avg_shots_per_game = filtered["shots"].sum() / total_matches
avg_possession_overall = filtered["possession"].mean()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("총 내기 경기 수", f"{total_matches} 경기")
kpi2.metric("경기당 평균 득점", f"{avg_goals_per_game:.2f} 골")
kpi3.metric("경기당 평균 슈팅", f"{avg_shots_per_game:.2f} 회")
kpi4.metric("평균 점유율", f"{avg_possession_overall:.1f} %")


# ================================
#  탭 구성
# ================================
tab_overview, tab_compare, tab_matches = st.tabs(
    [" 전체 요약", " 유저 1:1 비교", " 경기 리스트"]
)

# ---------- 탭 1 ----------
# ----------------------------------------
# 🏆 1vs1 공식경기 명예의 전당
# ----------------------------------------

with tab_overview:
    import base64
import streamlit.components.v1 as components

# ======================================================
# 🏆 1vs1 공식경기 명예의 전당
# ======================================================
st.markdown("## 🏆 1vs1 공식경기 명예의 전당 Presented by Sejune inc.")

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
# (FC 온라인 실제 표기 기준)
# -------------------------------
def get_tier_icon_path(name: str):
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
    return "#1f77b4"

# -------------------------------
# 데이터 없을 경우
# -------------------------------
if max_division_df.empty:
    st.info("최고 공식경기 등급 데이터를 불러올 수 없습니다.")
else:
    # division_code 낮을수록 상위 티어
    hall_df = (
        max_division_df
        .sort_values("division_code", ascending=True)
        .reset_index(drop=True)
    )

    cards_html = ""

    for rank, row in hall_df.iterrows():
        color = get_tier_color(row["division_name"])

        icon_path = get_tier_icon_path(row["division_name"])
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
                        #{rank + 1} {row['nickname']}
                    </div>
                    <div style="color:{color};font-weight:700;">
                        {row['division_name']}
                    </div>
                    <div style="color:#9aa0a6;font-size:12px;">
                        달성일: {row['achievementDate'] or "N/A"}
                    </div>
                </div>
            </div>
        </div>
        """

    components.html(cards_html, height=1100, scrolling=True)

    st.markdown("---")
  
    # =============================
    # 요약 테이블
    # =============================
    st.subheader(" 유저별 요약 통계")
    st.dataframe(summary, use_container_width=True)



# ---------- 탭 2: 유저 비교 ----------
with tab_compare:
    st.subheader(" 유저 1:1 비교 (VS 분석)")

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


# ---------- 탭 3: 경기 리스트 ----------
with tab_matches:
    st.subheader("경기 리스트")
    view = filtered.copy()
    view = view.sort_values("date", ascending=False)
    view["date_str"] = view["date"].dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(view, use_container_width=True)

    #streamlit run dashboard_wager_analysis.py