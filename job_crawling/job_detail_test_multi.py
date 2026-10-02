import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import json
import os
from urllib.parse import urlparse, parse_qs, urljoin

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ==========================================================
# 설정
# ==========================================================

# 처음 실행은 3개 테스트
# 336개 전체를 돌릴 때는 None으로 변경
TEST_LIMIT = None

CSV_FILE = "saramin_jobs_clean.csv"

load_dotenv()

DB_USER = os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DATABASE", "jobinsight_db")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)


# ==========================================================
# 1. CSV 불러오기
# ==========================================================

df = pd.read_csv(CSV_FILE)

print("=" * 60)
print("JobInsight V2 상세 채용정보 크롤링")
print("=" * 60)
print(f"전체 공고 수: {len(df)}")


# ==========================================================
# 2. 테스트 공고 선정
# ==========================================================

# 전체 공고
target = df.copy()

# 이미 상세 크롤링된 job_id 확인
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT job_id FROM job_details")
    )

    crawled_job_ids = {
        row[0]
        for row in result
    }

# CSV의 URL 기준으로 job_id 연결
with engine.connect() as conn:
    result = conn.execute(
        text("""
            SELECT job_id, url
            FROM jobs
        """)
    )

    job_map = {
        row.url: row.job_id
        for row in result
    }

target["job_id"] = target["URL"].map(job_map)

# 이미 크롤링된 공고 제외
target = target[
    ~target["job_id"].isin(crawled_job_ids)
].copy()

print(f"이미 상세 크롤링된 공고: {len(crawled_job_ids)}개")
print(f"추가 상세 크롤링 대상: {len(target)}개")

if TEST_LIMIT is None:
    test_jobs = target
else:
    test_jobs = target.head(TEST_LIMIT)

    if TEST_LIMIT is None:
        test_jobs = target
    else:
        test_jobs = target.head(TEST_LIMIT)

print(f"상세 크롤링 대상: {len(test_jobs)}개")


# ==========================================================
# 3. 섹션명 정규화
# ==========================================================

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

    for emoji in [
        "📋",
        "🏠",
        "🎁",
        "🚀",
        "🛎️",
        "🛎"
    ]:
        title = title.replace(emoji, "")

    title = title.strip("[] ")

    return title.strip()


# ==========================================================
# 4. 상세 섹션 구조화
# ==========================================================

def extract_detail_sections(detail_text):

    lines = [
        line.strip()
        for line in detail_text.splitlines()
        if line.strip()
    ]

    section_indices = []

    for i, line in enumerate(lines):

        clean_line = normalize_section_title(line)

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

            detail_sections[section_name] += (
                "\n" + content_text
            )

        else:

            detail_sections[section_name] = content_text

    return detail_sections


# ==========================================================
# 5. DB의 job_id 찾기
# ==========================================================

def get_job_id(job_url):

    with engine.connect() as conn:

        result = conn.execute(
            text("""
                SELECT job_id
                FROM jobs
                WHERE url = :url
                LIMIT 1
            """),
            {"url": job_url}
        )

        row = result.fetchone()

        if row:
            return row[0]

    return None


# ==========================================================
# 6. 상세정보 DB 저장
# ==========================================================

def save_detail(job_id, detail_sections):

    detail_json = json.dumps(
        detail_sections,
        ensure_ascii=False
    )

    with engine.begin() as conn:

        # 같은 공고의 기존 상세정보가 있으면 삭제
        conn.execute(
            text("""
                DELETE FROM job_details
                WHERE job_id = :job_id
            """),
            {"job_id": job_id}
        )

        # 새 상세정보 저장
        conn.execute(
            text("""
                INSERT INTO job_details
                (
                    job_id,
                    detail_sections
                )
                VALUES
                (
                    :job_id,
                    :detail_sections
                )
            """),
            {
                "job_id": job_id,
                "detail_sections": detail_json
            }
        )


# ==========================================================
# 7. 공고별 상세페이지 크롤링
# ==========================================================

success_count = 0
fail_count = 0

for test_no, (_, row) in enumerate(
    test_jobs.iterrows(),
    start=1
):

    job_url = row["URL"]
    company = row["회사명"]
    title = row["공고명"]

    print("\n" + "=" * 60)
    print(f"[{test_no}/{len(test_jobs)}]")
    print("=" * 60)
    print("회사:", company)
    print("공고:", title)

    try:

        # --------------------------------------------------
        # 세션
        # --------------------------------------------------

        session = requests.Session()

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/154.0.0.0 Safari/537.36"
            )
        }


        # --------------------------------------------------
        # 상세페이지
        # --------------------------------------------------

        res = session.get(
            job_url,
            headers=headers,
            timeout=10
        )

        print("상세페이지:", res.status_code)

        if res.status_code != 200:
            raise Exception("상세페이지 접속 실패")


        # --------------------------------------------------
        # rec_idx
        # --------------------------------------------------

        query = parse_qs(
            urlparse(job_url).query
        )

        rec_idx = query.get(
            "rec_idx",
            [None]
        )[0]

        if not rec_idx:
            raise Exception("rec_idx 없음")


        # --------------------------------------------------
        # AJAX
        # --------------------------------------------------

        ajax_url = (
            "https://www.saramin.co.kr"
            "/zf_user/jobs/relay/view-ajax"
        )

        ajax_headers = {
            "User-Agent": headers["User-Agent"],
            "Accept": "text/html, */*; q=0.01",
            "Content-Type": (
                "application/x-www-form-urlencoded; charset=UTF-8"
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

        print("AJAX:", ajax_res.status_code)

        if ajax_res.status_code != 200:
            raise Exception("AJAX 요청 실패")


        # --------------------------------------------------
        # iframe
        # --------------------------------------------------

        ajax_soup = BeautifulSoup(
            ajax_res.text,
            "html.parser"
        )

        iframe = ajax_soup.select_one(
            "#iframe_content_0"
        )

        if not iframe:
            raise Exception(
                "상세 본문 iframe 없음"
            )

        detail_path = iframe.get("src")

        detail_url = urljoin(
            "https://www.saramin.co.kr",
            detail_path
        )


        # --------------------------------------------------
        # 실제 상세본문
        # --------------------------------------------------

        detail_res = session.get(
            detail_url,
            headers={
                "User-Agent": headers["User-Agent"],
                "Referer": job_url
            },
            timeout=10
        )

        print(
            "상세본문:",
            detail_res.status_code
        )

        if detail_res.status_code != 200:
            raise Exception(
                "상세본문 요청 실패"
            )


        # --------------------------------------------------
        # 상세본문 추출
        # --------------------------------------------------

        detail_soup = BeautifulSoup(
            detail_res.text,
            "html.parser"
        )

        content = detail_soup.select_one(
            ".user_content"
        )

        if not content:
            raise Exception(
                "user_content 없음"
            )

        detail_text = content.get_text(
            "\n",
            strip=True
        )


        # --------------------------------------------------
        # 섹션 구조화
        # --------------------------------------------------

        detail_sections = extract_detail_sections(
            detail_text
        )

        print(
            "추출된 섹션:",
            ", ".join(detail_sections.keys())
            if detail_sections
            else "없음"
        )


        # --------------------------------------------------
        # jobs 테이블의 job_id 확인
        # --------------------------------------------------

        job_id = get_job_id(job_url)

        if job_id is None:

            print(
                "DB에서 job_id를 찾지 못했습니다."
            )

            fail_count += 1
            continue


        # --------------------------------------------------
        # DB 저장
        # --------------------------------------------------

        save_detail(
            job_id,
            detail_sections
        )

        print(
            f"DB 저장 완료 - job_id: {job_id}"
        )

        success_count += 1


    except Exception as e:

        print("오류:", e)

        fail_count += 1


    # --------------------------------------------------
    # 다음 공고 전 3~5초 랜덤 대기
    # --------------------------------------------------

    if test_no < len(test_jobs):

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


# ==========================================================
# 8. 최종 결과
# ==========================================================

print("\n" + "=" * 60)
print("상세 크롤링 및 DB 저장 완료")
print("=" * 60)
print("대상:", len(test_jobs))
print("성공:", success_count)
print("실패:", fail_count)
print("=" * 60)