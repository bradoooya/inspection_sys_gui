import os
import sys

#　プロジェクトルートディレクトリをパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
import logging
from typing import Optional, List, Tuple, Callable
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget


class MainWindow(QMainWindow):
    """
    メインウィンドウクラス

    アプリケーション全体のウィンドウ管理とタブページの制御を行います。
    """
    WINDOW_TITLE = "検査システム"
    WINDOW_SIZE = (800, 600)
    
    def __init__(self) -> None:
        ""