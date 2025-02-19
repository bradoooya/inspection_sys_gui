# tests/test_integration.py
import os
import json
import pytest
from app.web.app import app

@pytest.fixture
def client():
    # Flask のテストクライアントを利用するためのフィクスチャ
    with app.test_client() as client:
        yield client

def test_index_page(client):
    """
    トップページ ('/') にアクセスして、HTTP ステータス 200 と
    ページ内に "Inspection System" の文字列が含まれているかを確認。
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b'Inspection System' in response.data

def test_calibration_page(client):
    """
    キャリブレーション画面 ('/calibration') にアクセスして、
    正しいHTMLが返されるか確認。
    """
    response = client.get('/calibration')
    assert response.status_code == 200
    assert b'キャリブレーション' in response.data

def test_inspection_page(client):
    """
    検査画面 ('/inspection') にアクセスし、ページ内に「検査」というキーワードが含まれるか確認。
    """
    response = client.get('/inspection')
    assert response.status_code == 200
    assert b'検査' in response.data

def test_preview_page(client):
    """
    プレビュ―画面 ('/preview') にアクセスし、画像が返されるか、
    または適切なエラーメッセージ（404 など）が返されるか確認。
    """
    response = client.get('/preview')
    # 画像ファイルが存在する場合は 200、存在しない場合は 404 と想定
    assert response.status_code in [200, 404]

def test_admin_page(client):
    """
    管理者用画面 ('/admin') にアクセスし、ページ内に「管理者」という文字列が含まれるか確認。
    """
    response = client.get('/admin')
    assert response.status_code == 200
    assert b'管理者' in response.data

def test_get_settings_api(client):
    """
    /api/settings エンドポイントに GET リクエストを送り、設定情報の JSON が返されるか確認。
    """
    response = client.get('/api/settings')
    assert response.status_code == 200
    data = json.loads(response.data)
    # 例として、color_range キーが存在するか確認
    assert 'color_range' in data

def test_get_logs_api(client):
    """
    /api/logs エンドポイントに GET リクエストを送り、ログ情報が返されるか確認。
    """
    response = client.get('/api/logs')
    # ログファイルが存在する場合は200、なければ404と想定
    if response.status_code == 200:
        data = json.loads(response.data)
        assert 'logs' in data
    else:
        assert response.status_code == 404

def test_trigger_api(client):
    """
    /api/trigger エンドポイントに POST リクエストを送り、外部トリガーが受信された旨の応答が返されるか確認。
    """
    response = client.post('/api/trigger', json={"trigger": "start"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data.get("status") == "Trigger received"
