# volta_stats.py
import json
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VOLTA_JSON_PATH = BASE_DIR / "volta_matches.json"

def calc_volta_stats():
    with open(VOLTA_JSON_PATH, "r", encoding="utf-8") as f:
        matches = json.load(f)

    stats = defaultdict(lambda: {
        "nickname": "",
        "games": 0,
        "win": 0,
        "draw": 0,
        "lose": 0
    })

    for m in matches:
        ouid = m["ouid"]
        result = m["matchResult"]

        s = stats[ouid]
        s["nickname"] = m["nickname"]
        s["games"] += 1

        if result == "승":
            s["win"] += 1
        elif result == "무":
            s["draw"] += 1
        elif result == "패":
            s["lose"] += 1

    result_list = []
    for ouid, s in stats.items():
        win_rate = round(s["win"] / s["games"] * 100, 1)
        result_list.append({
            "ouid": ouid,
            **s,
            "win_rate": win_rate
        })

    result_list.sort(key=lambda x: x["win_rate"], reverse=True)
    return result_list


# 터미널 테스트용
if __name__ == "__main__":
    for r in calc_volta_stats():
        print(r)