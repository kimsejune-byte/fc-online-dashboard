# volta_run.py
import requests
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from tqdm import tqdm

# ==============================
# 기본 설정
# ==============================
API_KEY = "live_7a611a04eeb1ac043f43a92245935f274608d65acac4fcb584f1baad81aa8bd7efe8d04e6d233bd35cf2fabdeb93fb0d"
HEADERS = {"x-nxopen-api-key": API_KEY}

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "volta_matches.json"

MATCH_TYPE_VOLTA = 214  # 볼타 공식경기

KST = timezone(timedelta(hours=9))

# ==============================
# 우리 멤버
# ==============================
OUR_PLAYERS = {
    "40260d503f67f41c85ad1fbb6bf97fae": "들을엉",
    "2fe7767c06e059a2593e2ec5747ca28b": "희미한연기",
    "970686025f32d1af9205cb93cce0ed0e": "호랑이소굴로들가",
    "abdee2cf7166a82cc746fe903ba131d9": "서울의환호",
    "8ae71939629a719da141318475d8f1da": "서울시마포구",
    "6fcf2b3f3ac52bf388e3cc9a1bba1f68": "200000000",
}
OUR_OUIDS = set(OUR_PLAYERS.keys())

print("\n[INFO] OUR_OUIDS 준비 완료")
print(OUR_OUIDS)

# ==============================
# API 함수
# ==============================
def fetch_match_list(ouid: str, limit: int = 50):
    url = "https://open.api.nexon.com/fconline/v1/user/match"
    params = {
        "ouid": ouid,
        "matchtype": MATCH_TYPE_VOLTA,
        "offset": 0,
        "limit": limit,
    }
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code != 200:
        return []
    return res.json()


def fetch_match_detail(match_id: str):
    url = "https://open.api.nexon.com/fconline/v1/match-detail"
    res = requests.get(url, headers=HEADERS, params={"matchid": match_id})
    if res.status_code != 200:
        return None
    return res.json()

# ==============================
# 메인 수집 로직
# ==============================
def collect_volta_matches():
    # 기존 데이터
    if OUTPUT_PATH.exists():
        saved = json.load(open(OUTPUT_PATH, encoding="utf-8"))
    else:
        saved = []

    saved_keys = {(r["matchId"], r["ouid"]) for r in saved}

    print("\n🔍 볼타 공식경기 matchId 수집 중...")
    all_match_ids = set()

    for ouid, name in OUR_PLAYERS.items():
        print(f" - {name}")
        ids = fetch_match_list(ouid)
        all_match_ids.update(ids)

    print(f"\n🔎 전체 match 수: {len(all_match_ids)}")

    new_rows = []

    for match_id in tqdm(all_match_ids):
        detail = fetch_match_detail(match_id)
        if not detail:
            continue

        # --- 날짜 (KST 변환) ---
        raw_date = detail.get("matchDate")
        if raw_date:
            dt = datetime.fromisoformat(raw_date.replace("Z", ""))
            dt = dt.astimezone(KST)
            match_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            match_date = None

        for info in detail.get("matchInfo", []):
            ouid = info.get("ouid")
            if ouid not in OUR_OUIDS:
                continue

            key = (match_id, ouid)
            if key in saved_keys:
                continue

            # =========================
            # ✅ Volta 핵심: player[0].status
            # =========================
            status = {}
            if info.get("player"):
                status = info["player"][0].get("status", {})

            new_rows.append({
                "matchId": match_id,
                "date": match_date,
                "matchType": MATCH_TYPE_VOLTA,
                "ouid": ouid,
                "nickname": OUR_PLAYERS.get(ouid),
                "matchResult": info.get("matchDetail", {}).get("matchResult"),

                # --- 개인 스탯 (정답 경로) ---
                "goal": status.get("goal", 0),
                "assist": status.get("assist", 0),
                "block": status.get("block", 0),
                "block_try": status.get("blockTry", 0),
                "rating": round(status.get("spRating", 0.0), 2),
            })

    if new_rows:
        saved.extend(new_rows)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(saved, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 새로 저장된 볼타 경기: {len(new_rows)}개")

# ==============================
# 실행
# ==============================
if __name__ == "__main__":
    collect_volta_matches()