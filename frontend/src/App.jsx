import { useEffect, useState } from 'react'
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useLocation,
} from 'react-router-dom'
import './App.css'


const API_URL = 'http://127.0.0.1:8000'


// --------------------------------------------------
// 헤더
// --------------------------------------------------

function Header() {
  const location = useLocation()

  return (
    <header className="header">
      <div className="logo">
        <Link to="/dashboard">JobInsight</Link>
      </div>

      <nav>
        <Link
          to="/dashboard"
          className={location.pathname === '/dashboard' ? 'active' : ''}
        >
          채용시장 분석
        </Link>

        <Link
          to="/jobs"
          className={location.pathname === '/jobs' ? 'active' : ''}
        >
          채용공고
        </Link>
      </nav>
    </header>
  )
}


// --------------------------------------------------
// 채용공고 카드
// --------------------------------------------------

function JobCard({ job, onDetail }) {
  return (
    <div className="job-card">
      <div className="job-company">
        {job.company_name}
      </div>

      <h3>{job.title}</h3>

      <p>
        {job.region} · {job.career_type} · {job.employment_type}
      </p>

      <p>
        {job.education_type} · 마감: {job.deadline}
      </p>

      <button
        className="detail-button"
        onClick={() => onDetail(job.job_id)}
      >
        미리보기
      </button>
    </div>
  )
}


// --------------------------------------------------
// 미리보기 모달
// --------------------------------------------------

function DetailModal({ job, loading, onClose }) {
  if (!job && !loading) {
    return null
  }

  return (
    <div
      className="detail-overlay"
      onClick={onClose}
    >
      <div
        className="detail-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="close-button"
          onClick={onClose}
        >
          ×
        </button>

        {loading ? (
          <div className="detail-loading">
            상세 공고를 불러오는 중...
          </div>
        ) : (
          <>
            <div className="detail-header">
              <p className="job-company">
                {job.company_name}
              </p>

              <h2>{job.title}</h2>

              <p>
                {job.region} · {job.career_type} ·{' '}
                {job.employment_type}
              </p>

              <p>
                {job.education_type} · 마감: {job.deadline}
              </p>
            </div>

            <div className="detail-content">
              {job.detail_sections &&
              Object.keys(job.detail_sections).length > 0 ? (
                Object.entries(job.detail_sections)
                  .filter(([sectionName]) =>
                    ['주요업무', '자격요건', '우대사항'].includes(
                      sectionName
                    )
                  )
                  .map(([sectionName, content]) => (
                    <section
                      className="detail-section"
                      key={sectionName}
                    >
                      <h3>{sectionName}</h3>

                      <div className="detail-text">
                        {content}
                      </div>
                    </section>
                  ))
              ) : (
                <p className="no-detail">
                  표시할 미리보기 내용이 없습니다.
                </p>
              )}

              <div className="original-job">
                <a
                  href={job.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  사람인 원문 공고 보기 →
                </a>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}


// --------------------------------------------------
// 채용시장 분석 페이지
// --------------------------------------------------

function DashboardPage({ onDetail }) {
  const [stats, setStats] = useState(null)

  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchResult, setSearchResult] = useState(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchPage, setSearchPage] = useState(1)

  const searchLimit = 20

  useEffect(() => {
    fetch(`${API_URL}/jobs/stats`)
      .then((response) => response.json())
      .then((data) => {
        setStats(data)
      })
      .catch((error) => {
        console.error('통계 API 호출 오류:', error)
      })
  }, [])


  const searchKeywordJobs = (selectedPage = 1) => {
    const keyword = searchKeyword.trim()

    if (!keyword) {
      setSearchResult(null)
      return
    }

    setSearchLoading(true)
    setSearchPage(selectedPage)

    fetch(
      `${API_URL}/jobs/search?keyword=${encodeURIComponent(
        keyword
      )}&page=${selectedPage}&limit=${searchLimit}`
    )
      .then((response) => response.json())
      .then((data) => {
        setSearchResult(data)
        setSearchLoading(false)
      })
      .catch((error) => {
        console.error('키워드 검색 API 호출 오류:', error)
        setSearchLoading(false)
      })
  }


  const totalSearchPages = searchResult
    ? Math.ceil(searchResult.total / searchLimit)
    : 0


  return (
    <main>
      <section className="hero">
        <p className="eyebrow">JOBINSIGHT</p>

        <h1>
          신입 IT·데이터
          <br />
          채용시장 분석
        </h1>

        <p>
          채용공고 데이터를 분석하고
          원하는 키워드의 채용시장 정보를 확인해보세요.
        </p>
      </section>


      {/* 통계 */}
      <section className="stats-section">
        <div className="section-title">
          <p className="eyebrow">JOB MARKET</p>
          <h2>전체 채용시장 분석</h2>
        </div>

        {stats && (
          <div className="stats-grid">

            <div className="stats-card">
              <h3>경력 구분</h3>

              {stats.career.map((item) => (
                <div
                  className="stats-row"
                  key={item.career_type}
                >
                  <span>{item.career_type}</span>
                  <strong>{item.count}건</strong>
                </div>
              ))}
            </div>


            <div className="stats-card">
              <h3>고용 형태</h3>

              {stats.employment.map((item) => (
                <div
                  className="stats-row"
                  key={item.employment_type}
                >
                  <span>{item.employment_type}</span>
                  <strong>{item.count}건</strong>
                </div>
              ))}
            </div>


            <div className="stats-card">
              <h3>학력 구분</h3>

              {stats.education.map((item) => (
                <div
                  className="stats-row"
                  key={item.education_type}
                >
                  <span>{item.education_type}</span>
                  <strong>{item.count}건</strong>
                </div>
              ))}
            </div>

          </div>
        )}
      </section>


      {/* 키워드 검색 */}
      <section className="keyword-search-section">

        <div className="section-title">
          <p className="eyebrow">KEYWORD SEARCH</p>

          <h2>채용공고 키워드 검색</h2>

          <p>
            주요업무·자격요건·우대사항에서
            원하는 키워드를 검색하세요.
          </p>
        </div>


        <div className="keyword-search-box">

          <input
            type="text"
            value={searchKeyword}
            onChange={(e) =>
              setSearchKeyword(e.target.value)
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                searchKeywordJobs(1)
              }
            }}
            placeholder="예: Python, Java, React, SQL"
          />

          <button
            onClick={() => searchKeywordJobs(1)}
          >
            검색
          </button>

        </div>


        {searchLoading && (
          <p className="keyword-loading">
            검색 중...
          </p>
        )}


        {searchResult && !searchLoading && (
          <div className="keyword-result">

            <div className="keyword-summary">

              <h3>
                '{searchResult.keyword}' 검색 결과
              </h3>

              <strong>
                {searchResult.total}건
              </strong>

            </div>


            <div className="keyword-section-counts">

              <div>
                <span>주요업무</span>
                <strong>
                  {searchResult.section_counts['주요업무']}건
                </strong>
              </div>

              <div>
                <span>자격요건</span>
                <strong>
                  {searchResult.section_counts['자격요건']}건
                </strong>
              </div>

              <div>
                <span>우대사항</span>
                <strong>
                  {searchResult.section_counts['우대사항']}건
                </strong>
              </div>

            </div>


            <div className="keyword-jobs">

              {searchResult.jobs.map((job) => (
                <JobCard
                  key={job.job_id}
                  job={job}
                  onDetail={onDetail}
                />
              ))}

            </div>


            {searchResult.jobs.length === 0 && (
              <p className="no-search-result">
                검색 결과가 없습니다.
              </p>
            )}


            {/* 검색 결과 페이지 */}
            {searchResult.total > searchLimit && (
              <div className="pagination">

                <button
                  onClick={() =>
                    searchKeywordJobs(searchPage - 1)
                  }
                  disabled={searchPage === 1}
                >
                  이전
                </button>

                <span>
                  {searchPage} / {totalSearchPages}
                </span>

                <button
                  onClick={() =>
                    searchKeywordJobs(searchPage + 1)
                  }
                  disabled={
                    searchPage >= totalSearchPages
                  }
                >
                  다음
                </button>

              </div>
            )}

          </div>
        )}

      </section>
    </main>
  )
}


// --------------------------------------------------
// 채용공고 페이지
// --------------------------------------------------

function JobsPage({ onDetail }) {

  const [career, setCareer] = useState('')
  const [employment, setEmployment] = useState('')
  const [education, setEducation] = useState('')

  const [jobs, setJobs] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)

  const limit = 20


  const searchJobs = (selectedPage = 1) => {

    setLoading(true)
    setPage(selectedPage)

    const params = new URLSearchParams()

    params.append('page', selectedPage)
    params.append('limit', limit)

    if (career) {
      params.append('career_type', career)
    }

    if (employment) {
      params.append('employment_type', employment)
    }

    if (education) {
      params.append('education_type', education)
    }


    fetch(`${API_URL}/jobs?${params.toString()}`)
      .then((response) => response.json())
      .then((data) => {
        setJobs(data.jobs)
        setTotal(data.total)
        setLoading(false)
      })
      .catch((error) => {
        console.error('API 호출 오류:', error)
        setLoading(false)
      })
  }


  useEffect(() => {
    searchJobs(1)
  }, [])


  const totalPages = Math.ceil(total / limit)


  return (
    <main>

      <section className="hero">

        <p className="eyebrow">JOBINSIGHT</p>

        <h1>
          신입 IT·데이터
          <br />
          채용공고
        </h1>

        <p>
          채용 조건을 선택하고 원하는 채용공고를 찾아보세요.
        </p>

      </section>


      {/* 조건 검색 */}
      <section className="filter-section">

        <div className="section-title">

          <p className="eyebrow">
            SEARCH FILTER
          </p>

          <h2>채용 조건 선택</h2>

        </div>


        <div className="filters">

          <div className="filter">

            <label>경력</label>

            <select
              value={career}
              onChange={(e) =>
                setCareer(e.target.value)
              }
            >
              <option value="">전체</option>
              <option value="신입">신입</option>
              <option value="신입/경력">신입/경력</option>
              <option value="경력무관">경력무관</option>
            </select>

          </div>


          <div className="filter">

            <label>고용형태</label>

            <select
              value={employment}
              onChange={(e) =>
                setEmployment(e.target.value)
              }
            >
              <option value="">전체</option>
              <option value="정규직">정규직</option>
              <option value="정규직 외">정규직 외</option>
            </select>

          </div>


          <div className="filter">

            <label>학력</label>

            <select
              value={education}
              onChange={(e) =>
                setEducation(e.target.value)
              }
            >
              <option value="">전체</option>
              <option value="4년제 대학 이상">
                4년제 대학 이상
              </option>
              <option value="학력무관">
                학력무관
              </option>
              <option value="전문대 이상">
                전문대 이상
              </option>
              <option value="고졸 이상">
                고졸 이상
              </option>
              <option value="석사 이상">
                석사 이상
              </option>
            </select>

          </div>


          <button
            className="search-button"
            onClick={() => searchJobs(1)}
          >
            조건 검색
          </button>

        </div>

      </section>


      {/* 검색 결과 */}
      <section className="result-section">

        <div>

          <p className="eyebrow">
            SEARCH RESULT
          </p>

          <h2>현재 조건의 채용공고</h2>

        </div>


        <div className="result-count">

          <strong>{total}</strong>

          <span>건</span>

        </div>


        <p className="selected-condition">

          {career || '전체 경력'} ·{' '}
          {employment || '전체 고용형태'} ·{' '}
          {education || '전체 학력'}

        </p>

      </section>


      {/* 공고 목록 */}
      <section id="jobs" className="jobs-section">

        {loading ? (

          <p>채용공고를 불러오는 중...</p>

        ) : (

          jobs.map((job) => (
            <JobCard
              key={job.job_id}
              job={job}
              onDetail={onDetail}
            />
          ))

        )}

      </section>


      {/* 페이지네이션 */}
      <div className="pagination">

        <button
          onClick={() => searchJobs(page - 1)}
          disabled={page === 1}
        >
          이전
        </button>

        <span>
          {page} / {totalPages}
        </span>

        <button
          onClick={() => searchJobs(page + 1)}
          disabled={page >= totalPages}
        >
          다음
        </button>

      </div>

    </main>
  )
}


// --------------------------------------------------
// App
// --------------------------------------------------

function App() {

  const [selectedJob, setSelectedJob] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)


  const openJobDetail = (jobId) => {

    setDetailLoading(true)
    setSelectedJob(null)

    fetch(`${API_URL}/jobs/${jobId}`)
      .then((response) => response.json())
      .then((data) => {
        setSelectedJob(data)
        setDetailLoading(false)
      })
      .catch((error) => {
        console.error('상세 공고 API 호출 오류:', error)
        setDetailLoading(false)
      })
  }


  const closeJobDetail = () => {
    setSelectedJob(null)
    setDetailLoading(false)
  }


  return (
    <BrowserRouter>

      <div className="app">

        <Header />

        <Routes>

          <Route
            path="/"
            element={
              <DashboardPage
                onDetail={openJobDetail}
              />
            }
          />

          <Route
            path="/dashboard"
            element={
              <DashboardPage
                onDetail={openJobDetail}
              />
            }
          />

          <Route
            path="/jobs"
            element={
              <JobsPage
                onDetail={openJobDetail}
              />
            }
          />

        </Routes>


        {/* 상세 모달은 페이지 공통 */}
        <DetailModal
          job={selectedJob}
          loading={detailLoading}
          onClose={closeJobDetail}
        />

      </div>

    </BrowserRouter>
  )
}


export default App