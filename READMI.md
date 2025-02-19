
# Inspection System

## Overview

Inspection Systemは、Raspberry Piを活用した低コスト・高信頼性の機械視覚検査システムです。  
従来は個別に行われていたキャリブレーション（カメラや照明の調整）と検査処理を1つの統合アプリケーションにまとめ、オペレーターが直感的に操作できるUIおよびWeb画面を提供します。  
また、自動キャリブレーション、自己学習、検査結果の統計分析などの先進機能により、安定した検査精度と継続的なシステム改善を実現しています。

## Features

- **統合キャリブレーション／検査／プレビュー機能**  
  - 起動時のカメラ専用キャリブレーション画面で、照明やカメラ位置の最適化をサポート。
  - ウィザード形式で、撮影条件、カラー範囲、検査領域の設定を簡単に行えます。

- **自動キャリブレーション＆自己学習**  
  - 撮影環境（照明、色温度、露出）を自動解析し、最適なカメラ設定を自動補正。
  - 過去の検査結果や誤判定データを基に、システムが自己学習を行い、キャリブレーション条件を最適化。

- **リアルタイム検査と結果表示**  
  - 内部／外部トリガーにより検査を開始し、画像処理により対象物の合否判定を実施。
  - 合否は大きな○×アイコンやランプ表示で、オペレーターに直感的なフィードバックを提供。

- **結果管理とリモート監視**  
  - 撮影画像や検査結果はタイムスタンプ付きで自動保存され、検査履歴をグラフ化・統計分析可能。
  - FlaskベースのWebアプリにより、リモートからのモニタリングや管理者用ログ確認が可能。

## Directory Structure

```
my_inspection_project/
├── app/
│   ├── core/                 # 設定、画像処理、検査ロジック、GPIO管理、機械学習モジュール
│   ├── ui/                   # キャリブレーション、検査、プレビュー、管理者用GUI
│   ├── web/                  # FlaskベースのWebアプリ（テンプレート、静的ファイル含む）
│   └── data/                 # 初期設定ファイルなどリソース類
├── tests/                    # 単体・統合テスト
├── log/                      # ログファイル（Rotating log）
├── result/                   # 検査結果の画像／JSONデータ
├── requirements.txt          # 必要なライブラリ一覧
└── README.md
```

## Setup

1. **Pythonのインストール**  
   推奨バージョン: Python 3.8～3.10

2. **仮想環境の作成・有効化**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # venv\Scripts\activate   # Windows
   ```

3. **依存ライブラリのインストール**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Gitリポジトリの初期化**（初回のみ）  
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Setup project structure"
   ```

## Running the Application

- **GUI版（デスクトップ）**  
  `app/ui/main.py` を実行して、ウィザード形式のキャリブレーション・検査画面を起動します。

- **Web版**  
  `app/web/app.py` を実行すると、Flaskサーバーが起動し、ブラウザからシステムの監視や管理が可能になります。

- **CLIデバッグモード**  
  コマンドラインから以下のように実行できます。  
  ```bash
  python app/core/main.py --mode debug --trigger internal --output-mode direct
  ```

## Contributing

- コードの改善や新機能の追加は、ブランチを分けた上でプルリクエストをお願いします。  
- テストケースの充実にもご協力ください。  
- 詳細なガイドラインは `CONTRIBUTING.md` をご確認ください。

## License

本プロジェクトはMITライセンスの下で公開されています。  
詳細は LICENSE ファイルをご覧ください。