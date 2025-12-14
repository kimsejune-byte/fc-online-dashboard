from datetime import timezone, timedelta, datetime
from extract_internal_matches import extract_internal_matches, save_worldcup_ids

print("\n===== ⏱️ 시간 기반 내전 경기 추출 & 저장 =====")
KST = timezone(timedelta(hours=9))

# 👇 여기 시간만 네가 그날그날 바꿔서 쓰면 됨
START = datetime(2025, 11, 14, 0, 0, 0, tzinfo=KST)
END   = datetime(2025, 11, 16, 5, 0, 0, tzinfo=KST)

matches = extract_internal_matches(START, END)
for m in matches:
    print(f" - {m['matchId']} @ {m['date']}")

save_worldcup_ids(matches)
print("\n✅ worldcup_detailed.json 업데이트 완료")
