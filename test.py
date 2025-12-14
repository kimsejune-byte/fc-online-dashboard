import requests
import json

API_KEY = "live_7a611a04eeb1ac043f43a92245935f274608d65acac4fcb584f1baad81aa8bd7efe8d04e6d233bd35cf2fabdeb93fb0d"
HEADERS = {"x-nxopen-api-key": API_KEY}

# 🔥 테스트할 accessid  (너 멤버 중 아무나 넣으면 됨)
TEST_ACCESSID = "6fcf2b3f3ac52bf388e3cc9a1bba1f68"   # 200000000


def test_endpoint(name, url, params=None):
    print(f"\n===== 테스트: {name} =====")
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=5)
        print("STATUS:", res.status_code)
        print("TEXT:", res.text)
    except Exception as e:
        print("ERROR:", e)


# 1) 가장 유력했던 기본 정보 API
test_endpoint(
    name="유저 기본정보(user/basic)",
    url="https://open.api.nexon.com/fconline/v1/user/basic",
    params={"accessid": TEST_ACCESSID}
)

# 2) 혹시나 하는 ouid도 테스트
test_endpoint(
    name="유저 기본정보(user/basic, ouid)",
    url="https://open.api.nexon.com/fconline/v1/user/basic",
    params={"ouid": TEST_ACCESSID}
)

# 3) 유저 최고 등급 정보 (여기에도 포함돼 있을 가능성)
test_endpoint(
    name="유저 최고 등급(maxdivision)",
    url="https://open.api.nexon.com/fconline/v1/user/maxdivision",
    params={"accessid": TEST_ACCESSID}
)

# 4) 유저 매치 정보 (구단가치가 있을 수도 있어)
test_endpoint(
    name="유저 매치 리스트(matches)",
    url="https://open.api.nexon.com/fconline/v1/user/match",
    params={"accessid": TEST_ACCESSID, "matchtype": 40}
)

# 5) FC 온라인 전체 선수 메타 정보 (여기에는 없을 가능성 크지만 혹시)
test_endpoint(
    name="선수 시즌 정보(seasonid)",
    url="https://open.api.nexon.com/fconline/v1/seasonid"
)

# 6) 전체 선수 리스트 (여기에 팀 가치 같은 필드 있을 수도 있어서)
test_endpoint(
    name="선수 스탯 정보(players)",
    url="https://open.api.nexon.com/fconline/v1/players"
)