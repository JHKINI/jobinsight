CREATE DATABASE IF NOT EXISTS jobinsight_db;

USE jobinsight_db;

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
);

CREATE TABLE IF NOT EXISTS job_details (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    detail_sections JSON NOT NULL,
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_job_details_job
        FOREIGN KEY (job_id)
        REFERENCES jobs(job_id)
        ON DELETE CASCADE
);