# tests/test_image_processor.py
import cv2
import numpy as np
import pytest
from app.core.settings import Settings
from app.core.image_processor import ImageProcessor

@pytest.fixture
def dummy_settings(tmp_path):
    # 一時設定ファイルを用意し、必要なデフォルト設定を利用
    settings_path = tmp_path / "settings.json"
    default_settings = {
        "color_range": [[[0, 0, 0], [255, 255, 255]]],  # 全範囲を対象
        "clip_positions": [{"x": 0, "y": 0, "w": 100, "h": 100}],
        "thresholds": [50.0],
        "color_space": "HSV",
        "gamma_value": 1.0,
        "morph_kernel_size": 3,
        "noise_reduction_method": "None",
        "frame_width": 100,
        "frame_height": 100,
        "rotation": 0,
        "trigger_threshold": 50.0,
        "trigger_positions": [{"x": 0, "y": 0, "w": 50, "h": 50}]
    }
    with open(str(settings_path), "w", encoding="utf-8") as f:
        import json
        json.dump(default_settings, f)
    settings_obj = Settings(config_path=str(settings_path))
    return settings_obj

@pytest.fixture
def dummy_black_image():
    # 黒画像（100x100）を作成
    return np.zeros((100, 100, 3), dtype=np.uint8)

@pytest.fixture
def dummy_white_image():
    # 白画像（100x100）を作成
    return np.ones((100, 100, 3), dtype=np.uint8) * 255

def test_calculate_black_area_percentage(dummy_black_image, dummy_settings):
    processor = ImageProcessor(dummy_black_image, dummy_settings)
    percentage = processor.calculate_black_area_percentage()
    # 黒画像なので黒の割合は100%になるはず
    assert percentage == pytest.approx(100.0, abs=0.1)

def test_calculate_black_area_percentage_white(dummy_white_image, dummy_settings):
    processor = ImageProcessor(dummy_white_image, dummy_settings)
    percentage = processor.calculate_black_area_percentage()
    # 白画像なので黒の割合は0%になるはず
    assert percentage == pytest.approx(0.0, abs=0.1)

def test_calculate_color_areas(dummy_black_image, dummy_settings):
    # 黒画像の場合、全体が対象色とみなす設定なら合格となるか検証（設定に応じて調整）
    processor = ImageProcessor(dummy_black_image, dummy_settings)
    results, percentages = processor.calculate_color_areas()
    # このテストは、clip_positions の領域（例：0,0,100,100）の対象色割合が100%と判定されることを期待
    # 設定 thresholds は50.0 なので、100% >= 50.0 で合格
    assert len(results) == 1
    assert results[0] is True
    assert percentages[0] == pytest.approx(100.0, abs=0.1)

def test_calculate_trigger_area_states(dummy_black_image, dummy_settings):
    # 黒画像かつ trigger_positions も黒なら、トリガー状態は True になるはず
    processor = ImageProcessor(dummy_black_image, dummy_settings)
    states, percentages = processor.calculate_trigger_area_states()
    # テスト用 trigger_threshold は50.0なので、黒画像（100%）なら True
    if dummy_settings.settings.get("trigger_positions"):
        assert all(state is True for state in states)
        for p in percentages:
            assert p == pytest.approx(100.0, abs=0.1)
