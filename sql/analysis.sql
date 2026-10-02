USE jobinsight_db;

-- 전체 공고 수
SELECT COUNT(*) AS total_jobs
FROM jobs;

-- 경력 구분
SELECT career_type, COUNT(*) AS count
FROM jobs
GROUP BY career_type
ORDER BY count DESC;

-- 고용 형태
SELECT employment_type, COUNT(*) AS count
FROM jobs
GROUP BY employment_type
ORDER BY count DESC;

-- 학력
SELECT education_type, COUNT(*) AS count
FROM jobs
GROUP BY education_type
ORDER BY count DESC;

-- 신입 + 정규직
SELECT COUNT(*) AS count
FROM jobs
WHERE career_type = '신입'
  AND employment_type = '정규직';

-- 신입 + 정규직 + 4년제 이상
SELECT COUNT(*) AS count
FROM jobs
WHERE career_type = '신입'
  AND employment_type = '정규직'
  AND education_type = '4년제 대학 이상';