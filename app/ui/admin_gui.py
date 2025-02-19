import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QMessageBox
from PySide6.QtCore import Slot

class AdminPage(QWidget):
    def __init__(self, parent=None):
        logging.debug("AdminPage __init__ 開始")
        super().__init__(parent)
        self.initUI()
        logging.debug("AdminPage __init__ 完了")

    def initUI(self):
        logging.debug("initUI 開始")
        layout = QVBoxLayout()

        label = QLabel("管理者用画面:\n詳細設定、ログ確認、ユーザーロール管理を行います。")
        logging.info("ラベルを作成: 管理者用画面")
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        logging.info("log_viewer 作成: 読み取り専用")
        
        self.refresh_logs_button = QPushButton("ログ更新")
        self.refresh_logs_button.clicked.connect(self.refresh_logs)
        logging.info("refresh_logs_button 作成、クリックシグナルを接続")
        
        self.setting_input = QLineEdit()
        self.setting_input.setPlaceholderText("新しい設定値を入力")
        logging.info("setting_input 作成: プレースホルダーテキストを設定")
        
        self.update_setting_button = QPushButton("設定更新")
        self.update_setting_button.clicked.connect(self.update_setting)
        logging.info("update_setting_button 作成、クリックシグナルを接続")
        
        layout.addWidget(label)
        logging.debug("ラベルをレイアウトに追加")
        layout.addWidget(self.log_viewer)
        logging.debug("log_viewer をレイアウトに追加")
        layout.addWidget(self.refresh_logs_button)
        logging.debug("refresh_logs_button をレイアウトに追加")
        layout.addWidget(self.setting_input)
        logging.debug("setting_input をレイアウトに追加")
        layout.addWidget(self.update_setting_button)
        logging.debug("update_setting_button をレイアウトに追加")
        
        self.setLayout(layout)
        logging.info("initUI 完了: UI レイアウトが設定されました")
    
    @Slot()
    def refresh_logs(self):
        logging.debug("refresh_logs 開始")
        try:
            with open("log/app.log", "r", encoding="utf-8") as f:
                logs = f.read()
            logging.info("ログファイルの読み込みに成功")
            self.log_viewer.setPlainText(logs)
            logging.debug("log_viewer にログ内容をセット")
        except Exception as e:
            logging.error("ログの読み込みに失敗: %s", str(e))
            QMessageBox.warning(self, "エラー", f"ログの読み込みに失敗しました: {e}")
        logging.debug("refresh_logs 完了")

    @Slot()
    def update_setting(self):
        logging.debug("update_setting 開始")
        new_setting = self.setting_input.text()
        logging.info("新しい設定値を取得: %s", new_setting)
        # ここに実際の設定更新処理を追加することができます
        QMessageBox.information(self, "設定更新", f"新しい設定: {new_setting}\n(実際の更新処理は未実装)")
        logging.debug("update_setting 完了")
