# app/infrastructure/database.py
import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# データベースのパス（SQLite を使用する例）
DATABASE_URL = f"sqlite:///{os.path.join('app', 'data', 'inspection.db')}"

# エンジンの作成
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# セッションファクトリの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Baseクラス（全てのモデルの継承元）
Base = declarative_base()

# 検査結果を保存するテーブルのモデル定義
class InspectionResult(Base):
    __tablename__ = "inspection_results"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    result = Column(String(10), nullable=False)  # "PASS" または "FAIL"
    details = Column(Text, nullable=True)

# テーブル作成
def init_db():
    Base.metadata.create_all(bind=engine)
    logging.info("データベースのテーブル作成完了")

if __name__ == "__main__":
    init_db()
