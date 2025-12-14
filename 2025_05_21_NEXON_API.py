import requests

API_KEY = "여기에_넥슨_API_KEY_붙여넣기"
headers = {"x-nxopen-api-key": API_KEY}

# 사용자 OCID 조회
nickname = "test_7a611a04eeb1ac043f43a92245935f278fc16c133a245a6223141cedd10f417fefe8d04e6d233bd35cf2fabdeb93fb0d"
url = f"https://open.api.nexon.com/fconline/v1.0/users?nickname={nickname}"
res = requests.get(url, headers=headers)
ocid = res.json().get("ocid")
print("OCID:", ocid)
