# -*- coding: utf-8 -*-
"""
OUID -> 최신 닉네임 맵 자동 생성/갱신 스크립트
실행:  python refresh_nickname_map.py
생성:  nickname_map.json (프로젝트 같은 폴더)
"""

import json
from pathlib import Path
import requests

API_KEY = "live_7a611a04eeb1ac043f43a92245935f274608d65acac4fcb584f1baad81aa8bd7efe8d04e6d233bd35cf2fabdeb93fb0d"
HEADERS = {"x-nxopen-api-key": API_KEY}

BASE_DIR = Path(__file__).resolve().parent
OUT_PATH = BASE_DIR / "nickname_map.json"

# 우리 멤버 OUID (고정값)
OUR_OUIDS = [
    "40260d503f67f41c85ad1fbb6bf97fae",
    "2fe7767c06e059a2593e2ec5747ca28b",
    "970686025f32d1af9205cb93cce0ed0e",
    "abdee2cf7166a82cc746fe903ba131d9",
    "8ae71939629a719da141318475d8f1da",
    "6fcf2b3f3ac52bf388e3cc9a1bba1f68",
]

def get_nickname(ouid: str) -> str:
    # 프로필/닉네임 조회 엔드포인트 (Nexon API)
    url = f"https://open.api.nexon.com/fconline/v1/user/basic?ouid={ouid}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    # 보통 { "ouid": "...", "nickname": "..." } 형태
    return data.get("nickname") or ""

def main():
    mapping = {}
    for ouid in OUR_OUIDS:
        try:
            nickname = get_nickname(ouid)
        except Exception as e:
            print(f"[WARN] {ouid} 닉네임 조회 실패: {e}")
            nickname = mapping.get(ouid, "")  # 실패 시 이전 값 유지(없으면 빈칸)
        mapping[ouid] = nickname

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print("\n✅ nickname_map.json 갱신 완료:")
    for k, v in mapping.items():
        print(f" - {k} : {v}")

if __name__ == "__main__":
    main()
