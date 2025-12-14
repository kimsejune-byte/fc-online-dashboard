# volta_run.py
from pathlib import Path
import json
import requests
from datetime import datetime, timezone, timedelta

# ==============================
# 기본 설정
# ==============================
BASE_DIR = Path(__file__).resolve().parent
VOLTA_JSON_PATH = BASE_DIR / "volta_matches.json"

API_KEY = "live_7a611a04eeb1ac043f43a92245935f274608d65acac4fcb584f1baad81aa8bd7efe8d04e6d233bd35cf2fabdeb93fb0d"
HEADERS = {"x-nxopen-api-key": API_KEY}

KST = timezone(timedelta(hours=9))

# 우리 고정 6명 (ouid → nickname)
OUR_OUID_MAP = {
    "40260d503f67f41c85ad1fbb6bf97fae": "들을엉",
    "2fe7767c06e059a2593e2ec5747ca28b": "희미한연기",
    "970686025f32d1af9205cb93cce0ed0e": "호랑이소굴로들가",
    "abdee2cf7166a82cc746fe903ba131d9": "서울의환호",
    "8ae71939629a719da141318475d8f1da": "서울시마포구",
    "6fcf2b3f3ac52bf388e3cc9a1bba1f68": "200000000",
}

MATCH_TYPE_VOLTA_OFFICIAL = 214
MATCH_LIMIT = 50  # 유저당 최근 N경기

# ==============================
# API 함수
# ==============================
def fetch_user_matches(ouid: str):
    url = "https://open.api.nexon.com/fconline/v1/user/match"
    params = {
        "ouid": ouid,
        "matchtype": MATCH_TYPE_VOLTA_OFFICIAL,
        "limit": MATCH_LIMIT,
    }
    res = requests.get(url, headers=HEADERS, params=params, timeout=5)
    if res.status_code == 200:
        return res.json()
    return []

def fetch_match_detail(match_id: str):
    url = "https://open.api.nexon.com/fconline/v1/match-detail"
    params = {"matchid": match_id}
    res = requests.get(url, headers=HEADERS, params=params, timeout=5)
    if res.status_code == 200:
        return res.json()
    return None

# ==============================
# 메인 수집 로직
# ==============================
def collect_volta_matches():
    # 기존 데이터 로드
    if VOLTA_JSON_PATH.exists():
        with open(VOLTA_JSON_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
    else:
        saved = []

    saved_keys = {
        (m["matchId"], m["ouid"]) for m in saved
    }

    new_rows = []

    for ouid, nickname in OUR_OUID_MAP.items():
        print(f"🔍 {nickname} 볼타 공식경기 조회 중...")
        match_ids = fetch_user_matches(ouid)

        for match_id in match_ids:
            key = (match_id, ouid)
            if key in saved_keys:
                continue

            detail = fetch_match_detail(match_id)
            if not detail:
                continue

            # 해당 유저의 matchInfo 찾기
            player_info = None
            for p in detail.get("matchInfo", []):
                if p.get("ouid") == ouid:
                    player_info = p
                    break

            if not player_info:
                continue

            match_result = player_info.get("matchDetail", {}).get("matchResult")
            match_date = detail.get("matchDate")

            new_rows.append({
                "matchId": match_id,
                "date": match_date,
                "matchType": MATCH_TYPE_VOLTA_OFFICIAL,
                "ouid": ouid,
                "nickname": nickname,
                "matchResult": match_result,
            })

    if new_rows:
        saved.extend(new_rows)
        with open(VOLTA_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(saved, f, ensure_ascii=False, indent=2)

    return len(new_rows)

# ==============================
# 터미널 실행
# ==============================
if __name__ == "__main__":
    count = collect_volta_matches()
    print(f"\n✅ 새로 저장된 볼타 공식경기: {count}건")