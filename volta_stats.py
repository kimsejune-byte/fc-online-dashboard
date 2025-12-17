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
        "lose": 0,
        "goal_sum": 0,
        "assist_sum": 0,
        "block_sum": 0,
        "rating_sum": 0.0,
        "rating_cnt": 0
    })

    for m in matches:
        ouid = m["ouid"]
        s = stats[ouid]

        s["nickname"] = m["nickname"]
        s["games"] += 1

        # 승/무/패
        if m["matchResult"] == "승":
            s["win"] += 1
        elif m["matchResult"] == "무":
            s["draw"] += 1
        elif m["matchResult"] == "패":
            s["lose"] += 1

        # 누적 스탯
        s["goal_sum"] += m.get("goal", 0)
        s["assist_sum"] += m.get("assist", 0)
        s["block_sum"] += m.get("block", 0)

        rating = m.get("rating")
        if rating is not None:
            s["rating_sum"] += rating
            s["rating_cnt"] += 1

    result = []
    for ouid, s in stats.items():
        games = s["games"]

        result.append({
            "ouid": ouid,
            "nickname": s["nickname"],
            "games": games,
            "win": s["win"],
            "draw": s["draw"],
            "lose": s["lose"],
            "win_rate": round(s["win"] / games * 100, 1),

            # ✅ 평균 스탯
            "avg_goal": round(s["goal_sum"] / games, 2),
            "avg_assist": round(s["assist_sum"] / games, 2),
            "avg_block": round(s["block_sum"] / games, 2),
            "avg_rating": round(
                s["rating_sum"] / s["rating_cnt"], 2
            ) if s["rating_cnt"] > 0 else 0.0
        })

    return result


# =========================
# 터미널 테스트
# =========================
if __name__ == "__main__":
    stats = calc_volta_stats()

    print("\n📊 개인별 평균 스탯")
    for s in stats:
        print(s)

    print("\n🥅 평균 득점왕:", max(stats, key=lambda x: x["avg_goal"]))
    print("🎯 평균 도움왕:", max(stats, key=lambda x: x["avg_assist"]))
    print("🛡 평균 차단왕:", max(stats, key=lambda x: x["avg_block"]))
    print("⭐ 평균 평점 MVP:", max(stats, key=lambda x: x["avg_rating"]))