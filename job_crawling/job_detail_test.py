import requests
from bs4 import BeautifulSoup

url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?view_type=public-recruit&rec_idx=54827315"

headers = {
    "User-Agent": "Mozilla/5.0"
}

# 세션 사용
session = requests.Session()

# 1. 먼저 상세페이지 접속
res = session.get(
    url,
    headers=headers,
    timeout=10
)

print("상세페이지 응답:", res.status_code)


# --------------------------------------------------
# 상세내용 AJAX 요청 테스트
# --------------------------------------------------

ajax_url = "https://www.saramin.co.kr/zf_user/jobs/relay/view-ajax"

ajax_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "Accept": "text/html, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.saramin.co.kr",
    "Referer": url
}

data = {
    "rec_idx": "54827315",
    "rec_seq": "0",
    "utm_source": "",
    "utm_medium": "",
    "utm_term": "",
    "utm_campaign": "",
    "view_type": "public-recruit",
    "t_ref": "",
    "t_ref_content": "",
    "t_ref_scnid": "",
    "search_uuid": "",
    "refer": "",
    "searchType": "",
    "searchword": "",
    "ref_dp": "SRI_050_VIEW_MIX_RCT_BBS_NLG",
    "dpId": "",
    "recommendRecIdx": "",
    "referNonce": "",
    "trainingStudentCode": ""
}

ajax_res = session.post(
    ajax_url,
    headers=ajax_headers,
    data=data,
    timeout=10
)





print("\n" + "=" * 60)
print("상세요강 전체 위치 확인")
print("=" * 60)

keyword = "상세요강"

positions = []
start = 0

while True:
    index = ajax_res.text.find(keyword, start)

    if index == -1:
        break

    positions.append(index)
    start = index + len(keyword)

print("발견 횟수:", len(positions))

for i, index in enumerate(positions):
    print(f"\n[{i}] 위치: {index}")
    print("-" * 60)

    print(
        ajax_res.text[
            max(0, index - 500):
            index + 1500
        ]
    )


print("AJAX 응답:", ajax_res.status_code)
print("AJAX HTML 길이:", len(ajax_res.text))

print("\n" + "=" * 60)
print("AJAX 응답 앞부분")
print("=" * 60)

print(ajax_res.text[:5000])


ajax_soup = BeautifulSoup(ajax_res.text, "html.parser")

print("\n" + "=" * 60)
print("AJAX 상세내용 구조 확인")
print("=" * 60)

print("이미지 개수:", len(ajax_soup.select("img")))

for i, img in enumerate(ajax_soup.select("img")):
    print(f"\n[{i}]")
    print("src:", img.get("src"))
    print("alt:", img.get("alt"))


keywords = [
    "기술스택",
    "주요업무",
    "자격요건",
    "우대사항",
    "담당업무",
    "지원자격"
]

print("\n" + "=" * 60)
print("AJAX 상세내용 키워드 확인")
print("=" * 60)

ajax_text = ajax_soup.get_text("\n", strip=True)

for keyword in keywords:
    print(f"\n[{keyword}]")

    if keyword in ajax_text:
        index = ajax_text.find(keyword)
        print("발견 위치:", index)
        print(ajax_text[max(0, index-300):index+1000])
    else:
        print("찾지 못함")


print("\n" + "=" * 60)
print("상세요강 HTML 구조 확인")
print("=" * 60)

detail_text = "상세요강"

if detail_text in ajax_res.text:
    index = ajax_res.text.find(detail_text)

    print("발견 위치:", index)

    print(
        ajax_res.text[
            max(0, index - 2000):
            index + 5000
        ]
    )
else:
    print("상세요강을 찾지 못했습니다.")


print("\n" + "=" * 60)
print("상세요강 전체 위치 확인")
print("=" * 60)

keyword = "상세요강"

positions = []
start = 0

while True:
    index = ajax_res.text.find(keyword, start)

    if index == -1:
        break

    positions.append(index)
    start = index + len(keyword)

print("발견 횟수:", len(positions))

for i, index in enumerate(positions):
    print(f"\n[{i}] 위치: {index}")

    print(
        ajax_res.text[
            max(0, index - 500):
            index + 1500
        ]
    )


# 상세요강 iframe 주소 확인
detail_path = "/zf_user/jobs/relay/view-detail?rec_idx=54827315&rec_seq=0&t_category=non-logged_relay_view&t_content=view_detail&t_ref=&t_ref_content="

detail_url = "https://www.saramin.co.kr" + detail_path

print("상세페이지 URL:")
print(detail_url)

# 상세요강 iframe 주소 확인
detail_path = "/zf_user/jobs/relay/view-detail?rec_idx=54827315&rec_seq=0&t_category=non-logged_relay_view&t_content=view_detail&t_ref=&t_ref_content="

detail_url = "https://www.saramin.co.kr" + detail_path

print("상세페이지 URL:")
print(detail_url)

detail_res = session.get(
    detail_url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
        "Referer": url
    },
    timeout=10
)

print("응답 상태:", detail_res.status_code)
print("HTML 길이:", len(detail_res.text))

detail_soup = BeautifulSoup(detail_res.text, "html.parser")

content = detail_soup.select_one(".user_content")

if content:

    detail_text = content.get_text("\n", strip=True)

    print("\n" + "=" * 60)
    print("상세 공고 본문")
    print("=" * 60)
    print(detail_text[:5000])

# 사용 기술 영역 추출
lines = [
    line.strip()
    for line in detail_text.splitlines()
    if line.strip()
]

# "모집부문 / 상세내용" 이후의 "사용 기술" 찾기
section_start = -1

for i, line in enumerate(lines):
    if line == "모집부문 / 상세내용":
        section_start = i
        break

tech_start = -1

if section_start != -1:
    for i in range(section_start + 1, len(lines)):
        if lines[i] == "사용 기술":
            tech_start = i
            break

# 기술스택 영역의 종료 지점
end_markers = {
    "주요업무",
    "담당업무",
    "자격요건",
    "지원자격",
    "우대사항",
    "마감일 및 근무지",
    "복지 및 혜택",
    "채용절차 및 기타 지원 유의사항"
}

if tech_start != -1:

    tech_end = len(lines)

    for i in range(tech_start + 1, len(lines)):
        if lines[i] in end_markers:
            tech_end = i
            break

    tech_list = [
        line.lstrip("•").strip()
        for line in lines[tech_start + 1:tech_end]
        if line.strip()
    ]

    print("\n" + "=" * 60)
    print("기술스택 리스트")
    print("=" * 60)
    print(tech_list)

else:
    print("사용 기술 영역을 찾지 못했습니다.") 