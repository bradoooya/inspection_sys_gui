import os
import sys

# プロジェクトルートを sys.path に追加する（2階層上に設定）
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging
from typing import Optional, List, Tuple, Callable
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import Slot, Qt 
from PySide6.QtGui import QPainter

from app.ui.home_gui import HomePage
from app.ui.calibration_gui import CalibrationPage
from app.ui.inspection_gui import InspectionPage
from app.ui.preview_gui import PreviewPage
from app.ui.admin_gui import AdminPage
from app.core.settings import Settings
from app.core.core_controller import CoreController
from app.core.logger_setup import LoggerSetup
#from app.ui.bounding_boxes_gui import BoundingBoxTab
from app.ui.colorfilter_gui import ColorFilterTab
from app.ui.home_gui import HomeTab


class MainWindow(QMainWindow):
    """
    メインウィンドウクラス

    アプリケーション全体のウィンドウ管理とタブページの制御を行います。
    """
    WINDOW_TITLE = "検査システム"
    WINDOW_SIZE = (800, 600)

    def __init__(self) -> None:
        """
        コンストラクタ

        ウィンドウ初期化、コアコンポーネントの初期化、UIのセットアップおよび
        イベントハンドラの設定を行います。
        """
        super().__init__()
        self._init_window()
        self._init_core_components()
        self._setup_ui()
        self._setup_event_handlers()

    def _init_window(self) -> None:
        """
        ウィンドウの初期設定を行います。
        """
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(*self.WINDOW_SIZE)
        logging.info("ウィンドウの初期設定完了")

    def _init_core_components(self) -> None:
        """
        コアコンポーネントの初期化（Settings、CoreController など）を行います。
        """
        try:
            self.settings = Settings()
            self.core_controller = CoreController(self.settings)
            logging.info("コアコンポーネントの初期化完了")
        except Exception as e:
            logging.error(f"コアコンポーネントの初期化に失敗: {e}")
            raise

    def _setup_ui(self) -> None:
        """
        UIコンポーネントのセットアップを行い、タブウィジェットを中央ウィンドウに設定します。
        """
        try:
            self.tab_widget = QTabWidget()
            self._setup_tabs()
            self.setCentralWidget(self.tab_widget)
            logging.info("UIのセットアップ完了")
        except Exception as e:
            logging.error(f"UIのセットアップに失敗: {e}")
            raise

    def _setup_tabs(self) -> None:
        """
        タブの設定を行い、各タブページを QTabWidget に追加します。
        """
        for tab_name, tab_class in self._get_tab_configurations():
            # タブ生成関数の場合はインスタンス化する
            tab = tab_class() if callable(tab_class) else tab_class
            self.tab_widget.addTab(tab, tab_name)
        logging.info("タブのセットアップ完了")

    def _get_tab_configurations(self) -> List[Tuple[str, Callable]]:
        """
        タブのタイトルと生成関数のリストを返します。
        各タブには必要な依存オブジェクトのみを渡します。

        Returns:
            List[Tuple[str, Callable]]: (タブ名, タブ生成関数) のリスト
        """
        return [
            ("ホーム画面", HomePage),
            # ("カメラキャリブレーション", CalibrationPage),
            # ("バウンディングボックス設定", lambda: BoundingBoxTab(
            #     settings=self.settings
            # )),
            # ("カラーフィルター設定", lambda: ColorFilterTab(
            #     settings=self.settings
            # )),
            # ("検査", InspectionPage),
            # ("プレビュー", lambda: PreviewPage(self.core_controller)),
            # ("管理者", AdminPage),
        ]

    def _setup_event_handlers(self) -> None:
        """
        イベントハンドラの設定を行います。

        ※必要に応じて、追加のイベントハンドラを定義してください。
        """
        pass

    @Slot()
    def on_close(self) -> None:
        """
        ウィンドウを閉じる際の処理を行います。
        """
        logging.info("ウィンドウを閉じます")
        self.close()

    @Slot()
    def on_about(self) -> None:
        """
        「アプリケーションについて」の情報を表示する処理を行います。
        """
        logging.info("アプリケーションについての情報を表示します")
        # ここに処理を追加
        pass

    @Slot()
    def on_help(self) -> None:
        """
        ヘルプ情報を表示する処理を行います。
        """
        logging.info("ヘルプ情報を表示します")
        # ここに処理を追加
        pass

    @Slot()
    def on_settings(self) -> None:
        """
        設定画面を表示する処理を行います。
        """
        logging.info("設定画面を表示します")
        # ここに処理を追加
        pass

    @Slot()
    def on_exit(self) -> None:
        """
        アプリケーションを終了する処理を行います。
        """
        logging.info("アプリケーションを終了します")
        self.close()


def main() -> None:
    """
    アプリケーションのエントリーポイント

    ログ設定、アプリケーションの初期化、メインウィンドウの表示を行います。
    """
    try:
        LoggerSetup.setup_logging()
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"アプリケーション起動エラー: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
