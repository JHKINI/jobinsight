import pandas as pd

# CSV 불러오기
df = pd.read_csv(
    "saramin_jobs.csv",
    encoding="utf-8-sig"
)

print("=" * 60)
print("데이터 기본 정보")
print("=" * 60)

print(f"행 개수: {len(df)}")
print(f"열 개수: {len(df.columns)}")

print("\n컬럼명:")
print(df.columns.tolist())


print("\n" + "=" * 60)
print("데이터 미리보기")
print("=" * 60)

print(df.head())


print("\n" + "=" * 60)
print("결측치 확인")
print("=" * 60)

print(df.isnull().sum())


print("\n" + "=" * 60)
print("중복 URL 확인")
print("=" * 60)

print(f"전체 행 수: {len(df)}")
print(f"중복 URL 수: {df['URL'].duplicated().sum()}")


print("\n" + "=" * 60)
print("데이터 타입")
print("=" * 60)

print(df.dtypes)


print("\n" + "=" * 60)
print("각 컬럼의 고유값 개수")
print("=" * 60)

for column in df.columns:
    print(f"{column}: {df[column].nunique()}개")

print("\n" + "=" * 60)
print("경력/고용형태 종류")
print("=" * 60)

print(df["경력/고용형태"].value_counts())


print("\n" + "=" * 60)
print("학력 종류")
print("=" * 60)

print(df["학력"].value_counts())


print("\n" + "=" * 60)
print("마감일 종류")
print("=" * 60)

print(df["마감일"].value_counts())