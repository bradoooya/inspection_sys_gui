import logging
import os
from logging.handlers import RotatingFileHandler

class LoggerSetup:
    """
    プログラムのログ設定を行うクラスです。
    ログは log ディレクトリ内の app.log に出力されます。
    """
    @staticmethod
    def setup_logging(log_level=logging.DEBUG) -> None:
        # プロジェクトルートからの log ディレクトリのパスを作成
        log_dir = os.path.join(os.path.dirname(__file__), "..", "log")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")
        
        # ルートロガーを取得してレベル設定
        logger = logging.getLogger()
        logger.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 以前のハンドラを全て削除
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # ファイルハンドラ（ローテーション付き）
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # コンソールへも出力（必要に応じて）
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
