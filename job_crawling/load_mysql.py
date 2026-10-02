import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

# 1. 환경변수
host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
user = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")
database = os.getenv("MYSQL_DATABASE")

# 2. MySQL 연결
engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
)

# 3. CSV 불러오기
df = pd.read_csv("saramin_jobs_clean.csv")

print(f"CSV 데이터: {len(df)}건")

# 4. 테이블 생성
create_table_sql = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    region VARCHAR(255) NOT NULL,
    career_type VARCHAR(50) NOT NULL,
    employment_type VARCHAR(50) NOT NULL,
    education VARCHAR(100) NOT NULL,
    education_type VARCHAR(100) NOT NULL,
    deadline VARCHAR(50) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

with engine.begin() as conn:
    conn.execute(text(create_table_sql))

print("jobs 테이블 생성 완료")

# 5. 컬럼명 변경
df = df.rename(columns={
    "회사명": "company_name",
    "공고명": "title",
    "지역": "region",
    "학력": "education",
    "마감일": "deadline",
    "URL": "url"
})

# 필요한 컬럼만 선택
df = df[
    [
        "company_name",
        "title",
        "region",
        "경력구분",
        "고용형태",
        "education",
        "학력구분",
        "deadline",
        "url"
    ]
]

# DB 컬럼명으로 변경
df = df.rename(columns={
    "경력구분": "career_type",
    "고용형태": "employment_type",
    "학력구분": "education_type"
})

# 6. 데이터 적재
df.to_sql(
    "jobs",
    con=engine,
    if_exists="append",
    index=False
)

print(f"MySQL 적재 완료: {len(df)}건")