import RPi.GPIO as GPIO
import logging

# 警告メッセージの無効化
GPIO.setwarnings(False)

# GPIOピンの定義（物理ピン番号）
BUSY_PIN = 8      # BUSY状態の表示用（出力専用）
PASS_PIN = 10     # 検査合格時の表示用（出力専用）
FAIL_PIN = 16     # 検査不合格時の表示用（出力専用）
CONTROL_PIN = 15  # 内部トリガー入力用（入力専用）
# FAIL詳細出力用のGPIOピン（複数の検査領域に対応）
FAIL_DETAIL_PINS = [18, 22, 24, 26, 32]
# 外部トリガー入力用ピンの定義
EXTERNAL_TRIGGER_PIN = 13  # 外部トリガー入力（入力専用）

def setup_gpio():
    """
    GPIO を初期化する関数です。
    - GPIOの番号付け方式として BOARD モードを使用します。
    - 各ピンの方向（入力/出力）や初期状態、プルアップ／プルダウン設定を行います。
    """
    # BOARD モードを指定（物理ピン番号を使用）
    GPIO.setmode(GPIO.BOARD)
    
    # 出力用ピンの設定（初期状態は LOW）
    GPIO.setup(BUSY_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(PASS_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(FAIL_PIN, GPIO.OUT, initial=GPIO.LOW)
    
    # 入力用ピンの設定
    # CONTROL_PIN は内部トリガーのため、プルダウン抵抗を有効に
    GPIO.setup(CONTROL_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # 外部トリガーピンも同様にプルダウン設定
    GPIO.setup(EXTERNAL_TRIGGER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    # FAIL_DETAIL_PINS も出力として設定（初期状態 LOW）
    for pin in FAIL_DETAIL_PINS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    
    logging.info(f"{__name__}.setup_gpio: GPIO を初期化しました。")

def cleanup_gpio():
    """
    GPIO をクリーンアップする関数です。
    - GPIO.cleanup() を呼び出し、使用したGPIOリソースを解放します。
    """
    try:
        GPIO.cleanup()
        logging.info(f"{__name__}.cleanup_gpio: GPIO をクリーンアップしました。")
    except Exception as e:
        logging.exception(f"GPIOクリーンアップ中にエラーが発生しました: {e}")
