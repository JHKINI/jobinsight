import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urljoin
import pandas as pd
import re
import random
import time


# --------------------------------------------------
# 1. 채용공고 데이터 불러오기
# --------------------------------------------------

df = pd.read_csv("saramin_jobs_clean.csv")

# 랜덤 10개
test_jobs = df.sample(n=10, random_state=42)
print("실제 선택된 공고 수:", len(test_jobs))
print("=" * 60)
print("랜덤 10개 기술스택 크롤링 테스트")
print("=" * 60)
print(f"테스트 공고 수: {len(test_jobs)}")


# --------------------------------------------------
# 2. 전체 공고 테스트
# --------------------------------------------------

for test_no, (_, row) in enumerate(test_jobs.iterrows(), start=1):

    job_url = row["URL"]
    company = row["회사명"]
    title = row["공고명"]

    print("\n" + "=" * 60)
    print(f"[{test_no}/10]")
    print(f"회사: {company}")
    print(f"공고: {title}")
    print("=" * 60)

    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/154.0.0.0 Safari/537.36"
        )
    }

    try:

        # --------------------------------------------------
        # 3. 공고 페이지 요청
        # --------------------------------------------------

        res = session.get(
            job_url,
            headers=headers,
            timeout=10
        )

        print("상세페이지:", res.status_code)

        if res.status_code != 200:
            print("→ 상세페이지 접속 실패")
            continue


        # --------------------------------------------------
        # 4. rec_idx 추출
        # --------------------------------------------------

        query = parse_qs(urlparse(job_url).query)
        rec_idx = query.get("rec_idx", [None])[0]

        print("rec_idx:", rec_idx)

        if not rec_idx:
            print("→ rec_idx 없음")
            continue


        # --------------------------------------------------
        # 5. AJAX 요청
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
            print("→ AJAX 요청 실패")
            continue


        # --------------------------------------------------
        # 6. iframe 확인
        # --------------------------------------------------

        ajax_soup = BeautifulSoup(
            ajax_res.text,
            "html.parser"
        )

        iframe = ajax_soup.select_one(
            "#iframe_content_0"
        )

        if not iframe:
            print("→ 상세 본문 iframe 없음")
            continue

        detail_path = iframe.get("src")

        detail_url = urljoin(
            "https://www.saramin.co.kr",
            detail_path
        )


        # --------------------------------------------------
        # 7. 실제 상세본문 요청
        # --------------------------------------------------

        detail_res = session.get(
            detail_url,
            headers={
                "User-Agent": headers["User-Agent"],
                "Referer": job_url
            },
            timeout=10
        )

        print("상세본문:", detail_res.status_code)

        if detail_res.status_code != 200:
            print("→ 상세본문 요청 실패")
            continue


        # --------------------------------------------------
        # 8. 상세본문 추출
        # --------------------------------------------------

        detail_soup = BeautifulSoup(
            detail_res.text,
            "html.parser"
        )

        content = detail_soup.select_one(
            ".user_content"
        )

        if not content:
            print("→ user_content 없음")
            continue

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
        # 9. 사람인 기술스택 태그 추출
        # --------------------------------------------------

        tech_stack = []

        pattern = re.compile(
            r"선택\s*:\s*IT개발·데이터\s*>\s*기술스택\s*>\s*(.+)$"
        )

        for line in lines:

            match = pattern.search(line)

            if match:

                tech = match.group(1).strip()

                if tech and tech not in tech_stack:
                    tech_stack.append(tech)


        # --------------------------------------------------
        # 10. 결과 출력
        # --------------------------------------------------

        print("\n[기술스택 결과]")

        if tech_stack:

            print(f"기술스택 개수: {len(tech_stack)}개")

            print(
                " / ".join(tech_stack)
            )

        else:

            print("기술스택: 없음")


    except Exception as e:

        print("→ 오류 발생:", e)


    # --------------------------------------------------
    # 11. 다음 공고 전 랜덤 대기
    # --------------------------------------------------

    if test_no < len(test_jobs):

        sleep_time = random.randint(3, 5)

        print(
            f"\n다음 공고까지 {sleep_time}초 대기..."
        )

        time.sleep(sleep_time)


print("\n" + "=" * 60)
print("랜덤 10개 테스트 완료")
print("=" * 60)