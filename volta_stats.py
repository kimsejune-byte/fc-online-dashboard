# volta_stats.py
import json
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VOLTA_JSON_PATH = BASE_DIR / "volta_matches.json"

MIN_GAMES = 5  # 최소 경기수 필터 (원하면 1로 낮춰도 됨)


def calc_volta_stats():
    with open(VOLTA_JSON_PATH, "r", encoding="utf-8") as f:
        matches = json.load(f)

    stats = defaultdict(lambda: {
        "ouid": "",
        "nickname": "",
        "games": 0,
        "win": 0,
        "draw": 0,
        "lose": 0,
        "goal": 0,
        "assist": 0,
        "block": 0,
        "rating_sum": 0.0,
    })

    # ======================
    # 집계
    # ======================
    for m in matches:
        ouid = m["ouid"]
        s = stats[ouid]

        s["ouid"] = ouid
        s["nickname"] = m["nickname"]
        s["games"] += 1

        # 승/무/패
        if m["matchResult"] == "승":
            s["win"] += 1
        elif m["matchResult"] == "무":
            s["draw"] += 1
        elif m["matchResult"] == "패":
            s["lose"] += 1

        # KPI 누적
        s["goal"] += m.get("goal", 0) or 0
        s["assist"] += m.get("assist", 0) or 0
        s["block"] += m.get("block", 0) or 0
        s["rating_sum"] += m.get("rating", 0.0) or 0.0

    # ======================
    # 평균 KPI 계산
    # ======================
    result = []
    for s in stats.values():
        games = s["games"]
        if games < MIN_GAMES:
            continue

        result.append({
            "ouid": s["ouid"],
            "nickname": s["nickname"],
            "games": games,
            "win": s["win"],
            "draw": s["draw"],
            "lose": s["lose"],
            "win_rate": round(s["win"] / games * 100, 1),

            # 총합
            "goal": s["goal"],
            "assist": s["assist"],
            "block": s["block"],

            # ✅ 평균 KPI (핵심)
            "avg_goal": round(s["goal"] / games, 2),
            "avg_assist": round(s["assist"] / games, 2),
            "avg_block": round(s["block"] / games, 2),
            "avg_rating": round(s["rating_sum"] / games, 2),
        })

    return result


def select_kings(stats):
    return {
        "goal_king": max(stats, key=lambda x: x["avg_goal"]),
        "assist_king": max(stats, key=lambda x: x["avg_assist"]),
        "block_king": max(stats, key=lambda x: x["avg_block"]),
        "mvp": max(stats, key=lambda x: x["avg_rating"]),
    }


# ======================
# 터미널 실행용
# ======================
if __name__ == "__main__":
    stats = calc_volta_stats()
    kings = select_kings(stats)

    print("\n📊 개인별 볼타 평균 스탯")
    for s in sorted(stats, key=lambda x: x["win_rate"], reverse=True):
        print(s)

    print("\n👑 타이틀")
    print("🥅 득점왕:", kings["goal_king"]["nickname"], f"(경기당 {kings['goal_king']['avg_goal']})")
    print("🎯 도움왕:", kings["assist_king"]["nickname"], f"(경기당 {kings['assist_king']['avg_assist']})")
    print("🛡 차단왕:", kings["block_king"]["nickname"], f"(경기당 {kings['block_king']['avg_block']})")
    print("⭐ MVP:", kings["mvp"]["nickname"], f"(평균 평점 {kings['mvp']['avg_rating']})")