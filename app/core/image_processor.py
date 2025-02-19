import os 
import json 
import cv2
import logging
import numpy as np
from typing import Dict, List, Tuple
from app.core.settings import Settings  # Settingsモジュールから設定値を取得

class ImageProcessor:
    """
    画像処理を行うクラスです。
    入力画像から各種前処理を実施し、検査用のパラメータ（黒の割合、カラー領域の割合、トリガー状態など）を算出します。
    """

    def __init__(self, frame: np.ndarray, settings: "Settings") -> None:
        """
        初期化メソッド。

        Args:
            frame (np.ndarray): カメラから取得した画像（BGR形式）。
            settings (Settings): システム全体の設定オブジェクト。
        """
        self.frame = frame
        self.settings = settings
        self.combined_mask = None  # 複数のカラー範囲から統合したマスクを保持
        self.results: List[bool] = []  # 各検査領域の合否結果
        self.percentages: List[float] = []  # 各検査領域における対象色の割合

    def calculate_black_area_percentage(self) -> float:
        """
        画像全体における黒色領域の割合（％）を計算します。

        Returns:
            float: 黒の割合（％）。
        """
        try:
            # 画像をグレースケールに変換
            gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            # しきい値処理で、10以下のピクセルを黒とするバイナリマスクを作成
            _, black_mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY_INV)
            # 黒ピクセル数をカウントし、全体のピクセル数に対する割合を算出
            black_pixels = cv2.countNonZero(black_mask)
            total_pixels = self.frame.shape[0] * self.frame.shape[1]
            percentage = (black_pixels / total_pixels) * 100
            logging.debug(f"Black area percentage: {percentage:.2f}%")
            return percentage
        except Exception as e:
            logging.exception(f"Error calculating black area percentage: {e}")
            return 0.0

    def calculate_color_areas(self) -> Tuple[List[bool], List[float]]:
        """
        画像内で設定されたカラー範囲に基づいて、各検査領域ごとの対象色の割合を算出し、
        合否（Pass/Fail）を判断します。

        Returns:
            Tuple[List[bool], List[float]]: 検査結果（各領域がしきい値を超えているか）と各領域の割合（％）。
        """
        try:
            # 設定からカラー範囲を取得（例：HSVの場合の下限・上限のリスト）
            color_ranges = self.settings.settings.get("color_range", [])
            if not color_ranges:
                logging.warning("Color range is not set in settings.")
                return [], []

            # カラー空間変換：設定に応じてBGRからHSVまたはRGBに変換
            color_space = self.settings.settings.get("color_space", "HSV")
            if color_space == "HSV":
                converted = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
            elif color_space == "RGB":
                converted = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            else:
                converted = self.frame.copy()
                logging.warning(f"Unsupported color space: {color_space}. Using BGR by default.")

            # ガンマ補正：明るさの補正を行う（必要に応じて）
            gamma = self.settings.settings.get("gamma_value", 1.0)
            if gamma != 1.0:
                invGamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** invGamma) * 255 for i in range(256)]).astype("uint8")
                converted = cv2.LUT(converted, table)
                logging.debug(f"Applied gamma correction with gamma={gamma}")

            # ノイズ除去：Gaussian, Median, または Bilateral フィルタを適用
            noise_method = self.settings.settings.get("noise_reduction_method", "None")
            if noise_method == "Gaussian":
                converted = cv2.GaussianBlur(converted, (5, 5), 0)
            elif noise_method == "Median":
                converted = cv2.medianBlur(converted, 5)
            elif noise_method == "Bilateral":
                converted = cv2.bilateralFilter(converted, d=9, sigmaColor=75, sigmaSpace=75)

            # 各カラー範囲に対してマスクを生成し、全体マスクを作成
            masks = []
            for idx, color_range in enumerate(color_ranges):
                # color_range のフォーマットが正しいかチェック（例：[[下限3値], [上限3値]]）
                if (isinstance(color_range, list) and len(color_range) == 2 and
                    all(isinstance(part, list) and len(part) == 3 for part in color_range)):
                    lower, upper = color_range
                else:
                    logging.error(f"Invalid color_range format at index {idx}: {color_range}")
                    continue
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                mask = cv2.inRange(converted, lower_np, upper_np)
                masks.append(mask)

            # 複数のマスクをビット演算で統合
            if masks:
                combined_mask = masks[0]
                for mask in masks[1:]:
                    combined_mask = cv2.bitwise_or(combined_mask, mask)
            else:
                combined_mask = np.zeros(self.frame.shape[:2], dtype=np.uint8)

            # モルフォロジー演算（開演算）を適用して、ノイズを低減
            kernel_size = self.settings.settings.get("morph_kernel_size", 5)
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            self.combined_mask = combined_mask

            # 各クリップ領域（検査対象領域）ごとに、マスク内の対象色ピクセル割合を計算
            clip_positions = self.settings.settings.get("clip_positions", [])
            thresholds = self.settings.settings.get("thresholds", [60.0] * len(clip_positions))
            self.results = []
            self.percentages = []
            for idx, (pos, threshold) in enumerate(zip(clip_positions, thresholds)):
                x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
                x_end = min(x + w, combined_mask.shape[1])
                y_end = min(y + h, combined_mask.shape[0])
                roi = combined_mask[y:y_end, x:x_end]
                total_pixels = (x_end - x) * (y_end - y)
                if total_pixels == 0:
                    logging.warning(f"ROI {pos} has zero area. Skipping.")
                    self.results.append(False)
                    self.percentages.append(0.0)
                    continue
                roi_nonzero = cv2.countNonZero(roi)
                percentage = (roi_nonzero / total_pixels) * 100
                self.results.append(percentage >= threshold)
                self.percentages.append(percentage)
                logging.debug(f"ROI {idx} - Percentage: {percentage:.2f}% - {'Pass' if percentage >= threshold else 'Fail'}")
            return self.results, self.percentages

        except Exception as e:
            logging.exception(f"Error in calculate_color_areas: {e}")
            num_rois = len(self.settings.settings.get("clip_positions", []))
            return [False] * num_rois, [0.0] * num_rois

    def calculate_trigger_area_states(self) -> Tuple[List[bool], List[float]]:
        """
        トリガー領域における黒の割合を計算し、設定閾値以上ならTrueを返します。

        Returns:
            Tuple[List[bool], List[float]]: トリガー状態リストと黒の割合リスト。
        """
        try:
            trigger_positions = self.settings.settings.get("trigger_positions", [])
            states = []
            percentages = []
            gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            for pos in trigger_positions:
                x = max(pos["x"], 0)
                y = max(pos["y"], 0)
                w, h = pos["w"], pos["h"]
                x_end = min(x + w, width)
                y_end = min(y + h, height)
                if x_end <= x or y_end <= y:
                    states.append(False)
                    percentages.append(0.0)
                    continue
                roi = gray[y:y_end, x:x_end]
                total_pixels = roi.size
                _, mask = cv2.threshold(roi, 50, 255, cv2.THRESH_BINARY_INV)
                black_pixels = cv2.countNonZero(mask)
                percent = (black_pixels / total_pixels) * 100
                threshold = self.settings.settings.get("trigger_threshold", 70.0)
                states.append(percent >= threshold)
                percentages.append(percent)
                logging.debug(f"Trigger ROI {pos}: {percent:.2f}% - {'Triggered' if percent >= threshold else 'Not triggered'}")
            return states, percentages

        except Exception as e:
            logging.exception(f"Error in calculate_trigger_area_states: {e}")
            num_triggers = len(self.settings.settings.get("trigger_positions", []))
            return [False] * num_triggers, [0.0] * num_triggers

    def get_color_filtered_binary_image(self) -> np.ndarray:
        """
        作成した統合マスク（2値画像）を返します。

        Returns:
            np.ndarray: 統合マスクのコピー。
        """
        try:
            return self.combined_mask.copy()
        except Exception as e:
            logging.exception(f"Error getting binary image: {e}")
            return np.zeros((self.frame.shape[0], self.frame.shape[1]), dtype=np.uint8)

    def apply_hsv_filter(self) -> np.ndarray:
        """
        HSV 色空間に変換し、設定されたカラー範囲に基づいてフィルタを適用した画像を返します。

        Returns:
            np.ndarray: HSVフィルタ適用後の画像。
        """
        try:
            color_ranges = self.settings.settings.get("color_range", [])
            if not color_ranges:
                logging.warning("Color range not set.")
                return self.frame.copy()
            color_space = self.settings.settings.get("color_space", "HSV")
            if color_space != "HSV":
                logging.warning("HSV filter is applicable only in HSV color space.")
                return self.frame.copy()
            hsv_image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
            masks = []
            for color_range in color_ranges:
                if (isinstance(color_range, list) and len(color_range) == 2 and
                    all(isinstance(part, list) and len(part) == 3 for part in color_range)):
                    lower, upper = color_range
                else:
                    logging.error("Invalid color_range format.")
                    continue
                lower_np = np.array(lower, dtype=np.uint8)
                upper_np = np.array(upper, dtype=np.uint8)
                mask = cv2.inRange(hsv_image, lower_np, upper_np)
                masks.append(mask)
            if masks:
                combined = masks[0]
                for mask in masks[1:]:
                    combined = cv2.bitwise_or(combined, mask)
            else:
                combined = np.zeros(self.frame.shape[:2], dtype=np.uint8)
            filtered = cv2.bitwise_and(self.frame, self.frame, mask=combined)
            return filtered
        except Exception as e:
            logging.exception(f"Error applying HSV filter: {e}")
            return self.frame.copy()
