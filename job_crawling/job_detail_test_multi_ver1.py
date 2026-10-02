import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from urllib.parse import urlparse, parse_qs, urljoin


# --------------------------------------------------
# 1. CSV 불러오기
# --------------------------------------------------

df = pd.read_csv("saramin_jobs_clean.csv")


# --------------------------------------------------
# 2. 테스트할 공고 선정
# --------------------------------------------------

target = df[
    df["공고명"].str.contains(
        "개발|백엔드|프론트엔드|풀스택|데이터|데이터엔지니어|데이터분석|AI|인공지능|머신러닝|딥러닝|소프트웨어|웹|SW|서버|클라우드|DevOps|MLOps|시스템|솔루션|플랫폼|애플리케이션",
        case=False,
        na=False
    )
]

# 처음에는 3개만 테스트
test_jobs = target.head(3)


print("=" * 60)
print("기술스택 상세페이지 크롤링 테스트")
print("=" * 60)
print(f"테스트 공고 수: {len(test_jobs)}")


# --------------------------------------------------
# 3. 공고별 상세페이지 크롤링
# --------------------------------------------------

for test_no, (idx, row) in enumerate(test_jobs.iterrows(), start=1):

    job_url = row["URL"]
    company = row["회사명"]
    title = row["공고명"]

    print("\n" + "=" * 60)
    print(f"테스트 {test_no}")
    print("=" * 60)
    print("회사:", company)
    print("공고:", title)
    print("URL:", job_url)

    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/154.0.0.0 Safari/537.36"
        )
    }

    # --------------------------------------------------
    # 3-1. 공고 페이지 접속
    # --------------------------------------------------

    res = session.get(
        job_url,
        headers=headers,
        timeout=10
    )

    print("상세페이지 응답:", res.status_code)

    if res.status_code != 200:
        print("상세페이지 접속 실패")
        continue


    # --------------------------------------------------
    # 3-2. rec_idx 추출
    # --------------------------------------------------

    query = parse_qs(urlparse(job_url).query)
    rec_idx = query.get("rec_idx", [None])[0]

    if not rec_idx:
        print("rec_idx를 찾지 못했습니다.")
        continue


    # --------------------------------------------------
    # 3-3. AJAX 요청
    # --------------------------------------------------

    ajax_url = "https://www.saramin.co.kr/zf_user/jobs/relay/view-ajax"

    ajax_headers = {
        "User-Agent": headers["User-Agent"],
        "Accept": "text/html, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.saramin.co.kr",
        "Referer": job_url
    }

    data = {
        "rec_idx": rec_idx,
        "rec_seq": "0",
        "view_type": "public-recruit",
        "utm_source": "",
        "utm_medium": "",
        "utm_term": "",
        "utm_campaign": "",
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

    print("AJAX 응답:", ajax_res.status_code)

    if ajax_res.status_code != 200:
        print("AJAX 요청 실패")
        continue


    # --------------------------------------------------
    # 3-4. 상세 본문 iframe 찾기
    # --------------------------------------------------

    ajax_soup = BeautifulSoup(
        ajax_res.text,
        "html.parser"
    )

    iframe = ajax_soup.select_one("#iframe_content_0")

    if not iframe:
        print("상세 본문 iframe을 찾지 못했습니다.")
        continue

    detail_path = iframe.get("src")

    detail_url = urljoin(
        "https://www.saramin.co.kr",
        detail_path
    )

    print("상세 본문 URL 확인")


    # --------------------------------------------------
    # 3-5. 실제 상세 본문 요청
    # --------------------------------------------------

    detail_res = session.get(
        detail_url,
        headers={
            "User-Agent": headers["User-Agent"],
            "Referer": job_url
        },
        timeout=10
    )

    print("상세 본문 응답:", detail_res.status_code)

    if detail_res.status_code != 200:
        print("상세 본문 요청 실패")
        continue


    # --------------------------------------------------
    # 3-6. 상세 본문 추출
    # --------------------------------------------------

    detail_soup = BeautifulSoup(
        detail_res.text,
        "html.parser"
    )

    content = detail_soup.select_one(".user_content")

    if not content:
        print("user_content를 찾지 못했습니다.")
        continue

    detail_text = content.get_text(
        "\n",
        strip=True
    )


    # --------------------------------------------------
    # 4. 상세 본문 섹션 구조화
    # --------------------------------------------------

    lines = [
        line.strip()
        for line in detail_text.splitlines()
        if line.strip()
    ]


    section_aliases = {

        "주요업무": "주요업무",
        "담당업무": "주요업무",

        "자격요건": "자격요건",
        "지원자격": "자격요건",
        "지원 자격": "자격요건",

        "우대사항": "우대사항",
        "우대 사항": "우대사항",

        "고용형태": "고용형태",
        "근무형태": "고용형태",

        "근무지": "근무지",
        "근무지역": "근무지",

        "근무조건": "근무조건",

        "채용절차": "채용절차",

        "접수기간": "접수기간",
        "제출서류": "제출서류",
        "접수방법": "접수방법",

        "안내사항": "안내사항",
        "유의사항": "안내사항"
    }


    def normalize_section_title(line):

        title = line.strip()

        # 이모지 제거
        for emoji in ["📋", "🏠", "🎁", "🚀", "🛎️", "🛎"]:
            title = title.replace(emoji, "")

        # 대괄호 제거
        title = title.strip("[] ")

        return title.strip()


    # 섹션 제목 위치 찾기
    section_indices = []

    for i, line in enumerate(lines):

        clean_line = normalize_section_title(line)

        # 자격요건과 우대사항이 한 줄로 있는 경우
        if clean_line == "자격요건 및 우대사항":
            section_indices.append(
                (i, "자격요건")
            )
            continue

        if clean_line in section_aliases:
            section_indices.append(
                (i, section_aliases[clean_line])
            )


    # 중복 제거
    unique_sections = []

    for item in section_indices:
        if item not in unique_sections:
            unique_sections.append(item)

    section_indices = unique_sections


    # 섹션별 내용 추출
    detail_sections = {}

    for n, (start_idx, section_name) in enumerate(section_indices):

        if n + 1 < len(section_indices):
            end_idx = section_indices[n + 1][0]
        else:
            end_idx = len(lines)

        section_content = lines[
            start_idx + 1:end_idx
        ]

        if not section_content:
            continue

        content_text = "\n".join(section_content)

        if section_name in detail_sections:
            detail_sections[section_name] += "\n" + content_text
        else:
            detail_sections[section_name] = content_text


    # --------------------------------------------------
    # 5. 결과 출력
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("상세 섹션 구조화 결과")
    print("=" * 60)

    if detail_sections:

        for section_name, section_content in detail_sections.items():

            print("\n" + "-" * 60)
            print(f"[{section_name}]")
            print("-" * 60)

            print(section_content[:500])

    else:

        print("구조화할 수 있는 섹션을 찾지 못했습니다.")

# --------------------------------------------------
# 5-1. 기술스택 추출
# --------------------------------------------------

# 실제 기술로 볼 수 있는 키워드 목록
tech_keywords = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "Go",
    "Golang",
    "Kotlin",
    "Swift",
    "PHP",
    "Ruby",

    "Spring",
    "Spring Boot",
    "Django",
    "Flask",
    "FastAPI",
    "React",
    "Vue",
    "Angular",
    "Next.js",
    "Node.js",

    "MySQL",
    "MariaDB",
    "PostgreSQL",
    "Oracle",
    "MongoDB",
    "Redis",
    "Elasticsearch",

    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Jenkins",

    "Kafka",
    "RabbitMQ",

    "TensorFlow",
    "PyTorch",
    "Keras",
    "OpenCV",
    "YOLO",

    "Git",
    "GitHub",
    "Linux",
    "SQL"
]


# 기술 추출 대상 섹션
tech_sections = [
    "주요업무",
    "자격요건",
    "우대사항"
]


tech_text = ""

for section_name in tech_sections:

    if section_name in detail_sections:
        tech_text += "\n" + detail_sections[section_name]


    # 실제 본문에 등장한 기술만 추출
    tech_stack = []


    # --------------------------------------------------
    # 6. 다음 공고 전 3~5초 대기
    # --------------------------------------------------

    if test_no < len(test_jobs):

        sleep_time = random.randint(3, 5)

        print(
            f"\n다음 공고 테스트 전 "
            f"{sleep_time}초 대기..."
        )

        time.sleep(sleep_time)


print("\n" + "=" * 60)
print(f"{len(test_jobs)}개 공고 테스트 완료")
print("=" * 60)