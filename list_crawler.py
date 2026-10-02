import requests
from bs4 import BeautifulSoup
import time
import random
import pandas as pd

# 사람인 검색 결과 URL
url = "https://www.saramin.co.kr/zf_user/jobs/public/list?cat_mcls=2&exp_cd=1&exp_none=y&job_type=1&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C9%2C10&panel_type=domestic&search_optional_item=y&search_done=y&panel_count=y&preview=y"

headers = {
    "User-Agent": "Mozilla/5.0"
}

# 전체 데이터를 저장할 리스트
jobs = []

# 1페이지부터 반복
for page in range(1, 18):

    print("\n" + "=" * 60)
    print(f"{page}페이지 수집 시작")
    print("=" * 60)

    # 페이지 번호 추가
    params = {
        "page": page
    }

    # 웹페이지 요청
    res = requests.get(
        url,
        headers=headers,
        params=params
    )

    print(f"웹페이지 응답: {res.status_code}")

    # HTML 분석
    soup = BeautifulSoup(res.text, "html.parser")

    # 채용공고 목록
    items = soup.select(".list_item")

    print(f"수집된 공고 수: {len(items)}")

    # 공고가 없으면 종료
    if len(items) == 0:
        print("공고가 없어 수집을 종료합니다.")
        break

    # 공고 하나씩 추출
    for item in items:

        company = item.select_one(".company_nm .str_tit")
        title = item.select_one(".job_tit a.str_tit")
        region = item.select_one(".work_place")
        career = item.select_one(".career")
        education = item.select_one(".education")
        date = item.select_one(".support_detail .date")

        # 상세 URL
        if title:
            job_url = title.get("href")

            # 상대경로 → 전체 URL
            if job_url and job_url.startswith("/"):
                job_url = "https://www.saramin.co.kr" + job_url
        else:
            job_url = None

        # 데이터 저장
        jobs.append({
            "회사명": company.get_text(strip=True) if company else None,
            "공고명": title.get_text(strip=True) if title else None,
            "지역": region.get_text(" ", strip=True) if region else None,
            "경력/고용형태": career.get_text(" ", strip=True) if career else None,
            "학력": education.get_text(" ", strip=True) if education else None,
            "마감일": date.get_text(strip=True) if date else None,
            "URL": job_url
        })

    print(f"현재까지 누적 수집: {len(jobs)}건")

    # 요청 간격
    if page < 17:
        sleep_time = random.randint(3, 5)
        print(f"{sleep_time}초 대기...")
        time.sleep(sleep_time)


# DataFrame 변환
df = pd.DataFrame(jobs)

# 중복 제거
df = df.drop_duplicates(subset=["URL"])

# CSV 저장
df.to_csv(
    "saramin_jobs.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 60)
print("전체 크롤링 완료!")
print("=" * 60)
print(f"최종 수집 건수: {len(df)}건")
print("중복 제거 완료")
print("파일명: saramin_jobs.csv")
print("=" * 60)