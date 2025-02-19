import json
import os
import logging
from typing import Any, Dict, List
from dataclasses import dataclass

@dataclass
class CameraSettings:
    white_balance: int = 4500
    white_balance_automatic: bool = True
    brightness: int = 50
    contrast: int = 50
    saturation: int = 50
    resolution_scale: int = 100
    gain: int = 73
    power_line_frequency: int = 2  # 2:60Hz, 0:その他
    sharpness: int = 128
    backlight_compensation: bool = False
    auto_exposure: bool = True
    exposure_time_absolute: int = 333
    focus_absolute: int = 0
    focus_automatic_continuous: bool = True

class Settings:
    """
    設定を管理するクラス。
    JSON形式の設定ファイル（app/data/settings.json）から設定を読み込み、保存、検証を行います。
    """

    def __init__(self, config_path: str = os.path.join("app", "data", "settings.json")) -> None:
        """
        初期化メソッド。

        Args:
            config_path (str): 設定ファイルのパス。デフォルトは "app/data/settings.json"。
        """
        self.config_path: str = config_path
        self.settings: Dict[str, Any] = {}
        self.default_settings: Dict[str, Any] = {
            "color_range": [[[160, 100, 100], [180, 255, 255]]],
            "clip_positions": [],
            "thresholds": [],
            "color_space": "HSV",
            "gamma_value": 1.2,
            "morph_kernel_size": 5,
            "noise_reduction_method": "Gaussian",
            "frame_width": 1280,
            "frame_height": 720,
            "rotation": 90,
            "result_output_duration": 1.0,
            "trigger_threshold": 70.0,
        }
        self.camera_settings = CameraSettings()
        settings_dir = os.path.dirname(self.config_path)
        if settings_dir and not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
            logging.info(f"設定ディレクトリ {settings_dir} を作成しました。")
        self.load_settings()

    def load_settings(self) -> None:
        """
        設定ファイルを読み込みます。ファイルが存在しない、または空の場合は、デフォルト設定を用いて保存します。
        """
        if os.path.exists(self.config_path) and os.path.getsize(self.config_path) > 0:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
                logging.info(f"設定ファイルを読み込みました: {self.config_path}")
                logging.debug(f"Loaded settings: {self.settings}")
                cam_set = self.settings.get("camera_settings", {})
                for field in self.camera_settings.__dataclass_fields__:
                    setattr(
                        self.camera_settings,
                        field,
                        cam_set.get(field, getattr(self.camera_settings, field))
                    )
            except Exception as e:
                logging.error(f"設定ファイルの読み込みに失敗しました: {e}")
                self.settings = self.default_settings.copy()
        else:
            logging.warning("設定ファイルが存在しないか空です。デフォルト設定を使用します。")
            self.settings = self.default_settings.copy()
            self.save_settings()
        self.validate_settings()

    def save_settings(self) -> None:
        """
        現在の設定を設定ファイルに保存します。
        """
        try:
            self.settings["camera_settings"] = self.camera_settings.__dict__
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logging.info(f"設定ファイルを保存しました: {self.config_path}")
        except Exception as e:
            logging.error(f"設定ファイルの保存に失敗しました: {e}")

    def validate_settings(self) -> None:
        """
        読み込んだ設定に必須項目が含まれているか検証し、欠落している項目にはデフォルト値を補完します。
        """
        required_keys: List[str] = [
            "color_range",
            "clip_positions",
            "thresholds",
            "color_space",
            "gamma_value",
            "morph_kernel_size",
            "noise_reduction_method",
            "frame_width",
            "frame_height",
            "rotation",
        ]
        for key in required_keys:
            if key not in self.settings:
                logging.warning(f"設定に'{key}'が存在しません。デフォルト値を設定します。")
                self.settings[key] = self.default_settings[key]

        # clip_positions と thresholds の長さが一致しているか確認
        if "clip_positions" in self.settings and "thresholds" in self.settings:
            if len(self.settings["clip_positions"]) != len(self.settings["thresholds"]):
                logging.warning("clip_positions と thresholds の長さが一致していません。thresholds を clip_positions の長さに合わせます。")
                default_threshold: float = self.default_settings["thresholds"][0] if self.default_settings["thresholds"] else 50.0
                self.settings["thresholds"] = [default_threshold] * len(self.settings["clip_positions"])
                self.save_settings()
