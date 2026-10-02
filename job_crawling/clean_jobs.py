import pandas as pd

# 원본 CSV 불러오기
df = pd.read_csv(
    "saramin_jobs.csv",
    encoding="utf-8-sig"
)

print("=" * 60)
print("원본 데이터")
print("=" * 60)
print(f"데이터 수: {len(df)}건")


# ============================================================
# 1. 경력 구분
# ============================================================

def classify_career(value):

    if "경력무관" in value:
        return "경력무관"

    elif "신입 · 경력" in value:
        return "신입/경력"

    elif "신입" in value:
        return "신입"

    elif "경력" in value:
        return "경력"

    else:
        return "기타"


df["경력구분"] = df["경력/고용형태"].apply(classify_career)


# ============================================================
# 2. 고용형태
# ============================================================

def classify_employment(value):

    if "정규직 외" in value:
        return "정규직 외"

    elif "정규직" in value:
        return "정규직"

    else:
        return "기타"


df["고용형태"] = df["경력/고용형태"].apply(classify_employment)


# ============================================================
# 3. 학력 구분
# ============================================================

def classify_education(value):

    if "학력무관" in value:
        return "학력무관"

    elif "석사" in value:
        return "석사 이상"

    elif "대학교(4년)" in value:
        return "4년제 대학 이상"

    elif "대학(2,3년)" in value:
        return "전문대 이상"

    elif "고졸" in value:
        return "고졸 이상"

    else:
        return "기타"


df["학력구분"] = df["학력"].apply(classify_education)


# ============================================================
# 4. 중복 데이터 확인
# ============================================================

before = len(df)

df = df.drop_duplicates(subset=["URL"])

after = len(df)

print("\n중복 제거 결과")
print(f"제거 전: {before}건")
print(f"제거 후: {after}건")
print(f"제거된 중복: {before - after}건")


# ============================================================
# 5. 결측치 확인
# ============================================================

print("\n결측치 확인")
print(df.isnull().sum())


# ============================================================
# 6. 결과 확인
# ============================================================

print("\n" + "=" * 60)
print("경력구분 분포")
print("=" * 60)

print(df["경력구분"].value_counts())


print("\n" + "=" * 60)
print("고용형태 분포")
print("=" * 60)

print(df["고용형태"].value_counts())


print("\n" + "=" * 60)
print("학력구분 분포")
print("=" * 60)

print(df["학력구분"].value_counts())


# ============================================================
# 7. 정제 데이터 저장
# ============================================================

df.to_csv(
    "saramin_jobs_clean.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 60)
print("데이터 정제 완료!")
print("=" * 60)
print(f"최종 데이터: {len(df)}건")
print("파일명: saramin_jobs_clean.csv")
print("=" * 60)