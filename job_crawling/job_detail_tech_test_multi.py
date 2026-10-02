import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
import re
import time
import random
import pandas as pd

df = pd.read_csv("saramin_jobs_clean.csv")

# IT·데이터 관련 공고 중 앞에서 10개 선택
target = df[
    df["공고명"].str.contains(
        "개발|백엔드|프론트엔드|풀스택|데이터|AI|인공지능|머신러닝|딥러닝|소프트웨어|웹|SW|서버|클라우드|DevOps|MLOps|시스템|솔루션|플랫폼|애플리케이션",
        case=False,
        na=False
    )
]

job_urls = target["URL"].head(10).tolist()

print(f"자동 선택된 테스트 공고 수: {len(job_urls)}")

# --------------------------------------------------
# 2. 공통 헤더
# --------------------------------------------------

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}


# --------------------------------------------------
# 3. 공고 1개 처리 함수
# --------------------------------------------------

def crawl_job(job_url):

    session = requests.Session()

    result = {
        "url": job_url,
        "page_status": None,
        "ajax_status": None,
        "detail_status": None,
        "detail_found": False,
        "tech_stack": []
    }


    # --------------------------------------------------
    # 3-1. 공고 페이지
    # --------------------------------------------------

    res = session.get(
        job_url,
        headers=headers,
        timeout=10
    )

    result["page_status"] = res.status_code

    if res.status_code != 200:
        return result


    # --------------------------------------------------
    # 3-2. rec_idx
    # --------------------------------------------------

    query = parse_qs(urlparse(job_url).query)

    rec_idx = query.get(
        "rec_idx",
        [None]
    )[0]

    if not rec_idx:
        return result


    # --------------------------------------------------
    # 3-3. AJAX
    # --------------------------------------------------

    ajax_url = (
        "https://www.saramin.co.kr/"
        "zf_user/jobs/relay/view-ajax"
    )

    ajax_headers = {
        "User-Agent": headers["User-Agent"],
        "Accept": "text/html, */*; q=0.01",
        "Content-Type": (
            "application/x-www-form-urlencoded; "
            "charset=UTF-8"
        ),
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

    result["ajax_status"] = ajax_res.status_code

    if ajax_res.status_code != 200:
        return result


    # --------------------------------------------------
    # 3-4. iframe 확인
    # --------------------------------------------------

    ajax_soup = BeautifulSoup(
        ajax_res.text,
        "html.parser"
    )

    iframe = ajax_soup.select_one(
        "#iframe_content_0"
    )

    if not iframe:
        return result


    detail_path = iframe.get("src")

    if not detail_path:
        return result


    detail_url = urljoin(
        "https://www.saramin.co.kr",
        detail_path
    )


    # --------------------------------------------------
    # 3-5. 실제 상세본문
    # --------------------------------------------------

    detail_res = session.get(
        detail_url,
        headers={
            "User-Agent": headers["User-Agent"],
            "Referer": job_url
        },
        timeout=10
    )

    result["detail_status"] = detail_res.status_code

    if detail_res.status_code != 200:
        return result


    # --------------------------------------------------
    # 3-6. 상세본문 추출
    # --------------------------------------------------

    detail_soup = BeautifulSoup(
        detail_res.text,
        "html.parser"
    )

    content = detail_soup.select_one(
        ".user_content"
    )

    if not content:
        return result

    result["detail_found"] = True

    detail_text = content.get_text(
        "\n",
        strip=True
    )

    lines = [
        line.strip()
        for line in detail_text.splitlines()
        if line.strip()
    ]


    # --------------------------------------------------
    # 3-7. 실제 기술스택 추출
    # --------------------------------------------------

    pattern = re.compile(
        r"선택\s*:\s*IT개발·데이터\s*>\s*"
        r"기술스택\s*>\s*(.+)$"
    )

    tech_stack = []

    for line in lines:

        match = pattern.search(line)

        if match:

            tech = match.group(1).strip()

            if tech and tech not in tech_stack:
                tech_stack.append(tech)

    result["tech_stack"] = tech_stack

    return result


# --------------------------------------------------
# 4. 3개 공고 테스트
# --------------------------------------------------

print("=" * 60)
print("Saramin 기술스택 다건 크롤링 테스트")
print("=" * 60)

print(f"테스트 공고 수: {len(job_urls)}")


results = []


for i, job_url in enumerate(job_urls, start=1):

    print("\n" + "=" * 60)
    print(f"{i}번째 공고 테스트")
    print("=" * 60)

    print("URL:", job_url)

    try:

        result = crawl_job(job_url)

        results.append(result)

        print(
            "공고 페이지:",
            result["page_status"]
        )

        print(
            "AJAX:",
            result["ajax_status"]
        )

        print(
            "상세본문:",
            result["detail_status"]
        )

        print(
            "상세본문 추출:",
            "성공" if result["detail_found"]
            else "실패"
        )

        print(
            "기술스택 개수:",
            len(result["tech_stack"])
        )

        if result["tech_stack"]:

            print("기술스택:")

            for tech in result["tech_stack"]:
                print("-", tech)

        else:

            print(
                "명시적인 기술스택 없음"
            )

    except Exception as e:

        print("오류 발생:", e)


    # --------------------------------------------------
    # 5. 다음 공고 전 대기
    # --------------------------------------------------

    if i < len(job_urls):

        sleep_time = random.randint(3, 5)

        print(
            f"\n다음 공고까지 "
            f"{sleep_time}초 대기..."
        )

        time.sleep(sleep_time)


# --------------------------------------------------
# 6. 최종 요약
# --------------------------------------------------

print("\n" + "=" * 60)
print("최종 테스트 결과")
print("=" * 60)

for i, result in enumerate(results, start=1):

    print(
        f"{i}. "
        f"page={result['page_status']}, "
        f"ajax={result['ajax_status']}, "
        f"detail={result['detail_status']}, "
        f"tech={len(result['tech_stack'])}개"
    )

print("=" * 60)