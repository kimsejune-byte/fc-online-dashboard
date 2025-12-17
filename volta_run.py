# volta_run.py
import requests
import json
from pathlib import Path
from tqdm import tqdm

# ==============================
# 기본 설정
# ==============================
API_KEY = "live_7a611a04eeb1ac043f43a92245935f274608d65acac4fcb584f1baad81aa8bd7efe8d04e6d233bd35cf2fabdeb93fb0d"
HEADERS = {"x-nxopen-api-key": API_KEY}

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "volta_matches.json"

MATCH_TYPE_VOLTA = 214

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

print("\n[INFO] OUR_OUIDS 준비 완료:")
print(OUR_OUIDS)

# ==============================
# API
# ==============================
def fetch_match_list(ouid):
    url = "https://open.api.nexon.com/fconline/v1/user/match"
    params = {
        "ouid": ouid,
        "matchtype": MATCH_TYPE_VOLTA,
        "offset": 0,
        "limit": 100
    }
    res = requests.get(url, headers=HEADERS, params=params)
    return res.json() if res.status_code == 200 else []


def fetch_match_detail(match_id):
    url = "https://open.api.nexon.com/fconline/v1/match-detail"
    res = requests.get(url, headers=HEADERS, params={"matchid": match_id})
    return res.json() if res.status_code == 200 else None

# ==============================
# 메인 수집
# ==============================
def collect_volta_matches():
    if OUTPUT_PATH.exists():
        saved = json.load(open(OUTPUT_PATH, encoding="utf-8"))
    else:
        saved = []

    saved_keys = {(m["matchId"], m["ouid"]) for m in saved}

    print("\n🔍 볼타 공식경기 matchId 수집 중...\n")

    all_match_ids = set()
    for ouid, name in OUR_PLAYERS.items():
        print(f" - {name}")
        all_match_ids.update(fetch_match_list(ouid))

    print(f"\n🔎 전체 수집된 match 수: {len(all_match_ids)}")

    new_rows = []

    for match_id in tqdm(all_match_ids):
        detail = fetch_match_detail(match_id)
        if not detail:
            continue

        match_date = detail.get("matchDate", "").split(".")[0]

        for info in detail.get("matchInfo", []):
            ouid = info.get("ouid")
            if ouid not in OUR_OUIDS:
                continue

            key = (match_id, ouid)
            if key in saved_keys:
                continue

            # ✅ 여기 중요
            players = info.get("player", [])
            goals = assists = blocks = 0
            ratings = []

            for p in players:
                status = p.get("status", {})
                goals += status.get("goal", 0)
                assists += status.get("assist", 0)
                blocks += status.get("block", 0)

                if status.get("spRating") is not None:
                    ratings.append(status["spRating"])

            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

            new_rows.append({
                "matchId": match_id,
                "date": match_date,
                "matchType": MATCH_TYPE_VOLTA,
                "ouid": ouid,
                "nickname": OUR_PLAYERS[ouid],
                "matchResult": info.get("matchDetail", {}).get("matchResult"),
                "goal": goals,
                "assist": assists,
                "block": blocks,
                "rating": avg_rating,
            })

    if new_rows:
        saved.extend(new_rows)
        json.dump(saved, open(OUTPUT_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    print(f"\n✅ 새로 저장된 볼타 공식경기: {len(new_rows)}개")

# ==============================
# 실행
# ==============================
if __name__ == "__main__":
    collect_volta_matches()