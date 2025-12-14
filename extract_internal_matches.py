import requests
import time
from datetime import timezone, timedelta, datetime
import json
import os
from pathlib import Path

from refresh_nickname_map import OUR_OUIDS  # ✅ 멤버 OUID는 여기에서만 관리

API_KEY = "live_7a611a04eeb1ac043f43a92245935f274608d65acac4fcb584f1baad81aa8bd7efe8d04e6d233bd35cf2fabdeb93fb0d"
HEADERS = {"x-nxopen-api-key": API_KEY}

BASE_MATCH_URL = "https://open.api.nexon.com/fconline/v1/user/match"
DETAIL_URL = "https://open.api.nexon.com/fconline/v1/match-detail"

BASE_DIR = Path(__file__).resolve().parent
WORLDCUP_DETAIL_JSON_PATH = BASE_DIR / "worldcup_detailed.json"
NICKNAME_MAP_PATH = BASE_DIR / "nickname_map.json"


def load_nickname_map():
    """
    nickname_map.json 로드 (없으면 빈 dict)
    """
    if not NICKNAME_MAP_PATH.exists():
        return {}
    with open(NICKNAME_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_our_ouids():
    """
    고정 OUR_OUIDS 리스트를 set으로 반환
    (닉네임과 무관하게 항상 동일)
    """
    ouids = set(OUR_OUIDS)
    print("\n[INFO] OUR_OUIDS 준비 완료:")
    print(ouids)
    return ouids


def get_recent_match_ids_by_ouid(ouid: str, limit: int = 100):
    """
    ouid 기준으로 최근 친선전(matchtype=40) matchId 리스트 조회
    """
    res = requests.get(
        BASE_MATCH_URL,
        headers=HEADERS,
        params={"ouid": ouid, "matchtype": 40, "offset": 0, "limit": limit},
        timeout=10,
    )
    if res.status_code != 200:
        print(f"❌ OUID {ouid}의 매치ID 조회 실패: {res.status_code} {res.text}")
        return []
    return res.json()


def get_participants_ouid_and_date(match_id):
    """
    매치 상세 조회해서 참가자 OUID 목록과 KST 기준 날짜 반환
    """
    res = requests.get(f"{DETAIL_URL}?matchid={match_id}", headers=HEADERS, timeout=10)
    if res.status_code != 200:
        print(f"❌ matchId {match_id} 상세 조회 실패: {res.status_code}")
        return [], None

    data = res.json()
    ouids = [info.get("ouid") for info in data.get("matchInfo", [])]

    match_date_str = data.get("matchDate")
    if match_date_str:
        match_date_utc = datetime.strptime(
            match_date_str, "%Y-%m-%dT%H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        match_date = match_date_utc.astimezone(timezone(timedelta(hours=9)))  # KST
    else:
        match_date = None

    return ouids, match_date


def extract_internal_matches(start_dt, end_dt):
    """
    지정된 시간 범위에서
    - 참가자 2명이고
    - 둘 다 OUR_OUIDS에 포함된 경우만
    → 내기 경기로 판단하여 반환
    """
    our_ouids = get_our_ouids()
    nickname_map = load_nickname_map()
    all_match_ids = set()

    # ✅ OUID 기준으로만 최근 경기 수집
    for ouid in OUR_OUIDS:
        ids = get_recent_match_ids_by_ouid(ouid, limit=99)
        all_match_ids.update(ids)
        time.sleep(0.2)

    print(f"🔎 전체 수집된 matchId 수: {len(all_match_ids)}")
    internal_matches = []

    for match_id in all_match_ids:
        participants_ouid, match_date = get_participants_ouid_and_date(match_id)

        pretty_names = [nickname_map.get(o, o) for o in participants_ouid]

        print(f"[DEBUG] matchId: {match_id}")
        print(f"         날짜: {match_date}")
        print(f"         참가자 OUIDs: {participants_ouid}")
        print(f"         참가자 닉네임: {pretty_names}")

        if len(participants_ouid) == 2:
            print("         참가자 수 == 2 ✅")
            for ouid in participants_ouid:
                if ouid in our_ouids:
                    print(f"         ✔ {ouid} ∈ OUR_OUIDS")
                else:
                    print(f"         ❌ {ouid} ∉ OUR_OUIDS")
        else:
            print(f"         ❌ 참가자 수가 2명이 아님 → {len(participants_ouid)}명")

        if not match_date:
            continue
        if not (start_dt <= match_date <= end_dt):
            continue

        # ✅ 둘 다 우리 OUID인 경우에만 내기 경기로 인정
        if len(participants_ouid) == 2 and all(p in our_ouids for p in participants_ouid):
            internal_matches.append(
                {
                    "matchId": match_id,
                    "date": match_date.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        else:
            print(f"⛔ matchId {match_id} 제외됨 → OUIDs: {participants_ouid}")

        time.sleep(0.2)

    return internal_matches


def save_worldcup_ids(matches):
    """
    worldcup_detailed.json에 matchId + date 누적 저장 (중복 제거 & 정렬)
    """
    existing = []
    existing_ids = set()
    if WORLDCUP_DETAIL_JSON_PATH.exists():
        with open(WORLDCUP_DETAIL_JSON_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
            existing_ids = {m["matchId"] for m in existing}

    combined = existing + [m for m in matches if m["matchId"] not in existing_ids]
    combined = sorted(combined, key=lambda x: x["date"])

    with open(WORLDCUP_DETAIL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"✅ worldcup_detailed.json 누적 저장 완료 (총 {len(combined)}건)")
