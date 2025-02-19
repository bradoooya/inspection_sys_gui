import cv2
import logging
import numpy as np
from app.core.image_processor import ImageProcessor
from app.core.settings import Settings
from app.core.camera import Camera

class CoreController:
    """
    UI から呼び出される core モジュールの窓口クラスです。
    例として、画像処理を実行し、その結果を返します。
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # Camera インスタンスの初期化を追加
        self.camera = Camera()
        if not self.camera.find_and_open():
            logging.error("CoreController: カメラの初期化に失敗しました")

    def process_image(self, image_path: str) -> dict:
        frame = cv2.imread(image_path)
        if frame is None:
            logging.error(f"画像が読み込めません: {image_path}")
            return {}
        return self._process_image_frame(frame)

    def process_image_from_frame(self, frame: np.ndarray) -> dict:
        return self._process_image_frame(frame)

    def _process_image_frame(self, frame: np.ndarray) -> dict:
        processor = ImageProcessor(frame, self.settings)
        black_area = processor.calculate_black_area_percentage()
        try:
            color_results, color_percentages = processor.calculate_color_areas()
        except Exception as e:
            logging.exception("カラー領域の計算でエラーが発生しました。")
            color_results, color_percentages = [], []
        return {
            "black_area_percentage": black_area,
            "color_results": color_results,
            "color_percentages": color_percentages,
        }
