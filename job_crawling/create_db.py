from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv("MYSQL_HOST")
port = os.getenv("MYSQL_PORT")
user = os.getenv("MYSQL_USER")
password = os.getenv("MYSQL_PASSWORD")

engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/"
)

with engine.begin() as connection:
    connection.execute(
        text("CREATE DATABASE IF NOT EXISTS jobinsight_db")
    )

print("jobinsight_db 생성 완료!")