# tests/test_settings.py
import os
import json
import pytest
from app.core.settings import Settings

def test_load_default_settings(tmp_path):
    """
    設定ファイルが存在しない場合、デフォルト設定が読み込まれ、
    設定ファイルが新たに作成されることを確認するテスト。
    """
    temp_dir = tmp_path / "data"
    temp_dir.mkdir()
    temp_settings = temp_dir / "settings.json"

    # 存在しない状態で Settings インスタンスを作成
    settings_obj = Settings(config_path=str(temp_settings))

    # キーがデフォルト設定から補完されているか確認
    assert "color_range" in settings_obj.settings
    # 設定ファイルが作成されたか確認
    assert temp_settings.exists()

def test_save_settings(tmp_path):
    """
    設定を変更して保存した際に、ファイルに変更が反映されるかをテストする。
    """
    temp_dir = tmp_path / "data"
    temp_dir.mkdir()
    temp_settings = temp_dir / "settings.json"
    settings_obj = Settings(config_path=str(temp_settings))

    # 変更を加える
    settings_obj.settings["frame_width"] = 1024
    settings_obj.save_settings()

    # ファイルから再読み込みして確認
    with open(str(temp_settings), "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["frame_width"] == 1024

def test_validate_settings(tmp_path):
    """
    不足しているキーが validate_settings により補完されるかをテストする。
    """
    temp_dir = tmp_path / "data"
    temp_dir.mkdir()
    temp_settings = temp_dir / "settings.json"

    # 不完全な設定データを用意
    incomplete_data = {"clip_positions": []}
    with open(str(temp_settings), "w", encoding="utf-8") as f:
        json.dump(incomplete_data, f)

    settings_obj = Settings(config_path=str(temp_settings))
    # いくつかの必須キーが補完されているか確認
    for key in ["color_range", "thresholds", "color_space", "gamma_value"]:
        assert key in settings_obj.settings
