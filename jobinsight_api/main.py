from fastapi import FastAPI
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os
import json
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# MySQL 연결
host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
user = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")
database = os.getenv("MYSQL_DATABASE")

engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
)


@app.get("/")
def home():
    return {"message": "JobInsight API 실행 성공"}


@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM jobs"))
        count = result.scalar()

    return {
        "message": "MySQL 연결 성공",
        "job_count": count
    }
@app.get("/jobs")
def get_jobs(
    page: int = 1,
    limit: int = 20,
    career_type: str | None = None,
    employment_type: str | None = None,
    education_type: str | None = None
):
    offset = (page - 1) * limit

    conditions = []

    params = {
        "limit": limit,
        "offset": offset
    }

    # 경력 필터
    if career_type:
        conditions.append("career_type = :career_type")
        params["career_type"] = career_type

    # 고용형태 필터
    if employment_type:
        conditions.append("employment_type = :employment_type")
        params["employment_type"] = employment_type

    # 학력 필터
    if education_type:
        conditions.append("education_type = :education_type")
        params["education_type"] = education_type

    # WHERE 조건 생성
    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with engine.connect() as conn:

        # 전체 공고 수
        total = conn.execute(
            text(f"""
                SELECT COUNT(*)
                FROM jobs
                {where_clause}
            """),
            params
        ).scalar()

        # 현재 페이지 공고 조회
        result = conn.execute(
            text(f"""
                SELECT
                    job_id,
                    company_name,
                    title,
                    region,
                    career_type,
                    employment_type,
                    education,
                    education_type,
                    deadline,
                    url
                FROM jobs
                {where_clause}
                ORDER BY job_id
                LIMIT :limit OFFSET :offset
            """),
            params
        )

        jobs = [dict(row._mapping) for row in result]

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "count": len(jobs),
        "jobs": jobs
    }

@app.get("/jobs/stats")
def get_job_stats():

    with engine.connect() as conn:

        total = conn.execute(
            text("SELECT COUNT(*) FROM jobs")
        ).scalar()

        career_result = conn.execute(
            text("""
                SELECT career_type, COUNT(*) AS count
                FROM jobs
                GROUP BY career_type
                ORDER BY count DESC
            """)
        )

        career_stats = [
            dict(row._mapping)
            for row in career_result
        ]

        employment_result = conn.execute(
            text("""
                SELECT employment_type, COUNT(*) AS count
                FROM jobs
                GROUP BY employment_type
                ORDER BY count DESC
            """)
        )

        employment_stats = [
            dict(row._mapping)
            for row in employment_result
        ]

        education_result = conn.execute(
            text("""
                SELECT education_type, COUNT(*) AS count
                FROM jobs
                GROUP BY education_type
                ORDER BY count DESC
            """)
        )

        education_stats = [
            dict(row._mapping)
            for row in education_result
        ]

    return {
        "total": total,
        "career": career_stats,
        "employment": employment_stats,
        "education": education_stats
    }

@app.get("/jobs/search")
def search_jobs(
    keyword: str,
    page: int = 1,
    limit: int = 20
):
    keyword = keyword.strip()

    if not keyword:
        return {
            "keyword": "",
            "page": page,
            "limit": limit,
            "total": 0,
            "section_counts": {
                "주요업무": 0,
                "자격요건": 0,
                "우대사항": 0
            },
            "jobs": []
        }

    offset = (page - 1) * limit
    search_keyword = f"%{keyword}%"

    with engine.connect() as conn:

        # 전체 검색 공고 수
        total_query = text("""
            SELECT COUNT(*)
            FROM jobs j
            JOIN job_details d
                ON j.job_id = d.job_id
            WHERE
                LOWER(COALESCE(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(
                            d.detail_sections,
                            '$."주요업무"'
                        )
                    ), ''
                )) LIKE LOWER(:keyword)

                OR

                LOWER(COALESCE(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(
                            d.detail_sections,
                            '$."자격요건"'
                        )
                    ), ''
                )) LIKE LOWER(:keyword)

                OR

                LOWER(COALESCE(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(
                            d.detail_sections,
                            '$."우대사항"'
                        )
                    ), ''
                )) LIKE LOWER(:keyword)
        """)

        total = conn.execute(
            total_query,
            {"keyword": search_keyword}
        ).scalar()

        # 섹션별 검색 공고 수
        section_query = text("""
            SELECT
                SUM(
                    CASE
                        WHEN LOWER(COALESCE(
                            JSON_UNQUOTE(
                                JSON_EXTRACT(
                                    d.detail_sections,
                                    '$."주요업무"'
                                )
                            ), ''
                        )) LIKE LOWER(:keyword)
                        THEN 1
                        ELSE 0
                    END
                ) AS main_count,

                SUM(
                    CASE
                        WHEN LOWER(COALESCE(
                            JSON_UNQUOTE(
                                JSON_EXTRACT(
                                    d.detail_sections,
                                    '$."자격요건"'
                                )
                            ), ''
                        )) LIKE LOWER(:keyword)
                        THEN 1
                        ELSE 0
                    END
                ) AS requirement_count,

                SUM(
                    CASE
                        WHEN LOWER(COALESCE(
                            JSON_UNQUOTE(
                                JSON_EXTRACT(
                                    d.detail_sections,
                                    '$."우대사항"'
                                )
                            ), ''
                        )) LIKE LOWER(:keyword)
                        THEN 1
                        ELSE 0
                    END
                ) AS preference_count

            FROM jobs j
            JOIN job_details d
                ON j.job_id = d.job_id
        """)

        section_result = conn.execute(
            section_query,
            {"keyword": search_keyword}
        ).fetchone()

        # 검색 결과 공고
        jobs_query = text("""
            SELECT
                j.job_id,
                j.company_name,
                j.title,
                j.region,
                j.career_type,
                j.employment_type,
                j.education_type,
                j.deadline,
                j.url
            FROM jobs j
            JOIN job_details d
                ON j.job_id = d.job_id

            WHERE
                LOWER(COALESCE(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(
                            d.detail_sections,
                            '$."주요업무"'
                        )
                    ), ''
                )) LIKE LOWER(:keyword)

                OR

                LOWER(COALESCE(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(
                            d.detail_sections,
                            '$."자격요건"'
                        )
                    ), ''
                )) LIKE LOWER(:keyword)

                OR

                LOWER(COALESCE(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(
                            d.detail_sections,
                            '$."우대사항"'
                        )
                    ), ''
                )) LIKE LOWER(:keyword)

            ORDER BY j.job_id
            LIMIT :limit OFFSET :offset
        """)

        result = conn.execute(
            jobs_query,
            {
                "keyword": search_keyword,
                "limit": limit,
                "offset": offset
            }
        )

        jobs = [dict(row._mapping) for row in result]

    return {
        "keyword": keyword,
        "page": page,
        "limit": limit,
        "total": total,
        "section_counts": {
            "주요업무": section_result.main_count or 0,
            "자격요건": section_result.requirement_count or 0,
            "우대사항": section_result.preference_count or 0
        },
        "count": len(jobs),
        "jobs": jobs
    }
@app.get("/jobs/{job_id}")
def get_job_detail(job_id: int):

    with engine.connect() as conn:

        result = conn.execute(
            text("""
                SELECT
                    j.job_id,
                    j.company_name,
                    j.title,
                    j.region,
                    j.career_type,
                    j.employment_type,
                    j.education,
                    j.education_type,
                    j.deadline,
                    j.url,
                    d.detail_sections,
                    d.crawled_at
                FROM jobs j
                LEFT JOIN job_details d
                    ON j.job_id = d.job_id
                WHERE j.job_id = :job_id
            """),
            {"job_id": job_id}
        )

        row = result.fetchone()

    if not row:
        return {
            "message": "공고를 찾을 수 없습니다."
        }

    data = dict(row._mapping)
    if data["detail_sections"]:
        data["detail_sections"] = json.loads(
            data["detail_sections"]
        )

    return data
