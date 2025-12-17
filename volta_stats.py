# volta_stats.py
import json
from collections import defaultdict
from pathlib import Path

# ==============================
# 경로 설정
# ==============================
BASE_DIR = Path(__file__).resolve().parent
VOLTA_JSON_PATH = BASE_DIR / "volta_matches.json"


# ==============================
# 메인 스탯 계산 함수
# ==============================
def calc_volta_stats():
    if not VOLTA_JSON_PATH.exists():
        raise FileNotFoundError("volta_matches.json 파일이 없습니다.")

    with open(VOLTA_JSON_PATH, "r", encoding="utf-8") as f:
        matches = json.load(f)

    stats = defaultdict(lambda: {
        "nickname": "",
        "games": 0,
        "win": 0,
        "draw": 0,
        "lose": 0,
        "goal": 0,
        "assist": 0,
        "block": 0,
        "rating_sum": 0.0
    })

    # ------------------------------
    # match 단위 집계
    # ------------------------------
    for m in matches:
        ouid = m["ouid"]
        s = stats[ouid]

        s["nickname"] = m["nickname"]
        s["games"] += 1

        # 승무패
        if m["matchResult"] == "승":
            s["win"] += 1
        elif m["matchResult"] == "무":
            s["draw"] += 1
        elif m["matchResult"] == "패":
            s["lose"] += 1

        # 누적 스탯
        s["goal"] += m.get("goal", 0)
        s["assist"] += m.get("assist", 0)
        s["block"] += m.get("block", 0)
        s["rating_sum"] += m.get("rating", 0.0)

    # ------------------------------
    # 결과 정리
    # ------------------------------
    result = []

    for ouid, s in stats.items():
        games = s["games"]
        avg_rating = round(s["rating_sum"] / games, 2) if games > 0 else 0.0
        win_rate = round(s["win"] / games * 100, 1) if games > 0 else 0.0

        result.append({
            "ouid": ouid,
            "nickname": s["nickname"],
            "games": games,
            "win": s["win"],
            "draw": s["draw"],
            "lose": s["lose"],
            "win_rate": win_rate,
            "goal": s["goal"],
            "assist": s["assist"],
            "block": s["block"],
            "avg_rating": avg_rating
        })

    return result


# ==============================
# 랭킹 계산 함수들
# ==============================
def get_top_goal(stats):
    return max(stats, key=lambda x: x["goal"])


def get_top_assist(stats):
    return max(stats, key=lambda x: x["assist"])


def get_top_block(stats):
    return max(stats, key=lambda x: x["block"])


def get_mvp(stats, min_games=5):
    filtered = [s for s in stats if s["games"] >= min_games]
    return max(filtered, key=lambda x: x["avg_rating"]) if filtered else None


# ==============================
# 터미널 테스트
# ==============================
if __name__ == "__main__":
    stats = calc_volta_stats()

    print("📊 볼타 개인별 스탯")
    for s in stats:
        print(s)

    print("\n🥅 득점왕:", get_top_goal(stats))
    print("🎯 도움왕:", get_top_assist(stats))
    print("🛡 차단왕:", get_top_block(stats))
    print("⭐ MVP:", get_mvp(stats))