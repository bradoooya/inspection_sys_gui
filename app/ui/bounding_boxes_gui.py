import sys
import os
import json
import cv2
import numpy as np
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGraphicsScene,
                               QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                               QMessageBox, QSizePolicy)
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap, QImage, QColor
# 共通ウィジェットをインポート（RangeSlider 以外にも GraphicsView や ResizableGraphicsRectItem を使用）
from app.ui.common_widgets import GraphicsView, ResizableGraphicsRectItem
from app.core.camera import Camera
from app.core.settings import Settings

class BoundingBoxTab(QWidget):
    def __init__(self, cap, settings, parent=None):
        super().__init__(parent)
        self.cap = cap
        self.settings = settings
        self.settings_file = settings.settings_file
        self.scale_factor = 1.0  # 必要に応じて調整
        self.bounding_boxes = []
        self.trigger_boxes = []
        self.clip_positions = self.load_clip_positions()
        self.trigger_positions = self.load_trigger_positions()
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # 左側レイアウト：グラフィックスシーン・ビューと操作ボタン
        left_layout = QVBoxLayout()
        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.view)

        # カメラ画像表示用ピクスマップ（シーンに追加）
        self.pixmap_item = self.scene.addPixmap(QPixmap())

        # 初期バウンディングボックス作成
        self.create_initial_bounding_boxes()
        self.create_initial_trigger_boxes()

        # 操作ボタン
        controls_layout = QHBoxLayout()
        self.capture_button = QPushButton("再撮影")
        self.capture_button.clicked.connect(self.capture_image)
        controls_layout.addWidget(self.capture_button)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        controls_layout.addWidget(self.save_button)
        self.add_button = QPushButton("バウンディングボックス追加")
        self.add_button.clicked.connect(self.add_bounding_box)
        controls_layout.addWidget(self.add_button)
        self.delete_button = QPushButton("選択したボックス削除")
        self.delete_button.clicked.connect(self.delete_selected_bounding_box)
        controls_layout.addWidget(self.delete_button)
        self.add_trigger_button = QPushButton("トリガーボックス追加")
        self.add_trigger_button.clicked.connect(self.add_trigger_bounding_box)
        controls_layout.addWidget(self.add_trigger_button)
        self.reset_zoom_button = QPushButton("ズームリセット")
        self.reset_zoom_button.clicked.connect(self.view.reset_zoom)
        controls_layout.addWidget(self.reset_zoom_button)
        left_layout.addLayout(controls_layout)

        # 選択中のボックス情報表示ラベル
        self.info_label = QLabel("選択されたボックスの情報: なし")
        left_layout.addWidget(self.info_label)
        main_layout.addLayout(left_layout, 4)

        # 右側レイアウト：バウンディングボックス情報をテーブルで表示
        right_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Width", "Height"])
        self.table.cellChanged.connect(self.table_cell_changed)
        right_layout.addWidget(QLabel("バウンディングボックス情報:"))
        right_layout.addWidget(self.table)
        self.trigger_table = QTableWidget()
        self.trigger_table.setColumnCount(4)
        self.trigger_table.setHorizontalHeaderLabels(["X", "Y", "Width", "Height"])
        self.trigger_table.cellChanged.connect(self.trigger_table_cell_changed)
        right_layout.addWidget(QLabel("トリガーバウンディングボックス情報:"))
        right_layout.addWidget(self.trigger_table)
        main_layout.addLayout(right_layout, 1)

        # 初回キャプチャ
        self.capture_image()

    def load_clip_positions(self):
        clip_positions = self.settings.settings.get("clip_positions")
        if isinstance(clip_positions, list):
            return clip_positions
        else:
            return self.default_positions()

    def load_trigger_positions(self):
        trigger_positions = self.settings.settings.get("trigger_positions")
        if isinstance(trigger_positions, list):
            return trigger_positions
        else:
            return self.default_trigger_positions()

    def default_positions(self):
        return [{"x": 100, "y": 100, "w": 150, "h": 150},
                {"x": 300, "y": 100, "w": 150, "h": 150}]

    def default_trigger_positions(self):
        return [{"x": 500, "y": 100, "w": 75, "h": 75},
                {"x": 600, "y": 100, "w": 75, "h": 75},
                {"x": 700, "y": 100, "w": 75, "h": 75}]

    def create_initial_bounding_boxes(self):
        for pos in self.clip_positions:
            rect = QRectF(pos["x"], pos["y"], pos["w"], pos["h"])
            box = ResizableGraphicsRectItem(rect)
            self.scene.addItem(box)
            self.bounding_boxes.append(box)
            box.positionChanged.connect(self.update_table_from_box)
            box.sizeChanged.connect(self.update_table_from_box)

    def create_initial_trigger_boxes(self):
        for pos in self.trigger_positions:
            rect = QRectF(pos["x"], pos["y"], pos["w"], pos["h"])
            # 色は黄色で表示
            box = ResizableGraphicsRectItem(rect, color=QColor(255, 255, 0))
            self.scene.addItem(box)
            self.trigger_boxes.append(box)
            box.positionChanged.connect(self.update_trigger_table)
            box.sizeChanged.connect(self.update_trigger_table)

    def capture_image(self):
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.critical(self, "エラー", "カメラからフレームを取得できませんでした。")
            return
        # BGR→RGB変換
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = frame_rgb.shape
        bytes_per_line = 3 * width
        from PySide6.QtGui import QImage  # 遅延インポート
        q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(0, 0, width, height)
        self.view.reset_zoom()

    def save_settings(self):
        clip_positions = []
        for box in self.bounding_boxes:
            rect = box.rect
            pos = box.pos()
            clip_positions.append({
                "x": int(pos.x() + rect.x()),
                "y": int(pos.y() + rect.y()),
                "w": int(rect.width()),
                "h": int(rect.height())
            })
        trigger_positions = []
        for box in self.trigger_boxes:
            rect = box.rect
            pos = box.pos()
            trigger_positions.append({
                "x": int(pos.x() + rect.x()),
                "y": int(pos.y() + rect.y()),
                "w": int(rect.width()),
                "h": int(rect.height())
            })
        # 既存の設定を読み込む
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                settings = {}
        else:
            settings = {}
        settings["clip_positions"] = clip_positions
        settings["trigger_positions"] = trigger_positions
        try:
            if os.path.exists(self.settings_file):
                os.rename(self.settings_file, self.settings_file + ".bak")
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "成功", f"設定が保存されました: {self.settings_file}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")

    def delete_selected_bounding_box(self):
        selected_items = self.scene.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "削除するバウンディングボックスを選択してください。")
            return
        for item in selected_items:
            if item in self.bounding_boxes:
                self.scene.removeItem(item)
                self.bounding_boxes.remove(item)
            elif item in self.trigger_boxes:
                self.scene.removeItem(item)
                self.trigger_boxes.remove(item)
        self.update_table_from_box()
        self.update_trigger_table()

    def add_bounding_box(self):
        scene_rect = self.scene.sceneRect()
        new_rect = QRectF(scene_rect.center().x() - 75, scene_rect.center().y() - 75, 150, 150)
        box = ResizableGraphicsRectItem(new_rect)
        self.scene.addItem(box)
        self.bounding_boxes.append(box)
        box.positionChanged.connect(self.update_table_from_box)
        box.sizeChanged.connect(self.update_table_from_box)
        self.update_table_from_box()

    def add_trigger_bounding_box(self):
        scene_rect = self.scene.sceneRect()
        new_rect = QRectF(scene_rect.center().x() - 37.5, scene_rect.center().y() - 37.5, 75, 75)
        box = ResizableGraphicsRectItem(new_rect, color=QColor(255, 255, 0))
        self.scene.addItem(box)
        self.trigger_boxes.append(box)
        box.positionChanged.connect(self.update_trigger_table)
        box.sizeChanged.connect(self.update_trigger_table)
        self.update_trigger_table()

    def table_cell_changed(self, row, column):
        if row >= len(self.bounding_boxes):
            return
        item = self.table.item(row, column)
        if item is None:
            return
        try:
            value = float(item.text())
        except ValueError:
            QMessageBox.warning(self, "入力エラー", "数値を入力してください。")
            return
        box = self.bounding_boxes[row]
        rect = box.rect
        if column == 0:
            box.setPos(value, box.pos().y())
        elif column == 1:
            box.setPos(box.pos().x(), value)
        elif column == 2:
            rect.setWidth(value)
            box.rect = rect
            box.update_handles()
            box.update()
        elif column == 3:
            rect.setHeight(value)
            box.rect = rect
            box.update_handles()
            box.update()

    def trigger_table_cell_changed(self, row, column):
        if row >= len(self.trigger_boxes):
            return
        item = self.trigger_table.item(row, column)
        if item is None:
            return
        try:
            value = float(item.text())
        except ValueError:
            QMessageBox.warning(self, "入力エラー", "数値を入力してください。")
            return
        box = self.trigger_boxes[row]
        rect = box.rect
        if column == 0:
            box.setPos(value, box.pos().y())
        elif column == 1:
            box.setPos(box.pos().x(), value)
        elif column == 2:
            rect.setWidth(value)
            box.rect = rect
            box.update_handles()
            box.update()
        elif column == 3:
            rect.setHeight(value)
            box.rect = rect
            box.update_handles()
            box.update()

    def update_table_from_box(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.bounding_boxes))
        for row, box in enumerate(self.bounding_boxes):
            rect = box.rect
            pos = box.pos()
            absolute_x = pos.x() + rect.x()
            absolute_y = pos.y() + rect.y()
            self.table.setItem(row, 0, QTableWidgetItem(str(int(absolute_x))))
            self.table.setItem(row, 1, QTableWidgetItem(str(int(absolute_y))))
            self.table.setItem(row, 2, QTableWidgetItem(str(int(rect.width()))))
            self.table.setItem(row, 3, QTableWidgetItem(str(int(rect.height()))))
        self.table.blockSignals(False)

    def update_trigger_table(self):
        self.trigger_table.blockSignals(True)
        self.trigger_table.setRowCount(len(self.trigger_boxes))
        for row, box in enumerate(self.trigger_boxes):
            rect = box.rect
            pos = box.pos()
            absolute_x = pos.x() + rect.x()
            absolute_y = pos.y() + rect.y()
            self.trigger_table.setItem(row, 0, QTableWidgetItem(str(int(absolute_x))))
            self.trigger_table.setItem(row, 1, QTableWidgetItem(str(int(absolute_y))))
            self.trigger_table.setItem(row, 2, QTableWidgetItem(str(int(rect.width()))))
            self.trigger_table.setItem(row, 3, QTableWidgetItem(str(int(rect.height()))))
        self.trigger_table.blockSignals(False)

# 例: カメラインスタンス（Camera）の初期化後
camera = Camera()
settings = Settings()
# カメラの使用権取得やキャプチャ開始後に：
bounding_box_tab = BoundingBoxTab(camera.cap, settings)
