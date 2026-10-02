import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
import pandas as pd
import re
import time
import random
import os


# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

INPUT_FILE = "saramin_jobs_clean.csv"
OUTPUT_FILE = "saramin_jobs_detail.csv"

BASE_URL = "https://www.saramin.co.kr"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}


# --------------------------------------------------
# 2. 기술스택 패턴
# --------------------------------------------------

TECH_PATTERN = re.compile(
    r"선택\s*:\s*IT개발·데이터\s*>\s*"
    r"기술스택\s*>\s*(.+)$"
)


# --------------------------------------------------
# 3. 공고 1개 크롤링
# --------------------------------------------------

def crawl_job(job_url):

    session = requests.Session()

    result = {
        "상세페이지상태": None,
        "AJAX상태": None,
        "상세본문상태": None,
        "상세본문추출": False,
        "기술스택": None,
        "기술스택개수": 0
    }

    try:

        # --------------------------------------------------
        # 3-1. 공고 페이지
        # --------------------------------------------------

        res = session.get(
            job_url,
            headers=HEADERS,
            timeout=10
        )

        result["상세페이지상태"] = res.status_code

        if res.status_code != 200:
            return result


        # --------------------------------------------------
        # 3-2. rec_idx 추출
        # --------------------------------------------------

        query = parse_qs(
            urlparse(job_url).query
        )

        rec_idx = query.get(
            "rec_idx",
            [None]
        )[0]

        if not rec_idx:
            return result


        # --------------------------------------------------
        # 3-3. AJAX 요청
        # --------------------------------------------------

        ajax_url = (
            f"{BASE_URL}/zf_user/jobs/relay/view-ajax"
        )

        ajax_headers = {
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/html, */*; q=0.01",
            "Content-Type": (
                "application/x-www-form-urlencoded; "
                "charset=UTF-8"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "Origin": BASE_URL,
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

        result["AJAX상태"] = ajax_res.status_code

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
            BASE_URL,
            detail_path
        )


        # --------------------------------------------------
        # 3-5. 실제 상세본문
        # --------------------------------------------------

        detail_res = session.get(
            detail_url,
            headers={
                "User-Agent": HEADERS["User-Agent"],
                "Referer": job_url
            },
            timeout=10
        )

        result["상세본문상태"] = detail_res.status_code

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

        result["상세본문추출"] = True

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
        # 3-7. 기술스택 추출
        # --------------------------------------------------

        tech_stack = []

        for line in lines:

            match = TECH_PATTERN.search(line)

            if match:

                tech = match.group(1).strip()

                if tech and tech not in tech_stack:
                    tech_stack.append(tech)


        if tech_stack:

            result["기술스택"] = ", ".join(
                tech_stack
            )

            result["기술스택개수"] = len(
                tech_stack
            )

        else:

            result["기술스택"] = None
            result["기술스택개수"] = 0


    except Exception as e:

        print("오류:", e)

    return result


# --------------------------------------------------
# 4. 기존 데이터 불러오기
# --------------------------------------------------

df = pd.read_csv(
    INPUT_FILE
)

print("=" * 60)
print("Saramin 상세페이지 전체 크롤링")
print("=" * 60)

print(
    f"목록 데이터: {len(df)}건"
)


# --------------------------------------------------
# 5. 기존 진행 결과 확인
# --------------------------------------------------

if os.path.exists(OUTPUT_FILE):

    result_df = pd.read_csv(
        OUTPUT_FILE
    )

    print(
        f"기존 상세 크롤링 결과: "
        f"{len(result_df)}건"
    )

else:

    result_df = df.copy()

    result_df["상세페이지상태"] = None
    result_df["AJAX상태"] = None
    result_df["상세본문상태"] = None
    result_df["상세본문추출"] = False
    result_df["기술스택"] = None
    result_df["기술스택개수"] = 0

    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("새로운 결과 파일 생성")


# --------------------------------------------------
# 6. 처리할 URL 확인
# --------------------------------------------------

completed_urls = set(
    result_df.loc[
        result_df["상세본문추출"] == True,
        "URL"
    ].dropna()
)

print(
    f"이미 완료된 공고: "
    f"{len(completed_urls)}건"
)


# --------------------------------------------------
# 7. 전체 상세 크롤링
# --------------------------------------------------

for i, row in df.iterrows():

    job_url = row["URL"]

    # 이미 처리된 공고는 건너뜀
    if job_url in completed_urls:

        continue


    print("\n" + "=" * 60)
    print(
        f"진행: {i + 1}/{len(df)}"
    )

    print(
        f"회사: {row['회사명']}"
    )

    print(
        f"공고: {row['공고명']}"
    )


    result = crawl_job(
        job_url
    )


    # --------------------------------------------------
    # 결과 저장
    # --------------------------------------------------

    result_df.loc[
        result_df["URL"] == job_url,
        "상세페이지상태"
    ] = result["상세페이지상태"]

    result_df.loc[
        result_df["URL"] == job_url,
        "AJAX상태"
    ] = result["AJAX상태"]

    result_df.loc[
        result_df["URL"] == job_url,
        "상세본문상태"
    ] = result["상세본문상태"]

    result_df.loc[
        result_df["URL"] == job_url,
        "상세본문추출"
    ] = result["상세본문추출"]

    result_df.loc[
        result_df["URL"] == job_url,
        "기술스택"
    ] = result["기술스택"]

    result_df.loc[
        result_df["URL"] == job_url,
        "기술스택개수"
    ] = result["기술스택개수"]


    # 바로 저장
    result_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    print(
        "페이지:",
        result["상세페이지상태"]
    )

    print(
        "AJAX:",
        result["AJAX상태"]
    )

    print(
        "상세본문:",
        result["상세본문상태"]
    )

    print(
        "기술스택:",
        result["기술스택개수"],
        "개"
    )


    # --------------------------------------------------
    # 다음 공고까지 대기
    # --------------------------------------------------

    if i < len(df) - 1:

        sleep_time = random.randint(
            3,
            5
        )

        print(
            f"다음 공고까지 "
            f"{sleep_time}초 대기..."
        )

        time.sleep(
            sleep_time
        )


# --------------------------------------------------
# 8. 최종 결과
# --------------------------------------------------

print("\n" + "=" * 60)
print("전체 상세 크롤링 완료")
print("=" * 60)

print(
    f"전체 공고: {len(result_df)}건"
)

print(
    "상세본문 추출 성공:",
    result_df["상세본문추출"].sum(),
    "건"
)

print(
    "기술스택 존재:",
    (result_df["기술스택개수"] > 0).sum(),
    "건"
)

print(
    "기술스택 없음:",
    (result_df["기술스택개수"] == 0).sum(),
    "건"
)

print(
    f"저장 파일: {OUTPUT_FILE}"
)

print("=" * 60)