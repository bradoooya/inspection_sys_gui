import sys
import os
import json
import cv2
import numpy as np
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                               QPushButton, QGraphicsScene, QGraphicsView,
                               QMessageBox, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from app.ui.common_widgets import RangeSlider  # 先述の共通ウィジェット

class ColorFilterTab(QWidget):
    def __init__(self, cap, settings, parent=None):
        super().__init__(parent)
        self.cap = cap
        self.settings = settings
        self.settings_file = settings.settings_file
        self.init_hsv_ranges()
        self.init_ui()

    def init_hsv_ranges(self):
        try:
            color_range = self.settings.settings.get("color_range")
            if isinstance(color_range, list) and len(color_range) >= 1:
                first_range = color_range[0]
                if (isinstance(first_range, list) and len(first_range) == 2 and 
                    all(isinstance(part, list) and len(part) == 3 for part in first_range)):
                    self.hsv_lower = np.array(first_range[0], dtype=np.uint8)
                    self.hsv_upper = np.array(first_range[1], dtype=np.uint8)
                else:
                    raise ValueError("color_rangeの形式が不正です。")
            else:
                raise ValueError("color_rangeの形式が不正です。")
        except Exception as e:
            logging.error(f"HSV範囲初期化エラー: {e}")
            self.hsv_lower = np.array([0, 0, 0], dtype=np.uint8)
            self.hsv_upper = np.array([179, 255, 255], dtype=np.uint8)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.view)
        self.pixmap_item = self.scene.addPixmap(QPixmap())
        self.setup_hsv_sliders()
        self.cf_save_button = QPushButton("HSV設定を保存")
        self.cf_save_button.clicked.connect(self.save_hsv_settings)
        main_layout.addWidget(self.cf_save_button)
        # 初回更新
        self.update_color_filter()

    def setup_hsv_sliders(self):
        self.slider_layout = QGridLayout()
        # Hスライダー
        self.h_range_slider = RangeSlider(min_value=0, max_value=179)
        self.h_range_slider.left_value = int(self.hsv_lower[0])
        self.h_range_slider.right_value = int(self.hsv_upper[0])
        self.h_range_slider.valueChanged.connect(self.update_color_filter)
        self.slider_layout.addWidget(QLabel("H 範囲"), 0, 0)
        self.slider_layout.addWidget(self.h_range_slider, 0, 1)
        self.h_value_label = QLabel(f"{self.hsv_lower[0]} - {self.hsv_upper[0]}")
        self.slider_layout.addWidget(self.h_value_label, 0, 2)
        # Sスライダー
        self.s_range_slider = RangeSlider(min_value=0, max_value=255)
        self.s_range_slider.left_value = int(self.hsv_lower[1])
        self.s_range_slider.right_value = int(self.hsv_upper[1])
        self.s_range_slider.valueChanged.connect(self.update_color_filter)
        self.slider_layout.addWidget(QLabel("S 範囲"), 1, 0)
        self.slider_layout.addWidget(self.s_range_slider, 1, 1)
        self.s_value_label = QLabel(f"{self.hsv_lower[1]} - {self.hsv_upper[1]}")
        self.slider_layout.addWidget(self.s_value_label, 1, 2)
        # Vスライダー
        self.v_range_slider = RangeSlider(min_value=0, max_value=255)
        self.v_range_slider.left_value = int(self.hsv_lower[2])
        self.v_range_slider.right_value = int(self.hsv_upper[2])
        self.v_range_slider.valueChanged.connect(self.update_color_filter)
        self.slider_layout.addWidget(QLabel("V 範囲"), 2, 0)
        self.slider_layout.addWidget(self.v_range_slider, 2, 1)
        self.v_value_label = QLabel(f"{self.hsv_lower[2]} - {self.hsv_upper[2]}")
        self.slider_layout.addWidget(self.v_value_label, 2, 2)
        self.layout().addLayout(self.slider_layout)

    def update_color_filter(self):
        h_lower = self.h_range_slider.left_value
        h_upper = self.h_range_slider.right_value
        s_lower = self.s_range_slider.left_value
        s_upper = self.s_range_slider.right_value
        v_lower = self.v_range_slider.left_value
        v_upper = self.v_range_slider.right_value

        self.hsv_lower = np.array([h_lower, s_lower, v_lower], dtype=np.uint8)
        self.hsv_upper = np.array([h_upper, s_upper, v_upper], dtype=np.uint8)

        self.h_value_label.setText(f"{h_lower} - {h_upper}")
        self.s_value_label.setText(f"{s_lower} - {s_upper}")
        self.v_value_label.setText(f"{v_lower} - {v_upper}")

        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.critical(self, "エラー", "カメラからフレームを取得できませんでした。")
            return
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_frame, self.hsv_lower, self.hsv_upper)
        result_frame = cv2.bitwise_and(frame, frame, mask=mask)
        result_rgb = cv2.cvtColor(result_frame, cv2.COLOR_BGR2RGB)
        height, width, _ = result_rgb.shape
        bytes_per_line = 3 * width
        from PySide6.QtGui import QImage  # 遅延インポート
        q_image = QImage(result_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(0, 0, width, height)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def save_hsv_settings(self):
        hsv_lower_list = self.hsv_lower.tolist()
        hsv_upper_list = self.hsv_upper.tolist()
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                settings = {}
        else:
            settings = {}
        settings["color_range"] = [[hsv_lower_list, hsv_upper_list]]
        try:
            if os.path.exists(self.settings_file):
                os.rename(self.settings_file, self.settings_file + ".bak")
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "成功", f"HSV設定が保存されました: {self.settings_file}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")
