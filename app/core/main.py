# app/core/main.py
import sys
import argparse
import logging
from logger_setup import LoggerSetup
from settings import Settings
from inspection_runner import InspectionRunner
from gpio_setup import cleanup_gpio

def main() -> None:
    """
    メイン関数:
      - コマンドライン引数による実行モードやトリガーモードの設定
      - 設定ファイル（settings.json）の読み込み
      - LoggerSetup によるログ設定
      - InspectionRunner を用いた検査プロセスの実行
      - 最終的な GPIO のクリーンアップ
    """
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="検査システムの実行モードを選択します。")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["default", "debug"],
        default="default",
        help="実行モードを選択します。default: 継続実行、debug: 最大10ループ"
    )
    parser.add_argument(
        "--trigger",
        type=str,
        choices=["internal", "external"],
        default="internal",
        help="トリガーモードを選択します。internal: 内部トリガー、external: 外部トリガー"
    )
    parser.add_argument(
        "--output-mode",
        type=str,
        choices=["direct", "binary"],
        default="direct",
        help="FAIL時の出力方式を選択します。direct: 直接出力方式、binary: バイナリ方式（現在は direct のみサポート）"
    )
    args = parser.parse_args()

    # モードに応じたログレベルおよびループ回数の設定
    if args.mode == "default":
        log_level = logging.INFO
        max_loops = None  # 継続実行
        debug_mode = False
    else:  # args.mode == "debug"
        log_level = logging.DEBUG
        max_loops = 10    # 最大10ループ
        debug_mode = True

    # ログ設定の初期化
    LoggerSetup.setup_logging(log_level=log_level)
    logging.info(f"プログラム開始 (モード: {args.mode}, トリガーモード: {args.trigger}, ログレベル: {log_level})")

    # 設定の読み込み（app/data/settings.json から読み込み）
    settings = Settings()
    logging.info("設定の読み込み完了")

    # InspectionRunner の初期化（Core モジュールの検査処理）
    runner = InspectionRunner(settings, debug_mode=debug_mode, trigger_mode=args.trigger, output_mode=args.output_mode)
    logging.info("InspectionRunner の初期化完了")

    # 検査プロセスの実行
    try:
        runner.run(max_loops=max_loops)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt を検知。検査プロセスを停止します。")
    except Exception as e:
        logging.exception(f"検査プロセス中に予期せぬエラーが発生しました: {e}")
    finally:
        # GPIO のクリーンアップを実施し、システム終了時のリソース解放を行う
        cleanup_gpio()
        logging.info("プログラム終了")

if __name__ == "__main__":
    main()
