import cv2
import numpy as np
import logging
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QSlider
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from app.core.camera import capture_single_frame  # 変更: カメラモジュールをインポート

class CalibrationDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("カメラ校正")
        self.settings = settings
        # 直接カメラを保持せず、更新ごとに使うので削除
        # self.capture = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 約30fpsで更新

        self.image_label = QLabel(self)
        self.crosshair_color = (0, 255, 0)  # 緑色の十字
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(50)
        self.slider.valueChanged.connect(self.slider_changed)

        self.capture_button = QPushButton("画像を撮影")
        self.capture_button.clicked.connect(self.capture_image)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.capture_button)
        self.setLayout(layout)

    def update_frame(self):
        # camera.py の capture_single_frame() を使用して1枚取得（必ずカメラは解放されます）
        frame = capture_single_frame()
        if frame is None:
            logging.error("カメラからの画像取得に失敗しました。")
            return

        # 中央に十字を描画
        h, w, _ = frame.shape
        center = (w // 2, h // 2)
        cv2.line(frame, (center[0]-20, center[1]), (center[0]+20, center[1]), self.crosshair_color, 2)
        cv2.line(frame, (center[0], center[1]-20), (center[0], center[1]+20), self.crosshair_color, 2)

        # settings が設定されている場合のみ前回設定のバウンディングボックスを描画
        if self.settings and self.settings.settings.get("clip_positions"):
            pos = self.settings.settings["clip_positions"][0]
            x = pos.get("x", center[0]-50)
            y = pos.get("y", center[1]-50)
            w_box = pos.get("w", 100)
            h_box = pos.get("h", 100)
            cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), (255, 0, 0), 2)  # 青色の枠

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = image.shape
        bytesPerLine = channel * width
        q_img = QImage(image.data, width, height, bytesPerLine, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(q_img))

    def slider_changed(self, value):
        # 例: スライダー値により、何かの明るさ調整を行う場合
        logging.info(f"スライダー値: {value}")

    def capture_image(self):
        # capture_single_frame() を使用して画像を撮影
        frame = capture_single_frame()
        if frame is not None:
            logging.info("画像を撮影しました。設定更新処理を行います。")
            if self.settings is not None:
                self.settings.settings["clip_positions"] = [{"x": 100, "y": 100, "w": 200, "h": 200}]
                self.settings.save_settings()
            else:
                logging.error("設定が存在しないため更新できません。")
            self.accept()  # ダイアログを閉じる
        else:
            logging.error("キャプチャ画像の取得に失敗しました。")

    def closeEvent(self, event):
        self.timer.stop()
        # カメラは capture_single_frame() 内で確実に解放されるため不要
        event.accept()