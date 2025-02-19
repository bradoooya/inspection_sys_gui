from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QHBoxLayout,
    QSlider, QCheckBox, QLineEdit
)
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QImage, QPixmap
import cv2
import logging
from dataclasses import dataclass

from app.core.settings import Settings
from app.core.camera import Camera
from app.core.camera_manager import CameraManager


@dataclass
class CameraParams:
    """カメラパラメータを管理するデータクラス"""
    white_balance: int = 4500                      # ホワイトバランス温度
    white_balance_automatic: bool = True           # 自動ホワイトバランス
    brightness: int = 50
    contrast: int = 50
    saturation: int = 50
    resolution_scale: int = 100
    gain: int = 73                                 # ゲイン
    power_line_frequency: int = 2                  # 2:60Hz, 0: その他（ON/OFFとする）
    sharpness: int = 128
    backlight_compensation: bool = False           # 逆光補正
    auto_exposure: bool = True                     # 自動露出（ONなら手動露出は無効）
    exposure_time_absolute: int = 333              # 露出時間
    focus_absolute: int = 0                        # フォーカス値
    focus_automatic_continuous: bool = True        # 自動フォーカス


class CalibrationPage(QWidget):
    """
    キャリブレーション用の画面

    カメラパラメータの調整、プレビュー画像の更新、画像キャプチャなどの制御を行います。
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        コンストラクタ

        設定の初期化、UI ウィジェット生成、カメラ初期化と初回プレビュー撮影を行います。
        """
        super().__init__(parent)
        self.camera_params = CameraParams()
        self._init_settings()
        self.setup_ui()
        
        # シングルトンでカメラインスタンスを取得（コンストラクタで既にカメラの使用権を獲得）
        self.camera = Camera()
        if not self.camera.acquire():
            logging.error("カメラの使用権を取得できませんでした")
            QMessageBox.warning(self, "エラー", "カメラは他の処理で使用中です")
        
        # 初期化処理では既にオープン済みのカメラを流用する
        self.__init_camera()
        self.capture_before_preview()

    # --- 設定・初期化関連 ---
    def _init_settings(self) -> None:
        """アプリ設定の初期化を行います。"""
        try:
            self.settings = Settings()
        except Exception as e:
            logging.error(f"設定の初期化に失敗: {e}")
            raise

    def __init_camera(self) -> None:
        """
        カメラ初期化処理（既存のオープン済みカメラを利用）
        """
        if self.camera.cap is not None and self.camera.cap.isOpened():
            logging.info("既存のカメラリソースを利用します。")
        else:
            logging.warning("カメラリソースがオープンされていません。必要に応じて再オープンします。")
            # 必要なら再オープンも試みる（但し通常はこの分岐を通らない）
            if not self.camera._open_camera():
                logging.error("再オープンに失敗しました。")

    # --- UI セットアップ ---
    def setup_ui(self) -> None:
        """UI ウィジェット（プレビュー、カメラパラメータ入力欄、各種ボタン）の生成と配置を行います。"""
        layout = QVBoxLayout()

        # AUTO チェックボタン（最上部）
        auto_layout = QHBoxLayout()
        self.auto_checkbox = QCheckBox("AUTO")
        self.auto_checkbox.setChecked(False)
        self.auto_checkbox.toggled.connect(self.toggle_auto_controls)
        auto_layout.addWidget(self.auto_checkbox)
        layout.addLayout(auto_layout)

        # プレビューエリア（Before/After 両方）
        preview_layout = QHBoxLayout()
        preview_fixed_width = 400
        preview_fixed_height = 300
        self.preview_before = QLabel("Before Preview")
        self.preview_after =     QLabel("After Preview")
        self.preview_before.setFixedSize(
            preview_fixed_width, preview_fixed_height
        )
        self.preview_after.setFixedSize(
            preview_fixed_width, preview_fixed_height
        )
        self.preview_before.setAlignment(Qt.AlignCenter)
        self.preview_after.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_before)
        preview_layout.addWidget(self.preview_after)
        layout.addLayout(preview_layout)

        # カメラパラメータ操作用ウィジェット群
        sliders_layout = QVBoxLayout()
        self._setup_camera_controls(sliders_layout)
        layout.addLayout(sliders_layout)

        # 各種操作ボタン
        button_layout = QHBoxLayout()
        self.reflect_button = QPushButton("反映")
        self.reflect_button.clicked.connect(self.update_camera_parameters)
        button_layout.addWidget(self.reflect_button)

        self.default_button = QPushButton("デフォルト")
        self.default_button.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.default_button)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_camera_parameters)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def toggle_auto_controls(self, enabled: bool) -> None:
        """
        AUTO チェック状態に応じ、全カメラパラメータ入力欄の有効・無効を切り替え、
        無効時は背景色をグレーに変更
        """
        controls = [
            self.wb_slider, self.wb_value_edit,
            self.brightness_slider, self.brightness_value_edit,
            self.contrast_slider, self.contrast_value_edit,
            self.saturation_slider, self.saturation_value_edit,
            self.resolution_slider, self.resolution_value_edit,
            self.gain_slider, self.gain_value_edit,
            self.sharpness_slider, self.sharpness_value_edit,
            self.exposure_slider
        ]
        for ctrl in controls:
            ctrl.setDisabled(enabled)
            ctrl.setStyleSheet("background-color: lightgray;" if enabled else "")

    def capture_before_preview(self) -> None:
        """
        初回または反映後の撮影で、Before プレビュー画像を更新。
        撮影後は必ずカメラリソースを解放する。
        """
        frame = CameraManager.capture_single_frame()
        if frame is not None:
            image = self.convert_frame_to_qimage(frame)
            self.preview_before.setPixmap(QPixmap.fromImage(image))
        else:
            QMessageBox.warning(self, "エラー", "カメラから画像を取得できませんでした")

    def _setup_camera_controls(self, layout: QVBoxLayout) -> None:
        """
        カメラパラメータの入力欄（スライダーと数値入力フィールド）の生成と連動設定を行います。

        各パラメータのウィジェットは固定幅で統一しています。
        """
        slider_width = 200  # 全スライダーの固定幅

        # ホワイトバランス（自動制御と温度調整）
        wb_layout = QHBoxLayout()
        self.wb_auto_checkbox = QCheckBox("自動ホワイトバランス")
        self.wb_auto_checkbox.setChecked(self.camera_params.white_balance_automatic)
        self.wb_auto_checkbox.toggled.connect(lambda chk: self.wb_slider.setEnabled(not chk))
        wb_layout.addWidget(self.wb_auto_checkbox)
        wb_layout.addWidget(QLabel("温度"))
        self.wb_slider = QSlider(Qt.Horizontal)
        self.wb_slider.setMinimum(2000)
        self.wb_slider.setMaximum(6500)
        self.wb_slider.setValue(self.camera_params.white_balance)
        self.wb_slider.setFixedWidth(slider_width)
        self.wb_slider.setEnabled(not self.camera_params.white_balance_automatic)
        wb_layout.addWidget(self.wb_slider)
        self.wb_value_edit = QLineEdit(str(self.camera_params.white_balance))
        self.wb_value_edit.setFixedWidth(50)
        wb_layout.addWidget(self.wb_value_edit)
        self.wb_slider.valueChanged.connect(lambda val: self.wb_value_edit.setText(str(val)))
        self.wb_value_edit.returnPressed.connect(
            lambda: self.wb_slider.setValue(int(self.wb_value_edit.text()))
        )
        layout.addLayout(wb_layout)

        # 明るさ
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("明るさ"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(255)
        self.brightness_slider.setValue(self.camera_params.brightness)
        self.brightness_slider.setFixedWidth(slider_width)
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_value_edit = QLineEdit(str(self.camera_params.brightness))
        self.brightness_value_edit.setFixedWidth(50)
        brightness_layout.addWidget(self.brightness_value_edit)
        self.brightness_slider.valueChanged.connect(lambda val: self.brightness_value_edit.setText(str(val)))
        self.brightness_value_edit.returnPressed.connect(
            lambda: self.brightness_slider.setValue(int(self.brightness_value_edit.text()))
        )
        layout.addLayout(brightness_layout)

        # コントラスト
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("コントラスト"))
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(255)
        self.contrast_slider.setValue(self.camera_params.contrast)
        self.contrast_slider.setFixedWidth(slider_width)
        contrast_layout.addWidget(self.contrast_slider)
        self.contrast_value_edit = QLineEdit(str(self.camera_params.contrast))
        self.contrast_value_edit.setFixedWidth(50)
        contrast_layout.addWidget(self.contrast_value_edit)
        self.contrast_slider.valueChanged.connect(
            lambda val: self.contrast_value_edit.setText(str(val))
        )
        self.contrast_value_edit.returnPressed.connect(
            lambda: self.contrast_slider.setValue(int(self.contrast_value_edit.text()))
        )
        layout.addLayout(contrast_layout)

        # 彩度
        saturation_layout = QHBoxLayout()
        saturation_layout.addWidget(QLabel("彩度"))
        self.saturation_slider = QSlider(Qt.Horizontal)
        self.saturation_slider.setMinimum(0)
        self.saturation_slider.setMaximum(255)
        self.saturation_slider.setValue(self.camera_params.saturation)
        self.saturation_slider.setFixedWidth(slider_width)
        saturation_layout.addWidget(self.saturation_slider)
        self.saturation_value_edit = QLineEdit(str(self.camera_params.saturation))
        self.saturation_value_edit.setFixedWidth(50)
        saturation_layout.addWidget(self.saturation_value_edit)
        self.saturation_slider.valueChanged.connect(lambda val: self.saturation_value_edit.setText(str(val)))
        self.saturation_value_edit.returnPressed.connect(
            lambda: self.saturation_slider.setValue(int(self.saturation_value_edit.text()))
        )
        layout.addLayout(saturation_layout)

        # 解像度スケール
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("解像度スケール"))
        self.resolution_slider = QSlider(Qt.Horizontal)
        self.resolution_slider.setMinimum(50)
        self.resolution_slider.setMaximum(150)
        self.resolution_slider.setValue(self.camera_params.resolution_scale)
        self.resolution_slider.setFixedWidth(slider_width)
        resolution_layout.addWidget(self.resolution_slider)
        self.resolution_value_edit = QLineEdit(str(self.camera_params.resolution_scale))
        self.resolution_value_edit.setFixedWidth(50)
        resolution_layout.addWidget(self.resolution_value_edit)
        self.resolution_slider.valueChanged.connect(lambda val: self.resolution_value_edit.setText(str(val)))
        self.resolution_value_edit.returnPressed.connect(
            lambda: self.resolution_slider.setValue(int(self.resolution_value_edit.text()))
        )
        layout.addLayout(resolution_layout)

        # ゲイン
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("ゲイン"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setMinimum(0)
        self.gain_slider.setMaximum(255)
        self.gain_slider.setValue(self.camera_params.gain)
        self.gain_slider.setFixedWidth(slider_width)
        gain_layout.addWidget(self.gain_slider)
        self.gain_value_edit = QLineEdit(str(self.camera_params.gain))
        self.gain_value_edit.setFixedWidth(50)
        gain_layout.addWidget(self.gain_value_edit)
        self.gain_slider.valueChanged.connect(lambda val: self.gain_value_edit.setText(str(val)))
        self.gain_value_edit.returnPressed.connect(
            lambda: self.gain_slider.setValue(int(self.gain_value_edit.text()))
        )
        layout.addLayout(gain_layout)

        # 電源周波数補正（チェックボックスのみ）
        plf_layout = QHBoxLayout()
        self.plf_checkbox = QCheckBox("電源周波数補正(60Hz)")
        self.plf_checkbox.setChecked(self.camera_params.power_line_frequency == 2)
        plf_layout.addWidget(self.plf_checkbox)
        layout.addLayout(plf_layout)

        # シャープネス
        sharpness_layout = QHBoxLayout()
        sharpness_layout.addWidget(QLabel("シャープネス"))
        self.sharpness_slider = QSlider(Qt.Horizontal)
        self.sharpness_slider.setMinimum(0)
        self.sharpness_slider.setMaximum(255)
        self.sharpness_slider.setValue(self.camera_params.sharpness)
        self.sharpness_slider.setFixedWidth(slider_width)
        sharpness_layout.addWidget(self.sharpness_slider)
        self.sharpness_value_edit = QLineEdit(str(self.camera_params.sharpness))
        self.sharpness_value_edit.setFixedWidth(50)
        sharpness_layout.addWidget(self.sharpness_value_edit)
        self.sharpness_slider.valueChanged.connect(
            lambda val: self.sharpness_value_edit.setText(str(val))
        )
        self.sharpness_value_edit.returnPressed.connect(
            lambda: self.sharpness_slider.setValue(int(self.sharpness_value_edit.text()))
        )
        layout.addLayout(sharpness_layout)

        # 逆光補正（チェックボックスのみ）
        blc_layout = QHBoxLayout()
        self.blc_checkbox = QCheckBox("逆光補正")
        self.blc_checkbox.setChecked(self.camera_params.backlight_compensation)
        blc_layout.addWidget(self.blc_checkbox)
        layout.addLayout(blc_layout)

        # 自動露出と露出時間
        ae_layout = QHBoxLayout()
        self.ae_checkbox = QCheckBox("自動露出")
        self.ae_checkbox.setChecked(self.camera_params.auto_exposure)
        self.ae_checkbox.toggled.connect(lambda chk: self.exposure_slider.setEnabled(not chk))
        ae_layout.addWidget(self.ae_checkbox)
        ae_layout.addWidget(QLabel("露出時間"))
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.setMinimum(3)
        self.exposure_slider.setMaximum(2047)
        self.exposure_slider.setValue(self.camera_params.exposure_time_absolute)
        self.exposure_slider.setEnabled(not self.camera_params.auto_exposure)
        self.exposure_slider.setFixedWidth(slider_width)
        ae_layout.addWidget(self.exposure_slider)
        self.exposure_value_edit = QLineEdit(str(self.camera_params.exposure_time_absolute))
        self.exposure_value_edit.setFixedWidth(50)
        ae_layout.addWidget(self.exposure_value_edit)
        self.exposure_slider.valueChanged.connect(lambda val: self.exposure_value_edit.setText(str(val)))
        self.exposure_value_edit.returnPressed.connect(
            lambda: self.exposure_slider.setValue(int(self.exposure_value_edit.text()))
        )
        layout.addLayout(ae_layout)

        # 自動フォーカスとフォーカス値
        focus_layout = QHBoxLayout()
        self.focus_auto_checkbox = QCheckBox("自動フォーカス")
        self.focus_auto_checkbox.setChecked(self.camera_params.focus_automatic_continuous)
        self.focus_auto_checkbox.toggled.connect(lambda chk: self.focus_slider.setEnabled(not chk))
        focus_layout.addWidget(self.focus_auto_checkbox)
        focus_layout.addWidget(QLabel("フォーカス"))
        self.focus_slider = QSlider(Qt.Horizontal)
        self.focus_slider.setMinimum(0)
        self.focus_slider.setMaximum(250)
        self.focus_slider.setSingleStep(5)
        self.focus_slider.setValue(self.camera_params.focus_absolute)
        self.focus_slider.setEnabled(not self.camera_params.focus_automatic_continuous)
        self.focus_slider.setFixedWidth(slider_width)
        focus_layout.addWidget(self.focus_slider)
        self.focus_value_edit = QLineEdit(str(self.camera_params.focus_absolute))
        self.focus_value_edit.setFixedWidth(50)
        focus_layout.addWidget(self.focus_value_edit)
        self.focus_slider.valueChanged.connect(lambda val: self.focus_value_edit.setText(str(val)))
        self.focus_value_edit.returnPressed.connect(
            lambda: self.focus_slider.setValue(int(self.focus_value_edit.text()))
        )
        layout.addLayout(focus_layout)

    @Slot()
    def update_camera_parameters(self) -> None:
        if self.auto_checkbox.isChecked():
            logging.info("AUTO設定: カメラパラメータはWebカメラに任せています。")
        else:
            self._apply_camera_settings()
            
        # After プレビュー更新
        from app.core.camera import capture_single_frame
        frame = capture_single_frame()
        if frame is not None:
            image = self.convert_frame_to_qimage(frame)
            self.preview_after.setPixmap(QPixmap.fromImage(image))
        else:
            logging.error("After プレビュー更新用の画像キャプチャに失敗しました")

    @Slot()
    def reset_to_default(self) -> None:
        """各パラメータをデフォルト値にリセットする"""
        default_params = CameraParams()  # デフォルト値の再取得
        self.camera_params = default_params
        self.wb_auto_checkbox.setChecked(default_params.white_balance_automatic)
        self.wb_slider.setValue(default_params.white_balance)
        self.wb_value_edit.setText(str(default_params.white_balance))
        self.brightness_slider.setValue(default_params.brightness)
        self.brightness_value_edit.setText(str(default_params.brightness))
        self.contrast_slider.setValue(default_params.contrast)
        self.contrast_value_edit.setText(str(default_params.contrast))
        self.saturation_slider.setValue(default_params.saturation)
        self.saturation_value_edit.setText(str(default_params.saturation))
        self.resolution_slider.setValue(default_params.resolution_scale)
        self.resolution_value_edit.setText(str(default_params.resolution_scale))
        self.gain_slider.setValue(default_params.gain)
        self.gain_value_edit.setText(str(default_params.gain))
        logging.info("パラメータをデフォルト値にリセットしました")

    @Slot()
    def save_camera_parameters(self) -> None:
        """現在のパラメータをjsonへ保存し、ポップアップで上書きするjsonのファイル名を表示"""
        try:
            self.camera_params.white_balance = self.wb_slider.value()
            self.camera_params.white_balance_automatic = self.wb_auto_checkbox.isChecked()
            self.camera_params.brightness = self.brightness_slider.value()
            self.camera_params.contrast = self.contrast_slider.value()
            self.camera_params.saturation = self.saturation_slider.value()
            self.camera_params.resolution_scale = self.resolution_slider.value()
            self.camera_params.gain = self.gain_slider.value()
            # settings にパラメータを反映
            self.settings.settings["camera_params"] = self.camera_params.__dict__
            self.settings.save_settings()
            filename = getattr(self.settings, "settings_file", "settings.json")
            QMessageBox.information(self, "保存完了", f"設定が上書き保存されました: {filename}")
            logging.info(f"カメラパラメータを保存しました: {filename}")
        except Exception as e:
            logging.error(f"カメラパラメータの保存に失敗: {e}")
            QMessageBox.warning(self, "エラー", "カメラパラメータの保存に失敗しました")

    def _apply_camera_settings(self) -> None:
        """カメラパラメータの適用"""
        if not hasattr(self, "brightness_slider"):
            logging.warning("UI コントロールが未初期化のため、カメラ設定を適用できません")
            return
        # 各パラメータをカメラへ適用
        self.camera.set_white_balance(self.wb_slider.value())
        self.camera.set_brightness(self.brightness_slider.value())
        self.camera.set_contrast(self.contrast_slider.value())
        self.camera.set_saturation(self.saturation_slider.value())
        self.camera.set_resolution_scale(self.resolution_slider.value())
        self.camera.set_gain(self.gain_slider.value())
        self.camera.set_power_line_frequency(2 if self.plf_checkbox.isChecked() else 0)
        self.camera.set_sharpness(self.sharpness_slider.value())
        self.camera.set_backlight_compensation(self.blc_checkbox.isChecked())
        self.camera.set_exposure_auto(self.ae_checkbox.isChecked())
        if not self.ae_checkbox.isChecked():
            self.camera.set_exposure_absolute(self.exposure_slider.value())
        self.camera.set_focus_auto(self.focus_auto_checkbox.isChecked())
        if not self.focus_auto_checkbox.isChecked():
            self.camera.set_focus_absolute(self.focus_slider.value())
        logging.info("カメラパラメータを適用しました")

    def _save_camera_parameters(self) -> None:
        """カメラパラメータの保存"""
        self.camera_params = CameraParams(
            white_balance=self.wb_slider.value(),
            brightness=self.brightness_slider.value(),
            contrast=self.contrast_slider.value(),
            saturation=self.saturation_slider.value(),
            resolution_scale=self.resolution_slider.value()
        )
        self._save_camera_params()

    def _save_camera_params(self) -> None:
        """カメラパラメータの保存"""
        try:
            self.settings.save_settings(self.camera_params.__dict__)
        except Exception as e:
            logging.error(f"カメラパラメータの保存に失敗: {e}")
            QMessageBox.warning(self, "エラー", 
                              "カメラパラメータの保存に失敗しました")
    
    def _load_camera_params(self) -> CameraParams:
        """カメラパラメータの読み込み"""
        try:
            params = self.settings.load_settings()
            if (isinstance(params, dict)
                and "camera_settings" in params
                and isinstance(params["camera_settings"], dict)):
                return CameraParams(**params["camera_settings"])
            else:
                logging.warning("読み込んだ設定が無効なため、デフォルト値を使用します。")
                return CameraParams()
        except Exception as e:
            logging.error(f"カメラパラメータの読み込みに失敗: {e}")
            return CameraParams()
        
    def capture_image(self) -> None:
        """画像のキャプチャ"""
        # Camera.generate_frame() ではなく、capture_single_frame() を利用することで
        # 撮影直後にカメラが解放されるようにします。
        from app.core.camera import capture_single_frame
        frame = capture_single_frame()
        if frame is not None:
            import cv2
            cv2.imshow("Calibration Image", frame)
            logging.info("画像のキャプチャに成功")
        else:
            logging.error("画像のキャプチャに失敗しました")
            QMessageBox.warning(self, "エラー", "画像のキャプチャに失敗しました")
        
    def closeEvent(self, event) -> None:
        """ウィンドウが閉じられる際の処理"""
        if hasattr(self, 'camera'):
            self.camera.release()  # 使用権の解放
        event.accept()
        logging.info("キャリブレーション画面を閉じました")
    
    def keyPressEvent(self, event) -> None:
        """キーボード入力の処理"""
        if event.key() == Qt.Key_Escape:
            self.close()
        event.accept()
    
    def close(self) -> None:
        """ウィンドウを閉じる"""
        self.camera.release()
        self.parent().setCurrentIndex(0) # 親ウィジェットのタブを切り替える
        self.deleteLater() # メモリリークを防ぐためにインスタンスを削除
        logging.info("キャリブレーション画面を閉じました")
    
    def update_preview_label(self, label: QLabel, frame) -> None:
        """QLabelに OpenCV 画像を表示"""
        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def convert_frame_to_qimage(self, frame) -> QImage:
        """
        OpenCV の BGR フレームを QImage に変換する
        """
        height, width, channels = frame.shape
        bytes_per_line = channels * width
        return QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()


