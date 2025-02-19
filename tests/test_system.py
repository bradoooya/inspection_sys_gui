# tests/test_system.py
import os
import json
import time
import pytest
from app.web.app import app

@pytest.fixture
def client():
    """
    Flask のテストクライアントを作成するフィクスチャ
    """
    with app.test_client() as client:
        yield client

def test_index_page(client):
    """
    トップページ ('/') にアクセスし、HTTPステータス200と「Inspection System」というキーワードが含まれるかを確認する。
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b'Inspection System' in response.data

def test_calibration_page(client):
    """
    キャリブレーションページ ('/calibration') にアクセスし、ページに「キャリブレーション」というテキストがあるかを確認する。
    """
    response = client.get('/calibration')
    assert response.status_code == 200
    assert b'キャリブレーション' in response.data

def test_inspection_page(client):
    """
    検査ページ ('/inspection') にアクセスし、「検査」という文字列が含まれているかを確認する。
    """
    response = client.get('/inspection')
    assert response.status_code == 200
    assert b'検査' in response.data

def test_preview_page(client):
    """
    プレビューページ ('/preview') にアクセスし、画像が正しく返されるか、または適切なエラーメッセージが返るかを確認する。
    """
    response = client.get('/preview')
    # 画像ファイルが存在する場合は200、存在しなければ404が返されることを想定
    assert response.status_code in [200, 404]

def test_admin_page(client):
    """
    管理者ページ ('/admin') にアクセスし、「管理者」というキーワードが含まれるかを確認する。
    """
    response = client.get('/admin')
    assert response.status_code == 200
    assert b'管理者' in response.data

def test_get_settings_api(client):
    """
    /api/settings エンドポイントに GET リクエストを送り、設定情報の JSON が返されるかを検証する。
    """
    response = client.get('/api/settings')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'color_range' in data

def test_get_logs_api(client):
    """
    /api/logs エンドポイントに GET リクエストを送り、ログ情報が正しく取得できるかを検証する。
    """
    response = client.get('/api/logs')
    # ログファイルが存在する場合は200、なければ404を想定
    if response.status_code == 200:
        data = json.loads(response.data)
        assert 'logs' in data
    else:
        assert response.status_code == 404

def test_trigger_api(client):
    """
    /api/trigger エンドポイントに POST リクエストを送り、外部トリガー要求が正しく処理されるかを検証する。
    """
    response = client.post('/api/trigger', json={"trigger": "start"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get("status") == "Trigger received"

def test_system_performance(client):
    """
    システムに連続してリクエストを送り、応答時間や安定性を検証する（ストレステストの簡易例）。
    """
    start_time = time.time()
    for _ in range(50):
        response = client.get('/')
        assert response.status_code == 200
    elapsed_time = time.time() - start_time
    # 50回のリクエストで10秒以内に処理が完了するかを検証（環境により調整）
    assert elapsed_time < 10
