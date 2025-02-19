# app/infrastructure/crud.py
import logging
from sqlalchemy.orm import Session
from .database import InspectionResult

def create_inspection_result(db: Session, result: str, details: str = "") -> InspectionResult:
    """
    検査結果を作成してデータベースに保存します。

    Args:
        db (Session): SQLAlchemy セッションオブジェクト。
        result (str): "PASS" または "FAIL"。
        details (str): 検査結果の詳細情報。

    Returns:
        InspectionResult: 作成された検査結果オブジェクト。
    """
    db_result = InspectionResult(result=result, details=details)
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    logging.info("検査結果がデータベースに保存されました。")
    return db_result

def get_all_inspection_results(db: Session):
    """
    全ての検査結果を取得します。

    Args:
        db (Session): SQLAlchemy セッションオブジェクト。

    Returns:
        List[InspectionResult]: 検査結果のリスト。
    """
    return db.query(InspectionResult).order_by(InspectionResult.timestamp.desc()).all()

# 使用例（モジュール単体テスト）
if __name__ == "__main__":
    from .database import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    create_inspection_result(db, "PASS", "全領域正常")
    results = get_all_inspection_results(db)
    for r in results:
        print(r.id, r.timestamp, r.result, r.details)
    db.close()
