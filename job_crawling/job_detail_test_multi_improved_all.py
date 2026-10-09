import json
import os
import random
import re
import time
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

# JobInsight - 전체 채용공고 멀티 크롤러 (개선 파서 + DB + JSON/CSV)
# 입력 CSV의 모든 URL을 처리하며, TEST_LIMIT으로 일부 테스트 가능
# ========================= 설정 =========================
CSV_FILE = "saramin_jobs_clean.csv"
DIAG_CSV_FILE = "jobinsight_parsing_diagnosis_v2.csv"
RESULT_CSV_FILE = "job_detail_retry40_improved_v7_results.csv"
SLEEP_MIN_SECONDS = 3
SLEEP_MAX_SECONDS = 5
REQUEST_TIMEOUT = 15

# 섹션 별칭: 공백/기호 차이는 정규화 후 비교
SECTION_ALIASES_RAW = {
    "주요업무": "주요업무", "담당업무": "주요업무", "업무내용": "주요업무",
    "주요업무내용": "주요업무", "수행업무": "주요업무", "직무내용": "주요업무",
    "모집업무": "주요업무", "하는일": "주요업무", "업무": "주요업무", "직무": "주요업무", "담당": "주요업무",
    "자격요건": "자격요건", "지원자격": "자격요건", "필수요건": "자격요건",
    "지원요건": "자격요건", "자격사항": "자격요건", "응시자격": "자격요건", "자격": "자격요건",
    "필수자격": "자격요건", "지원자격요건": "자격요건",
    "필수및우대자격요건": "자격요건및우대사항", "필수및우대요건": "자격요건및우대사항",
    "필수우대자격요건": "자격요건및우대사항", "필수및우대자격": "자격요건및우대사항",
    "우대사항": "우대사항", "우대요건": "우대사항", "우대조건": "우대사항",
    "우대자격": "우대사항", "우대경험": "우대사항",
    "고용형태": "고용형태", "근무형태": "고용형태", "채용형태": "고용형태",
    "근무지": "근무지", "근무지역": "근무지", "근무장소": "근무지", "勤務地": "근무지",
    "근무조건": "근무조건", "근무환경": "근무조건", "근무시간": "근무조건",
    "급여": "근무조건", "급여조건": "근무조건", "보수": "근무조건",
    "채용절차": "채용절차", "전형절차": "채용절차", "전형방법": "채용절차",
    "채용과정": "채용절차", "진행절차": "채용절차", "전형": "채용절차",
    "접수기간": "접수기간", "모집기간": "접수기간", "지원기간": "접수기간", "접수": "접수방법",
    "접수방법": "접수방법", "지원방법": "접수방법", "지원방법및기간": "접수방법",
    "제출서류": "제출서류", "구비서류": "제출서류", "필요서류": "제출서류",
    "복리후생": "복리후생", "복리혜택": "복리후생", "혜택": "복리후생",
    "인재상": "인재상", "기업문화": "기업문화", "회사소개": "회사소개",
    "안내사항": "안내사항", "유의사항": "안내사항", "기타사항": "안내사항",
    "참고사항": "안내사항", "문의": "안내사항", "문의처": "안내사항",
    "모집부문": "모집부문", "모집분야": "모집부문", "채용분야": "모집부문",
    "담당직무": "주요업무", "직무소개": "주요업무", "직무": "주요업무",
}


def normalize_title(value: str) -> str:
    """제목 비교용 정규화: 공백/기호/괄호를 제거하고 한글·영문·숫자만 비교."""
    value = str(value or "").strip().lower()
    value = re.sub(r"[\U00010000-\U0010ffff]", "", value)
    return re.sub(r"[^0-9a-z가-힣]", "", value)


SECTION_ALIASES = {normalize_title(k): v for k, v in SECTION_ALIASES_RAW.items()}
COMBINED_REQUIREMENTS = {"자격요건및우대사항", "지원자격및우대사항", "자격및우대사항", "필수및우대자격요건", "필수및우대요건", "필수우대자격요건", "필수및우대자격"}


def clean_text(value: str) -> str:
    value = (value or "").replace("\xa0", " ").replace("\u200b", "")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    return value.strip()


def extract_dom_lines(content: Tag):
    """상세 본문을 추출한다. 표의 제목 셀과 값 셀을 합쳐 제목+내용 손실을 줄인다."""
    lines = []
    seen = set()

    for bad in content.select("script, style, noscript, iframe, button"):
        bad.decompose()

    def add_line(value):
        value = clean_text(value)
        if value and value not in seen:
            lines.append(value)
            seen.add(value)

    # 표는 행 전체 텍스트보다 셀 경계를 먼저 보존한다.
    for node in content.find_all(["h1", "h2", "h3", "h4", "h5", "p", "li", "tr", "dt", "dd", "b", "strong", "div"]):
        if node.name == "tr":
            cells = node.find_all(["th", "td"], recursive=False)
            raw_values = [clean_text(cell.get_text("\n", strip=True)) for cell in cells]
            values = [v for v in raw_values if v]
            if not values:
                continue

            # 안국약품 화면처럼 표의 열 제목이 '모집부서 | 담당직무 | 필수 및 우대 자격요건'인 경우,
            # 각 데이터 행을 업무/자격요건으로 분리한다. 단순히 표 전체를 한 줄로 합치면
            # 세 번째 열의 필수·우대 요건을 놓치거나 업무 내용과 섞일 수 있다.
            table = node.find_parent("table")
            header_cells = []
            if table:
                for candidate_row in table.find_all("tr"):
                    candidate_cells = candidate_row.find_all(["th", "td"], recursive=False)
                    candidate_values = [clean_text(c.get_text("\n", strip=True)) for c in candidate_cells]
                    candidate_norms = [normalize_title(v) for v in candidate_values]
                    if any("필수및우대자격요건" in x or "필수및우대요건" in x for x in candidate_norms):
                        header_cells = candidate_values
                        break
            header_norms = [normalize_title(v) for v in header_cells]
            req_col = next((i for i, x in enumerate(header_norms) if any(k in x for k in ("필수및우대자격요건", "필수및우대요건", "필수우대자격요건"))), None)
            duty_col = next((i for i, x in enumerate(header_norms) if x in {"담당직무", "업무내용", "주요업무", "담당업무"}), None)
            dept_col = next((i for i, x in enumerate(header_norms) if x in {"모집부서", "모집부문", "모집분야"}), None)
            current_norms = [normalize_title(v) for v in raw_values]
            is_header_row = any("필수및우대자격요건" in x or "필수및우대요건" in x for x in current_norms)
            if is_header_row:
                continue
            if header_cells and (req_col is not None or duty_col is not None):
                if dept_col is not None and dept_col < len(raw_values) and raw_values[dept_col]:
                    add_line(f"모집부문: {raw_values[dept_col]}")
                if duty_col is not None and duty_col < len(raw_values) and raw_values[duty_col]:
                    add_line(f"주요업무: {raw_values[duty_col]}")
                if req_col is not None and req_col < len(raw_values) and raw_values[req_col]:
                    add_line(f"필수 및 우대 자격요건: {raw_values[req_col]}")
                continue

            # 한 셀이 섹션 제목이고 나머지 셀에 내용이 있는 경우 한 줄로 합쳐
            # 기존 파서가 제목 행의 나머지 값을 버리는 문제를 방지한다.
            heading_cell = next((v for v in values if normalize_title(v) in SECTION_ALIASES), None)
            if heading_cell and len(values) > 1:
                heading_norm = normalize_title(heading_cell)
                heading = SECTION_ALIASES[heading_norm]
                rest = [v for v in values if v != heading_cell]
                add_line(f"{heading_cell}: {' | '.join(rest)}")
            else:
                add_line(" | ".join(values))
        else:
            # 중첩 li/p가 부모와 자식에서 중복되는 현상을 줄이기 위해
            # 자식 목록·문단이 들어 있는 노드는 텍스트를 한 번만 수집한다.
            if node.name in {"li", "p"} and node.find(["li", "p"]):
                continue
            # 셀트리온 등 카드형 공고는 제목/본문이 h2, p, li가 아닌 div에 들어간다.
            # div는 섹션 제목이거나 실제 텍스트를 담은 말단 div인 경우에만 수집한다.
            node_text = clean_text(node.get_text(" ", strip=True))
            if node.name in {"b", "strong", "div"}:
                normalized = normalize_title(node_text)
                numbered = re.match(r"^\s*(?:제\s*)?\d{1,2}\s*[.．、)）:：-]\s*(.+)$", node_text)
                numbered_norm = normalize_title(numbered.group(1)) if numbered else ""
                is_heading = normalized in SECTION_ALIASES or numbered_norm in SECTION_ALIASES
                if node.name in {"b", "strong"} and not is_heading:
                    continue
                if node.name == "div":
                    # 섹션명 div는 수집. 그 외에는 자식 div/p/li가 없는 말단 div만 수집해
                    # 상위 컨테이너의 전체 텍스트가 반복되는 것을 방지한다.
                    has_content_children = node.find(["div", "p", "li", "ul", "ol", "table", "section"]) is not None
                    if not is_heading and has_content_children:
                        continue
                    if not is_heading and len(node_text) < 2:
                        continue
            add_line(node_text)

    # 전체 본문 텍스트는 DOM의 원문 순서로 별도 보존한다.
    full_lines = [clean_text(x) for x in content.get_text("\n", strip=True).splitlines()]
    full_lines = [line for line in full_lines if line]
    dedup_full = []
    full_seen = set()
    for line in full_lines:
        if line not in full_seen:
            dedup_full.append(line)
            full_seen.add(line)

    # 구조 노드가 거의 없는 공고에서는 원문 줄을 파싱 입력으로 사용한다.
    if len(lines) < 3 and len(dedup_full) > len(lines):
        lines = dedup_full[:]
    return lines, "\n".join(lines), "\n".join(dedup_full)


def split_cell_line(line: str):
    """표 행에서 셀 경계를 활용하되 원문 줄도 유지한다."""
    return [clean_text(x) for x in re.split(r"\s*(?:\||｜|\t|：|:)\s*", line) if clean_text(x)]


def match_heading(line: str):
    """독립 제목, 표 셀 제목, '주요업무: ...'를 감지한다."""
    raw = clean_text(line)
    if not raw:
        return []

    # 화면에서 확인된 형태: '2. 지원자격', '3. 전형방법'처럼
    # 번호가 붙은 제목을 먼저 분리한다.
    numbered = re.match(r"^\s*(?:제\s*)?\d{1,2}\s*[.．、)）:：-]\s*(.+?)\s*$", raw)
    if numbered:
        numbered_title = clean_text(numbered.group(1))
        numbered_norm = normalize_title(numbered_title)
        if numbered_norm in SECTION_ALIASES:
            return [(SECTION_ALIASES[numbered_norm], "")]
        # 제목 뒤에 콜론으로 내용이 이어지는 번호형 제목도 지원
        numbered_inline = re.match(r"^(.+?)\s*[:：]\s*(.+)$", numbered_title)
        if numbered_inline:
            n_title = normalize_title(numbered_inline.group(1))
            if n_title in SECTION_ALIASES:
                return [(SECTION_ALIASES[n_title], clean_text(numbered_inline.group(2)))]

    # 먼저 제목과 내용이 한 줄에 붙은 형태를 확인한다.
    # '담당업무: 데이터 분석'에서 ':' 기준으로 나누기 전에 처리해야 한다.
    m = re.match(r"^\s*[\[\(【〈《「『]?\s*(.+?)\s*[:：]\s*(.+?)\s*[\]\)】〉》」』]?\s*$", raw)
    if m:
        title_norm = normalize_title(m.group(1))
        if title_norm in COMBINED_REQUIREMENTS:
            return [("자격요건및우대사항", clean_text(m.group(2)))]
        if title_norm in SECTION_ALIASES:
            return [(SECTION_ALIASES[title_norm], clean_text(m.group(2)))]

    parts = [raw] + split_cell_line(raw)
    matches = []
    for candidate in parts:
        norm = normalize_title(candidate)
        if norm in COMBINED_REQUIREMENTS:
            matches.extend([("자격요건", ""), ("우대사항", "")])
        elif norm in SECTION_ALIASES:
            matches.append((SECTION_ALIASES[norm], ""))
    # 중복 제거하되 같은 행에 서로 다른 섹션 제목이 있으면 둘 다 유지
    return list(dict.fromkeys(matches))

def extract_detail_sections(lines, full_text, image_alt_text=""):
    """섹션 제목과 같은 줄의 내용을 보존하고, 일부 섹션만 감지돼도 원문을 유지한다."""
    # '필수 및 우대 자격요건' 열은 필수/우대 항목이 한 셀에 함께 있으므로
    # 줄 단위로 분리한 뒤 '우대' 표현이 있는 항목을 우대사항으로 분류한다.
    expanded_lines = []
    for line in lines:
        m_combined = re.match(r"^\s*필수\s*및\s*우대\s*자격요건\s*[:：]\s*(.*)$", line, flags=re.S)
        if m_combined:
            for item in re.split(r"\n+", m_combined.group(1)):
                item = clean_text(item).lstrip("•·-▪◦ ")
                if item:
                    section = "우대사항" if "우대" in item else "자격요건"
                    expanded_lines.append(f"{section}: {item}")
        else:
            expanded_lines.append(line)
    lines = expanded_lines

    found = []
    for idx, line in enumerate(lines):
        for section, inline_content in match_heading(line):
            found.append((idx, section, inline_content))

    # 동일 인덱스의 서로 다른 제목은 유지한다.
    unique = []
    seen = set()
    for item in found:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    found = unique

    sections = {}
    for pos, (start, section, inline_content) in enumerate(found):
        later = [item[0] for item in found[pos + 1:] if item[0] > start]
        end = min(later) if later else len(lines)
        chunk = [inline_content] if inline_content else []
        for line in lines[start + 1:end]:
            headings = match_heading(line)
            # 다음 섹션 제목 줄은 내용에 넣지 않되, 제목+내용 형태면 그 내용은
            # 해당 섹션에서 이미 inline_content로 처리한다.
            if headings:
                continue
            if line and (not chunk or line != chunk[-1]):
                chunk.append(line)
        value = "\n".join(x for x in chunk if x).strip()
        if value:
            sections[section] = (sections.get(section, "") + "\n" + value).strip()

    # '필수 및 우대 자격요건'처럼 한 열에 필수/우대가 함께 있는 경우,
    # 셀 안의 줄바꿈을 기준으로 항목을 나누고 '우대'가 포함된 항목은 우대사항으로 분류한다.
    combined_keys = [key for key in sections if normalize_title(key) in COMBINED_REQUIREMENTS]
    for key in combined_keys:
        combined_text = sections.pop(key)
        for item in re.split(r"\n+", combined_text):
            item = clean_text(item).lstrip("•·-▪◦ ")
            if not item:
                continue
            target = "우대사항" if "우대" in item else "자격요건"
            sections[target] = (sections.get(target, "") + "\n" + item).strip()

    # 섹션 구조화가 부분 성공이어도 전체 텍스트를 별도 컬럼에서 보존하고,
    # JSON에도 상세내용을 남겨 누락된 나머지 공고 내용을 잃지 않게 한다.
    if full_text.strip():
        sections["상세내용"] = full_text.strip()
    elif not sections and image_alt_text.strip():
        sections["이미지대체텍스트"] = image_alt_text.strip()
    return sections, len(found)


def get_user_content(session, job_url, headers):
    res = session.get(job_url, headers=headers, timeout=REQUEST_TIMEOUT)
    res.raise_for_status()
    query = parse_qs(urlparse(job_url).query)
    rec_idx = query.get("rec_idx", [None])[0]
    if not rec_idx:
        raise ValueError("URL에서 rec_idx를 찾을 수 없음")

    ajax_url = "https://www.saramin.co.kr/zf_user/jobs/relay/view-ajax"
    ajax_headers = {
        "User-Agent": headers["User-Agent"],
        "Accept": "text/html, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.saramin.co.kr",
        "Referer": job_url,
    }
    payload = {
        "rec_idx": rec_idx, "rec_seq": "0", "view_type": "public-recruit",
        "utm_source": "", "utm_medium": "", "utm_term": "", "utm_campaign": "",
        "t_ref": "", "t_ref_content": "", "t_ref_scnid": "", "search_uuid": "",
        "refer": "", "searchType": "", "searchword": "",
        "ref_dp": "SRI_050_VIEW_MIX_RCT_BBS_NLG", "dpId": "",
        "recommendRecIdx": "", "referNonce": "", "trainingStudentCode": "",
    }
    ajax_res = session.post(ajax_url, headers=ajax_headers, data=payload, timeout=REQUEST_TIMEOUT)
    ajax_res.raise_for_status()
    iframe = BeautifulSoup(ajax_res.text, "html.parser").select_one("#iframe_content_0")
    if not iframe or not iframe.get("src"):
        raise ValueError("AJAX 응답에서 상세 본문 iframe을 찾지 못함")

    detail_url = urljoin("https://www.saramin.co.kr", iframe["src"])
    detail_res = session.get(
        detail_url,
        headers={"User-Agent": headers["User-Agent"], "Referer": job_url},
        timeout=REQUEST_TIMEOUT,
    )
    detail_res.raise_for_status()
    soup = BeautifulSoup(detail_res.text, "html.parser")
    content = soup.select_one(".user_content")
    if content is None:
        raise ValueError("상세 본문 .user_content를 찾지 못함")
    return content



from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ========================= 운영 설정 =========================
# 전체 채용공고 목록(saramin_jobs_clean.csv)의 URL을 대상으로 실행
# 첫 검증은 3건만 실행하고, 결과 확인 후 TEST_LIMIT = None으로 변경
MODE = "all"
TEST_LIMIT = 3

# 전체 공고 목록 CSV를 기준으로 실행하므로 실패 목록 파일은 선택에 사용하지 않음
PREVIOUS_RESULT_CSV = "job_detail_retry40_improved_v7_results.csv"
FAILED_DB_CSV = "jobinsight_parsing_failed_40.csv"

SAVE_TO_DB = True
EXPORT_JSON = True
RESULT_PREFIX = "jobinsight_detail_crawl"


def create_db_engine():
    """프로젝트 .env의 MYSQL_* 설정으로 DB 연결을 구성한다."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    database = os.getenv("MYSQL_DATABASE", "jobinsight_db")
    if not user or password is None:
        raise RuntimeError(".env에 MYSQL_USER와 MYSQL_PASSWORD를 설정하세요.")
    url = URL.create(
        "mysql+pymysql", username=user, password=password,
        host=host, port=port, database=database, query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True, future=True)


def get_job_id_map(engine):
    """jobs 테이블의 URL → job_id 매핑. DB 스키마는 기존 JobInsight 기준."""
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT job_id, url FROM jobs WHERE url IS NOT NULL")).fetchall()
    return {str(row.url).strip(): row.job_id for row in rows if row.url}


def get_existing_detail_map(engine):
    """기존 상세정보를 읽어 새 결과가 더 빈약할 때 기존 성공 데이터를 보호한다."""
    existing = {}
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT job_id, detail_sections FROM job_details")).fetchall()
    for row in rows:
        try:
            value = row.detail_sections
            if isinstance(value, str):
                value = json.loads(value or "{}")
            existing[row.job_id] = value if isinstance(value, dict) else {}
        except Exception:
            existing[row.job_id] = {}
    return existing


def has_structured_sections(sections):
    """본문 원문/이미지 alt만 있는 결과가 아니라 분류된 섹션이 있는지 확인한다."""
    return any(k not in {"상세내용", "이미지대체텍스트"} for k in (sections or {}))


def save_detail(engine, job_id, sections):
    """job_details의 해당 job_id 상세정보를 갱신한다. 다른 공고 데이터는 건드리지 않는다."""
    payload = json.dumps(sections, ensure_ascii=False)
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT detail_id FROM job_details WHERE job_id = :job_id LIMIT 1"),
            {"job_id": job_id},
        ).fetchone()
        if exists:
            conn.execute(
                text("UPDATE job_details SET detail_sections = :detail_sections WHERE job_id = :job_id"),
                {"job_id": job_id, "detail_sections": payload},
            )
        else:
            conn.execute(
                text("INSERT INTO job_details (job_id, detail_sections) VALUES (:job_id, :detail_sections)"),
                {"job_id": job_id, "detail_sections": payload},
            )


def crawl_one(row, headers):
    url = str(row.get("URL", "")).strip()
    company = str(row.get("회사명", row.get("company_name", "")))
    title = str(row.get("공고명", row.get("title", "")))
    session = requests.Session()
    try:
        content = get_user_content(session, url, headers)
        lines, dom_text, full_text = extract_dom_lines(content)
        image_urls, image_alts = [], []
        for img in content.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-original") or ""
            alt = clean_text(img.get("alt", ""))
            if src:
                image_urls.append(urljoin(url, src))
            if alt:
                image_alts.append(alt)
        image_urls = list(dict.fromkeys(image_urls))
        alt_text = "\n".join(dict.fromkeys(image_alts))
        sections, heading_hits = extract_detail_sections(lines, full_text or dom_text, alt_text)
        structured = [k for k in sections if k not in {"상세내용", "이미지대체텍스트"}]
        if structured:
            status = "섹션 구조화"
        elif sections.get("상세내용"):
            status = "본문 텍스트 보존(제목 분류 실패)"
        elif sections.get("이미지대체텍스트") or image_urls:
            status = "이미지 중심(OCR 별도 필요 가능)"
        else:
            status = "본문 텍스트 없음"
        return {
            "회사명": company, "공고명": title, "URL": url,
            "상태": status, "추출섹션": list(sections.keys()),
            "구조화섹션수": len(structured), "제목감지수": heading_hits,
            "본문글자수": len(full_text), "DOM추출글자수": len(dom_text),
            "이미지수": len(image_urls), "이미지URL": image_urls,
            "이미지대체텍스트": alt_text, "본문전체텍스트": full_text,
            "DOM구조텍스트": dom_text, "detail_sections": sections,
            "오류": "",
        }
    except Exception as exc:
        return {
            "회사명": company, "공고명": title, "URL": url,
            "상태": "요청/처리 실패", "추출섹션": [],
            "구조화섹션수": 0, "제목감지수": 0, "본문글자수": 0,
            "DOM추출글자수": 0, "이미지수": 0, "이미지URL": [],
            "이미지대체텍스트": "", "본문전체텍스트": "",
            "DOM구조텍스트": "", "detail_sections": {},
            "오류": f"{type(exc).__name__}: {exc}",
        }
    finally:
        session.close()


def load_retry_failed_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    """이전 파싱 결과에서 구조화가 안 된 URL만 골라 원본 공고 CSV와 연결한다."""
    if os.path.exists(PREVIOUS_RESULT_CSV):
        previous = pd.read_csv(PREVIOUS_RESULT_CSV, dtype=str).fillna("")
        if "URL" not in previous.columns or "상태" not in previous.columns:
            raise ValueError(f"{PREVIOUS_RESULT_CSV}에 URL/상태 컬럼이 필요합니다.")
        # 구조화 성공만 제외. 본문 텍스트만 보존되었거나 이미지 중심인 공고는 재검토 대상.
        failed_urls = set(previous.loc[previous["상태"] != "섹션 구조화", "URL"].astype(str).str.strip())
        failed_urls.discard("")
        print(f"이전 결과 기준 재시도 후보: {len(failed_urls)}건 ({PREVIOUS_RESULT_CSV})")
        return jobs[jobs["URL"].astype(str).str.strip().isin(failed_urls)].copy()

    if os.path.exists(FAILED_DB_CSV):
        failed = pd.read_csv(FAILED_DB_CSV, dtype=str).fillna("")
        url_col = "url" if "url" in failed.columns else "URL"
        failed_urls = set(failed[url_col].astype(str).str.strip())
        failed_urls.discard("")
        print(f"빈 상세정보 목록 기준 재시도 후보: {len(failed_urls)}건 ({FAILED_DB_CSV})")
        return jobs[jobs["URL"].astype(str).str.strip().isin(failed_urls)].copy()

    raise FileNotFoundError(
        "재시도 목록을 찾지 못했습니다. PREVIOUS_RESULT_CSV 또는 FAILED_DB_CSV 경로를 확인하세요."
    )


def load_new_or_empty_jobs(jobs: pd.DataFrame, engine) -> pd.DataFrame:
    """DB에 상세정보가 없거나 detail_sections가 빈 공고만 선택한다."""
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT job_id, detail_sections FROM job_details")).fetchall()
    existing_detail = {}
    for row in rows:
        try:
            value = row.detail_sections
            if isinstance(value, str):
                value = json.loads(value or "{}")
            existing_detail[row.job_id] = value if isinstance(value, dict) else {}
        except Exception:
            existing_detail[row.job_id] = {}

    url_to_id = get_job_id_map(engine)
    keep_urls = []
    for url in jobs["URL"].astype(str).str.strip():
        job_id = url_to_id.get(url)
        # jobs 테이블에 아직 없는 URL도 신규 공고일 수 있으므로 대상에 포함
        if job_id is None or job_id not in existing_detail or not existing_detail.get(job_id):
            keep_urls.append(url)
    return jobs[jobs["URL"].astype(str).str.strip().isin(set(keep_urls))].copy()


def main():
    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError(f"공고 CSV가 없습니다: {CSV_FILE}")
    jobs = pd.read_csv(CSV_FILE, dtype=str).fillna("")
    if "URL" not in jobs.columns:
        raise ValueError(f"CSV에 URL 열이 없습니다. 현재 열: {list(jobs.columns)}")
    jobs = jobs[jobs["URL"].astype(str).str.strip() != ""].drop_duplicates("URL").copy()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"{RESULT_PREFIX}_{MODE}_{timestamp}.json"
    csv_file = f"{RESULT_PREFIX}_{MODE}_{timestamp}.csv"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"}

    engine = None
    job_map = {}
    existing_detail_map = {}
    if SAVE_TO_DB:
        engine = create_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        job_map = get_job_id_map(engine)
        existing_detail_map = get_existing_detail_map(engine)
        print(f"DB 연결 확인 완료 | jobs URL 매핑: {len(job_map)}건")

    try:
        if MODE == "retry_failed":
            jobs = load_retry_failed_jobs(jobs)
        elif MODE == "new_or_empty":
            if engine is None:
                raise RuntimeError("new_or_empty 모드는 DB 연결이 필요합니다. SAVE_TO_DB=True로 설정하세요.")
            jobs = load_new_or_empty_jobs(jobs, engine)
        elif MODE != "all":
            raise ValueError("MODE는 retry_failed, new_or_empty, all 중 하나여야 합니다.")

        if TEST_LIMIT is not None:
            jobs = jobs.head(TEST_LIMIT)

        print(f"실행 모드: {MODE}")
        print(f"최종 대상 공고: {len(jobs)}건 | 대기: {SLEEP_MIN_SECONDS}~{SLEEP_MAX_SECONDS}초")
        results = []
        db_saved, db_missing, db_skipped_empty = 0, 0, 0

        for idx, (_, row) in enumerate(jobs.iterrows(), start=1):
            print(f"\n[{idx}/{len(jobs)}] {row.get('회사명', '')} | {row.get('공고명', '')}")
            result = crawl_one(row, headers)
            results.append(result)
            print(f"상태: {result['상태']} | 섹션: {result['추출섹션']} | 본문: {result['본문글자수']}자")

            # 요청 실패, 빈 결과, 기존보다 구조화 수준이 낮은 결과로 기존 데이터를 덮어쓰지 않는다.
            sections = result.get("detail_sections") or {}
            if SAVE_TO_DB and result["상태"] != "요청/처리 실패" and sections:
                job_id = job_map.get(result["URL"])
                if job_id is not None:
                    old_sections = existing_detail_map.get(job_id) or {}
                    new_is_structured = has_structured_sections(sections)
                    old_is_structured = has_structured_sections(old_sections)
                    # 새 결과가 구조화되지 않았는데 기존에는 구조화된 정보가 있으면 보존
                    if old_is_structured and not new_is_structured:
                        db_skipped_empty += 1
                        result["DB저장메모"] = "새 결과가 기존 구조화 데이터보다 불완전하여 기존 DB 유지"
                    else:
                        try:
                            save_detail(engine, job_id, sections)
                            existing_detail_map[job_id] = sections
                            db_saved += 1
                        except Exception as exc:
                            result["DB저장오류"] = f"{type(exc).__name__}: {exc}"
                            print(f"DB 저장 오류: {result['DB저장오류']}")
                else:
                    db_missing += 1
                    result["DB저장오류"] = "jobs 테이블에서 URL에 해당하는 job_id를 찾지 못함"
            elif SAVE_TO_DB and result["상태"] != "요청/처리 실패":
                db_skipped_empty += 1
                result["DB저장메모"] = "추출 결과가 비어 있어 기존 DB 데이터를 덮어쓰지 않음"

            if idx < len(jobs):
                delay = random.uniform(SLEEP_MIN_SECONDS, SLEEP_MAX_SECONDS)
                print(f"다음 공고까지 {delay:.1f}초 대기")
                time.sleep(delay)

        export_rows = []
        csv_rows = []
        for item in results:
            export_rows.append({
                "회사명": item["회사명"], "공고명": item["공고명"], "URL": item["URL"],
                "상태": item["상태"], "detail_sections": item["detail_sections"],
                "이미지URL": item["이미지URL"], "이미지대체텍스트": item["이미지대체텍스트"],
                "오류": item["오류"],
                **({"DB저장오류": item["DB저장오류"]} if item.get("DB저장오류") else {}),
                **({"DB저장메모": item["DB저장메모"]} if item.get("DB저장메모") else {}),
            })
            row_copy = dict(item)
            row_copy["추출섹션"] = ", ".join(row_copy["추출섹션"])
            row_copy["이미지URL"] = " | ".join(row_copy["이미지URL"])
            row_copy["추출결과JSON"] = json.dumps(row_copy.pop("detail_sections"), ensure_ascii=False)
            csv_rows.append(row_copy)

        if EXPORT_JSON:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(export_rows, f, ensure_ascii=False, indent=2)
        pd.DataFrame(csv_rows).to_csv(csv_file, index=False, encoding="utf-8-sig")

        print("\n" + "=" * 68)
        print(f"처리 완료: {len(results)}건")
        if results:
            print(pd.Series([x["상태"] for x in results]).value_counts().to_string())
        if SAVE_TO_DB:
            print(f"DB 저장 성공: {db_saved}건 | URL 매핑 누락: {db_missing}건 | 빈 결과 저장 건너뜀: {db_skipped_empty}건")
        if EXPORT_JSON:
            print(f"JSON 파일: {json_file}")
        print(f"CSV 검토 파일: {csv_file}")
        print("참고: 이미지 OCR은 수행하지 않으며, 이미지 URL과 alt 텍스트만 기록합니다.")
        print("=" * 68)
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
