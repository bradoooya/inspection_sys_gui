import os
from flask import Flask, render_template, jsonify, send_from_directory, request
import logging

# Flask インスタンスの作成
app = Flask(__name__, template_folder='templates', static_folder='static')

# ログ設定（必要に応じてファイル出力も追加）
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@app.route('/')
def index():
    """
    トップページ。システムの概要や各機能へのリンクを表示します。
    """
    return render_template('index.html')


@app.route('/calibration')
def calibration():
    """
    キャリブレーション画面。
    - カメラの向き、照明、色調整などを行うための画面。
    - 実際の処理は Core モジュールのキャリブレーション API と連携する予定。
    """
    return render_template('calibration.html')


@app.route('/inspection')
def inspection():
    """
    検査画面。
    - 検査処理の開始ボタンや検査結果の表示を行います。
    - 内部トリガー／外部トリガーの切り替えや、検査結果の統計情報を表示する予定。
    """
    return render_template('inspection.html')


@app.route('/preview')
def preview():
    """
    プレビューページ。
    - リアルタイムのカメラ映像や、処理済みの画像を表示します。
    - ここでは、例として「result/images」フォルダ内の最新画像を返す処理を行います。
    """
    # 例: 最新の画像ファイル名を "latest.png" とする（実際は Core から最新画像を取得する実装に変更）
    image_filename = "latest.png"
    image_dir = os.path.join(app.root_path, "..", "result", "images")
    if os.path.exists(os.path.join(image_dir, image_filename)):
        return send_from_directory(image_dir, image_filename)
    else:
        return "No preview available", 404


@app.route('/admin')
def admin():
    """
    管理者用画面。
    - システムの詳細設定、ログの確認、ユーザーロール管理などを行うページです。
    """
    return render_template('admin.html')


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """
    API エンドポイント：設定情報を JSON 形式で返します。
    """
    settings_path = os.path.join(app.root_path, "..", "app", "data", "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_data = f.read()
        return settings_data, 200, {'Content-Type': 'application/json'}
    else:
        return jsonify({"error": "Settings file not found"}), 404


@app.route('/api/trigger', methods=['POST'])
def trigger_inspection():
    """
    API エンドポイント：検査のトリガーを外部から制御するための例です。
    （実際には Core モジュールの InspectionRunner と連携して検査処理を開始します）
    """
    data = request.get_json()
    # ここで外部トリガーの処理を実施（例: trigger_mode が 'external' の場合）
    logging.info(f"外部トリガー要求を受け取りました: {data}")
    return jsonify({"status": "trigger received"}), 200

if __name__ == '__main__':
    # ホスト 0.0.0.0 で実行することで、ネットワーク上の他のデバイスからもアクセス可能
    app.run(host='0.0.0.0', port=5000, debug=True)
