# JobInsight

## 신입 IT·데이터 채용공고 데이터 수집·분석 웹 서비스

사람인에서 신입 IT·데이터 채용공고를 수집하고,
상세 공고의 주요업무·자격요건·우대사항을 구조화하여 MySQL에 저장한 뒤
FastAPI와 React를 통해 채용공고 검색 및 분석 기능을 제공하는 웹 서비스입니다.

---

## 1. Project Overview

### 프로젝트 목적

채용 플랫폼의 공고 데이터를 직접 수집하고 분석하여
신입 IT·데이터 직무의 채용시장 정보를 확인할 수 있는 서비스를 구현했습니다.

단순히 채용공고 목록을 수집하는 것에서 끝내지 않고,

- 채용공고 목록 데이터 수집
- 상세페이지 데이터 수집
- 데이터 정제 및 분류
- MySQL 데이터베이스 저장
- FastAPI API 구축
- React 기반 검색·분석 UI 구현

까지 데이터 수집부터 서비스 제공까지의 전체 흐름을 구현했습니다.

---

## 2. 주요 기능

### ① 채용공고 데이터 수집

사람인에서 다음 조건의 채용공고를 수집했습니다.

- 분야: IT개발·데이터
- 경력: 신입
- 고용형태: 정규직
- 지역: 전체

총 **336건**의 채용공고를 수집했습니다.

수집 데이터:

- 회사명
- 공고명
- 지역
- 경력
- 고용형태
- 학력
- 마감일
- 공고 URL

### ② 데이터 정제

수집된 원본 데이터를 분석에 사용할 수 있도록 분류했습니다.

#### 경력

```text
신입
신입/경력
경력무관
```

#### 고용형태

```text
정규직
정규직 외
```

#### 학력

```text
고졸 이상
전문대 이상
4년제 대학 이상
석사 이상
학력무관
```

URL을 기준으로 중복 공고를 제거했습니다.

### ③ 상세페이지 크롤링

사람인의 상세페이지가 단순한 HTML GET 요청만으로 전체 내용이 제공되지 않는 구조임을 확인하고,
개발자도구의 Network 요청을 분석하여 실제 상세 데이터가 전달되는 요청 구조를 확인했습니다.

```text
채용공고 상세 URL
      ↓
/zf_user/jobs/relay/view-ajax
      ↓
AJAX 응답 분석
      ↓
iframe_content_0 확인
      ↓
/zf_user/jobs/relay/view-detail
      ↓
상세 HTML 요청
      ↓
HTML Parsing
```

이를 통해 상세 공고의 주요 내용을 수집했습니다.

### ④ 상세 공고 구조화

상세페이지에서 현재 구조화하여 사용하는 주요 영역은 다음과 같습니다.

```text
주요업무
자격요건
우대사항
```

수집된 상세 데이터는 JSON 형태로 저장하여 공고별로 관리했습니다.

```text
jobs
  └── 채용공고 기본 정보

job_details
  └── 상세 공고 정보(JSON)
```

### ⑤ 조건 검색

사용자가 원하는 조건을 선택하여 채용공고를 검색할 수 있습니다.

- 경력
- 고용형태
- 학력

검색 결과는 페이지 단위로 조회합니다.

### ⑥ 키워드 검색

상세 공고의

- 주요업무
- 자격요건
- 우대사항

영역을 대상으로 키워드 검색을 구현했습니다.

예:

```text
Python
Java
React
SQL
```

검색 결과에서는

- 해당 키워드가 포함된 공고 수
- 주요업무 포함 공고 수
- 자격요건 포함 공고 수
- 우대사항 포함 공고 수
- 해당 공고 목록

을 확인할 수 있습니다.

검색은 **공고 단위**로 집계하며,
하나의 공고에서 동일한 키워드가 여러 번 등장하더라도 해당 공고는 1건으로 계산합니다.

### ⑦ 공고 미리보기

채용공고 목록에서 공고를 선택하면 수집된 상세 내용을 미리 확인할 수 있습니다.

```text
회사명
공고명
지역
경력
고용형태
학력
마감일

주요업무
자격요건
우대사항
```

원문 확인이 필요한 경우 사람인 원문 공고로 이동할 수 있습니다.

---

## 3. 데이터 분석 결과

총 수집 공고:

```text
336건
```

### 경력

| 경력구분 | 공고 수 |
|---|---:|
| 신입/경력 | 170 |
| 신입 | 141 |
| 경력무관 | 25 |

### 고용형태

| 고용형태 | 공고 수 |
|---|---:|
| 정규직 | 267 |
| 정규직 외 | 69 |

### 학력

| 학력구분 | 공고 수 |
|---|---:|
| 4년제 대학 이상 | 143 |
| 학력무관 | 86 |
| 전문대 이상 | 49 |
| 고졸 이상 | 34 |
| 석사 이상 | 24 |

### 주요 조건 결과

- 신입 + 정규직: **133건**
- 신입 + 정규직 + 4년제 대학 이상: **103건**

---

## 4. Backend API

FastAPI를 사용하여 MySQL의 채용공고 데이터를 API 형태로 제공합니다.

### 주요 API

```text
GET /
```

API 실행 확인

```text
GET /db-test
```

MySQL 연결 및 데이터 건수 확인

```text
GET /jobs
```

채용공고 목록 조회

조건:

```text
career_type
employment_type
education_type
```

```text
GET /jobs/{job_id}
```

특정 채용공고 상세 정보 조회

```text
GET /jobs/stats
```

채용공고 통계 조회

```text
GET /jobs/search?keyword=Python
```

상세 공고의 주요업무·자격요건·우대사항을 대상으로 키워드 검색

---

## 5. Database

MySQL을 사용하여 채용공고와 상세 데이터를 분리하여 저장했습니다.

### jobs

채용공고의 기본 정보를 저장합니다.

```text
job_id
company_name
title
region
career_type
employment_type
education
education_type
deadline
url
crawled_at
```

### job_details

상세페이지에서 수집한 내용을 저장합니다.

```text
detail_id
job_id
detail_sections
crawled_at
```

`job_details.job_id`와 `jobs.job_id`를 외래키로 연결했습니다.

---

## 6. Frontend

React와 Vite를 사용하여 웹 UI를 구현했습니다.

### 페이지 구성

```text
/dashboard
    ↓
채용시장 분석
키워드 검색

/jobs
    ↓
채용공고 조건 검색
채용공고 목록
페이지네이션
공고 미리보기
```

### 주요 UI

- 채용시장 통계
- 키워드 검색
- 조건별 채용공고 검색
- 검색 결과 페이지네이션
- 공고 미리보기
- 사람인 원문 링크

---

## 7. Tech Stack

### Crawling

- Python
- Requests
- BeautifulSoup
- Pandas

### Backend

- FastAPI
- SQLAlchemy
- Uvicorn

### Database

- MySQL
- JSON

### Frontend

- React
- Vite
- JavaScript
- CSS

### Development

- Git
- GitHub
- VS Code

---

## 8. 시행착오

### 상세페이지 요청 구조 분석

처음에는 상세 URL에 HTTP GET 요청을 보내 HTML을 파싱하는 방식으로 접근했습니다.

하지만 실제 상세 내용이 일반 HTML 응답에 모두 포함되어 있지 않아 원하는 데이터를 확인하기 어려웠습니다.

개발자도구의 Network 탭을 통해 페이지에서 발생하는 요청을 확인한 결과,

```text
/view-ajax
```

요청을 통해 상세페이지 콘텐츠가 구성되고,
응답 내부에서 실제 상세 콘텐츠를 제공하는 iframe을 확인할 수 있었습니다.

이에 따라 요청 흐름을 분석하여 실제 상세 HTML을 가져오는 방식으로 변경했습니다.

### 비정형 상세페이지

모든 채용공고가 동일한 HTML 구조를 사용하는 것은 아니었습니다.

현재는 다음과 같이 주요 영역이 명확하게 구분되는 상세페이지를 중심으로 구조화했습니다.

```text
주요업무
자격요건
우대사항
```

일부 공고는 표(table) 형태 등 다른 HTML 구조로 구성되어 있어
현재 파싱 로직으로 모든 내용을 동일하게 구조화하기 어려운 경우가 존재합니다.

---

## 9. 데이터 수집 검증

목록 데이터:

```text
수집 공고: 336건
중복 URL: 0건
결측값: 0건
```

상세 데이터:

```text
상세 크롤링 성공: 336 / 336
job_details 저장: 336건
```

구조화된 상세 영역:

```text
주요업무: 207건
자격요건: 265건
우대사항: 99건
```

※ 상세 영역은 하나의 공고가 여러 영역을 동시에 포함할 수 있으므로 합계는 전체 공고 수와 일치하지 않습니다.

---

## 10. 프로젝트 구조

```text
jobinsight/
│
├── crawler/
│   ├── cr.py
│   ├── clean_jobs.py
│   ├── create_db.py
│   ├── load_mysql.py
│   └── detail_crawler.py
│
├── backend/
│   ├── main.py
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── sql/
│   ├── schema.sql
│   └── analysis.sql
│
├── data/
│   └── README.md
│
├── .gitignore
└── README.md
```

---

## 11. 실행 방법

### Backend

```bash
cd backend

conda activate cr

python -m uvicorn main:app --reload
```

FastAPI:

```text
http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend

npm install

npm run dev
```

React:

```text
http://localhost:5173
```

---

## 12. 향후 개선사항

### 1. 비정형 상세페이지 파싱 고도화

현재 구조화하지 못하는 표(table) 기반 상세페이지의 HTML을 추가적으로 파싱하여
상세 데이터 수집 범위를 확대할 수 있습니다.

### 2. 기술스택 자동 추출

상세 공고에서 Python, Java, React, SQL 등의 기술 키워드를 자동으로 추출하고
기술스택별 채용 빈도 및 분포를 분석하는 기능으로 확장할 수 있습니다.

### 3. 수집 자동화

현재 수동으로 수행하는 데이터 수집 과정을 스케줄링하여
주기적으로 최신 채용공고를 수집하는 ETL 파이프라인으로 확장할 수 있습니다.
