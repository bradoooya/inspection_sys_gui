from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsView, QGraphicsScene
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtCore import Qt, QTimer
import cv2
import logging
from app.core.camera import Camera  # capture_single_frame ではなく Camera を使用

class PreviewPage(QWidget):
    """プレビュー画面を管理するクラス
    
    画像のライブビューとROI分析を行うGUIコンポーネントを提供します。
    
    Attributes:
        REFRESH_INTERVAL (int): プレビュー更新間隔(ミリ秒)
        core_controller (CoreController): 画像処理を制御するコントローラ
        image_view (QGraphicsView): 画像表示用ビュー
        scene (QGraphicsScene): 画像表示用シーン
    """
    
    REFRESH_INTERVAL = 1000  # 1秒

    def __init__(self, core_controller, parent=None):
        logging.debug("PreviewPage __init__ 開始")
        super().__init__(parent)
        self.core_controller = core_controller
        # カメラは初期化時に一度だけ走査する
        self.camera = Camera()
        logging.info("core_controller と camera を設定")
        self._setup_ui()
        self._setup_timer()
        logging.debug("PreviewPage __init__ 完了")

    def _setup_ui(self):
        """UIコンポーネントの初期設定を行う"""
        logging.debug("_setup_ui 開始")
        layout = QVBoxLayout()
        
        # ラベルの設定
        info_label = QLabel("プレビュー画面:\nライブ映像や処理済み画像の表示を行います。")
        info_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
        logging.info("info_label を作成")
        
        # 画像ビューの設定
        self.image_view = QGraphicsView()
        self.scene = QGraphicsScene(self)
        self.image_view.setScene(self.scene)
        self.image_view.setRenderHint(QPainter.SmoothPixmapTransform)
        logging.info("image_view と scene を作成、RenderHint を設定")
        
        layout.addWidget(info_label)
        logging.debug("info_label をレイアウトに追加")
        layout.addWidget(self.image_view)
        logging.debug("image_view をレイアウトに追加")
        self.setLayout(layout)
        logging.debug("_setup_ui 完了")

    def _setup_timer(self):
        """更新タイマーの設定を行う"""
        logging.debug("_setup_timer 開始")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_preview)
        self.timer.start(self.REFRESH_INTERVAL)
        logging.info("タイマーを開始(更新間隔: %s ミリ秒)", self.REFRESH_INTERVAL)
        logging.debug("_setup_timer 完了")

    def refresh_preview(self):
        """プレビュー画像の更新を行う"""
        logging.debug("refresh_preview 呼び出し開始")
        # 毎回新規走査せず、初期化済みのカメラインスタンスを利用
        frame = self.camera.capture_frame()
        if frame is None:
            logging.error("カメラからの画像取得に失敗しました")
            self._show_error_message("カメラからの画像取得に失敗しました。")
            return
        logging.debug("画像取得に成功")
        try:
            self._process_and_display_frame(frame)
            logging.debug("画像処理と表示に成功")
        except Exception as e:
            logging.error("画像処理中にエラーが発生: %s", str(e))
            self._show_error_message("画像処理中にエラーが発生しました。")
        logging.debug("refresh_preview 呼び出し完了")

    def _process_and_display_frame(self, frame):
        """フレームの処理と表示を行う
        
        Args:
            frame (np.ndarray): 処理対象のフレーム
        """
        logging.debug("_process_and_display_frame 開始")
        settings = self.core_controller.settings.settings
        logging.debug("settings を取得: %s", settings)
        
        # ROI処理
        if settings.get("clip_positions"):
            logging.info("ROI位置情報あり。ROI処理を実施")
            self._process_regions_of_interest(frame, settings["clip_positions"])
        else:
            logging.debug("ROI位置情報がないため、ROI処理はスキップ")
        
        # 画像の表示
        self._display_frame(frame)
        logging.debug("_process_and_display_frame 完了")

    def _process_regions_of_interest(self, frame, positions):
        """ROIの処理を行う
        
        Args:
            frame (np.ndarray): 処理対象のフレーム
            positions (list): ROIの位置情報リスト
        """
        logging.debug("_process_regions_of_interest 開始")
        for index, pos in enumerate(positions):
            x, y = pos.get("x", 100), pos.get("y", 100)
            w, h = pos.get("w", 100), pos.get("h", 100)
            logging.info("ROI[%s]: x=%s, y=%s, w=%s, h=%s", index, x, y, w, h)
            
            # ROI分析
            roi_region = frame[y:y+h, x:x+w]
            roi_ratio = self._analyze_roi(roi_region)
            logging.debug("ROI[%s] 分析結果: %.1f%%", index, roi_ratio)
            
            # 結果の描画
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            logging.debug("ROI[%s] に矩形を描画", index)
            cv2.putText(frame, f"{roi_ratio:.1f}%", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            logging.debug("ROI[%s] にテキストを描画", index)
        logging.debug("_process_regions_of_interest 完了")

    def _analyze_roi(self, roi):
        """ROIの色範囲分析を行う
        
        Args:
            roi (np.ndarray): 分析対象のROI
            
        Returns:
            float: 指定色範囲に該当する画素の割合
        """
        logging.debug("_analyze_roi 開始")
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        logging.debug("ROI を HSV に変換")
        color_ranges = self.core_controller.settings.settings.get(
            "color_range", [[[0, 0, 0], [179, 255, 255]]])
        logging.debug("color_ranges を取得: %s", color_ranges)
        
        mask = cv2.inRange(hsv_roi, 
                           tuple(color_ranges[0][0]),
                           tuple(color_ranges[0][1]))
        logging.debug("マスクを生成")
        non_zero = cv2.countNonZero(mask)
        total_pixels = roi.shape[0] * roi.shape[1]
        ratio = (non_zero / total_pixels * 100) if total_pixels else 0.0
        logging.info("ROI 分析結果: 非ゼロ画素数=%s, 総画素数=%s, 割合=%.1f%%", non_zero, total_pixels, ratio)
        logging.debug("_analyze_roi 完了")
        return ratio

    def _display_frame(self, frame):
        """フレームをGUIに表示する
        
        Args:
            frame (np.ndarray): 表示するフレーム
        """
        logging.debug("_display_frame 開始")
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            logging.debug("フレームを BGR から RGB に変換")
            height, width, channel = frame_rgb.shape
            q_img = QImage(frame_rgb.data, width, height, 
                           3 * width, QImage.Format_RGB888)
            logging.debug("QImage を生成: 幅=%s, 高さ=%s, チャンネル=%s", width, height, channel)
            
            self.scene.clear()
            logging.debug("シーンをクリア")
            self.scene.addPixmap(QPixmap.fromImage(q_img))
            logging.info("フレームをシーンに追加")
            self.image_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            logging.debug("image_view にシーンのサイズを適合")
        except Exception as e:
            logging.error("_display_frame 内でエラーが発生: %s", str(e))
        logging.debug("_display_frame 完了")

    def _show_error_message(self, message):
        """エラーメッセージを表示する
        
        Args:
            message (str): 表示するエラーメッセージ
        """
        logging.debug("_show_error_message 開始: メッセージ=%s", message)
        self.scene.clear()
        self.scene.addText(message)
        logging.info("エラーメッセージをシーンに表示")
        logging.debug("_show_error_message 完了")
