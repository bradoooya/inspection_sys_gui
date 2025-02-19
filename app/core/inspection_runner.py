import glob
import os
import time
import cv2
import logging
from datetime import datetime
import RPi.GPIO as GPIO
from gpio_setup import setup_gpio, cleanup_gpio, BUSY_PIN, PASS_PIN, FAIL_PIN, CONTROL_PIN, FAIL_DETAIL_PINS, EXTERNAL_TRIGGER_PIN
from image_processor import ImageProcessor
from typing import Optional, List
from settings import Settings
import json
import threading

class InspectionRunner:
    """
    検査プロセス全体を実行するクラスです。
    カメラの初期化、画像キャプチャ、画像処理による判定、結果保存、GPIOの制御を行います。
    """

    def __init__(self, settings: "Settings", debug_mode: bool = False,
                 trigger_mode: str = "internal", output_mode: str = "direct") -> None:
        """
        初期化メソッド。

        Args:
            settings (Settings): システム設定オブジェクト。
            debug_mode (bool): DEBUGモードか否か。デバッグ時はループ数などが制限されます。
            trigger_mode (str): 'internal'（内部トリガー）または 'external'（外部トリガー）。
            output_mode (str): FAIL時の出力方式。ここでは 'direct' のみ利用（binaryは廃止）。
        """
        self.settings: "Settings" = settings
        self.image_dir: str = "result/images"    # 画像保存先ディレクトリ
        self.json_dir: str = "result/json"         # JSON結果保存先ディレクトリ
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)

        self.debug_mode = debug_mode
        self.trigger_mode = trigger_mode
        self.output_mode = output_mode

        self.loop_count = 0
        self.stop_event = threading.Event()  # ループ停止用のフラグ

        self.last_external_trigger_state = GPIO.LOW  # 外部トリガーの前回状態

        # GPIO の初期化
        setup_gpio()
        logging.info("InspectionRunner 初期化完了")

    def run(self, max_loops: Optional[int] = None) -> None:
        """
        検査プロセスのメインループを実行します。

        Args:
            max_loops (Optional[int]): 最大ループ回数。Noneの場合は無制限に実行。
        """
        logging.info("検査プロセスの実行を開始します")
        try:
            while not self.stop_event.is_set():
                if self.trigger_mode == "internal":
                    # 内部トリガーの場合、CONTROL_PIN の状態を確認
                    if GPIO.input(CONTROL_PIN) == GPIO.LOW:
                        logging.info("内部トリガー: 制御ピンがLOWのため、検査開始")
                        self.perform_inspection_cycle(max_loops)
                    else:
                        logging.info("内部トリガー: 制御ピンがHIGH。待機状態です。")
                        self.wait_for_control_pin()
                elif self.trigger_mode == "external":
                    # 外部トリガーの場合、GPIOからの変化を監視
                    external_state = GPIO.input(EXTERNAL_TRIGGER_PIN)
                    if external_state == GPIO.HIGH and self.last_external_trigger_state == GPIO.LOW:
                        logging.info("外部トリガー: 状態変化検出。検査開始")
                        self.perform_inspection_cycle(max_loops)
                    else:
                        time.sleep(0.1)
                    self.last_external_trigger_state = external_state
                else:
                    logging.error(f"不明なトリガーモード: {self.trigger_mode}")
                    break
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt を検知。検査プロセスを停止します。")
        finally:
            self.stop()

    def wait_for_control_pin(self) -> None:
        """
        CONTROL_PIN が HIGH になるまで待機する。
        """
        logging.info("CONTROL_PIN の状態が HIGH になるのを待機中...")
        while not self.stop_event.is_set():
            if GPIO.input(CONTROL_PIN) == GPIO.HIGH:
                logging.info("CONTROL_PIN が HIGH になりました。")
                break
            time.sleep(0.5)

    def perform_inspection_cycle(self, max_loops: Optional[int] = None) -> None:
        """
        1回分の検査サイクル（カメラ初期化、フレームキャプチャ、検査処理、結果保存）を実行する。

        Args:
            max_loops (Optional[int]): 最大ループ回数。指定があれば、その回数に達したらサイクルを停止。
        """
        while not self.stop_event.is_set():
            if max_loops is not None and self.loop_count >= max_loops:
                logging.info("最大ループ回数に達したため、サイクルを停止します。")
                break

            # カメラの初期化
            logging.info("カメラの初期化中...")
            cap = self.initialize_camera()
            if cap is None:
                logging.error("カメラ初期化失敗。再試行します。")
                time.sleep(5)
                continue

            # フレームキャプチャ
            ret, frame = cap.read()
            if not ret or frame is None:
                logging.error("フレームキャプチャに失敗。再試行します。")
                cap.release()
                time.sleep(1)
                continue

            # カメラリソースの解放（キャプチャ直後に解放）
            cap.release()

            # 必要に応じて回転処理
            rotation = self.settings.settings.get("rotation", 0)
            if rotation == 90:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rotation == 180:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif rotation == 270:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

            # トリガーモードに応じた処理
            if self.trigger_mode == "internal":
                processor = ImageProcessor(frame, self.settings)
                trigger_states, trigger_percentages = processor.calculate_trigger_area_states()
                logging.info(f"トリガー状態: {trigger_states}")
                # すべてのトリガー条件が満たされた場合のみ判定を実行
                if all(trigger_states):
                    self.execute_inspection(frame, processor, trigger_states, trigger_percentages)
                else:
                    logging.debug("トリガー条件未満のため、判定処理をスキップします。")
            elif self.trigger_mode == "external":
                processor = ImageProcessor(frame, self.settings)
                self.execute_inspection(frame, processor, [], [])
            
            self.loop_count += 1
            logging.debug(f"ループ回数: {self.loop_count}")

            # 外部トリガーモードの場合、1回の実行で終了
            if self.trigger_mode == "external":
                logging.info("外部トリガーモードのため、1回実行で終了します。")
                break

    def execute_inspection(self, frame, processor, trigger_states: List[bool], trigger_percentages: List[float]) -> None:
        """
        画像処理を実行し、検査結果を保存するとともに、GPIO出力を制御します。

        Args:
            frame: キャプチャした画像
            processor: ImageProcessor のインスタンス
            trigger_states: トリガー領域の状態リスト（内部トリガーの場合）
            trigger_percentages: 各トリガー領域の黒の割合リスト
        """
        # GPIO をビジー状態に設定
        GPIO.output(BUSY_PIN, GPIO.HIGH)
        GPIO.output(PASS_PIN, GPIO.LOW)
        GPIO.output(FAIL_PIN, GPIO.LOW)
        for pin in FAIL_DETAIL_PINS:
            GPIO.output(pin, GPIO.LOW)
        logging.info(f"GPIO BUSY_PIN を HIGH に設定しました。{datetime.now()}")

        # 撮影前の待機
        time.sleep(1)

        # 画像処理による判定
        results, percentages = processor.calculate_color_areas()
        logging.info(f"判定結果: {results}, 色割合: {percentages}")

        # 画像と結果の保存
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.save_image(frame.copy(), results, percentages, trigger_states, trigger_percentages, timestamp)

        # 判定に応じたGPIO制御
        if all(results):
            GPIO.output(PASS_PIN, GPIO.HIGH)
            logging.info(f"合格：GPIO PASS_PIN を HIGH に設定 {datetime.now()}")
        else:
            GPIO.output(FAIL_PIN, GPIO.HIGH)
            logging.info(f"不合格：GPIO FAIL_PIN を HIGH に設定 {datetime.now()}")
            # 詳細な不合格情報の出力（handle_fail_details で実施）
            self.handle_fail_details(results)
        
        # ビジー状態の解除
        time.sleep(1)
        GPIO.output(BUSY_PIN, GPIO.LOW)
        logging.info(f"GPIO BUSY_PIN を LOW に設定 {datetime.now()}")

    def initialize_camera(self) -> Optional[cv2.VideoCapture]:
        """
        利用可能なカメラを自動検出し、VideoCapture オブジェクトを返します。

        Returns:
            cv2.VideoCapture または None（カメラが見つからなかった場合）
        """
        video_devices = glob.glob("/dev/video*")
        if not video_devices:
            logging.error("利用可能なビデオデバイスが見つかりません。")
            return None

        for device in sorted(video_devices):
            device_id = int(device.replace("/dev/video", ""))
            logging.debug(f"カメラデバイス {device} を試行中...")
            cap = cv2.VideoCapture(device_id)
            if cap.isOpened():
                logging.info(f"カメラがデバイス {device} で認識されました。")
                frame_width = self.settings.settings.get("frame_width", 640)
                frame_height = self.settings.settings.get("frame_height", 480)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
                cap.set(cv2.CAP_PROP_FPS, 15.0 if self.debug_mode else 7.5)
                return cap
            else:
                logging.warning(f"カメラ {device} は利用できません。")
                cap.release()
        logging.error("カメラの初期化に失敗しました。")
        return None

    def save_image(self, frame, results: List[bool], percentages: List[float],
                   trigger_states: List[bool], trigger_percentages: List[float],
                   timestamp: str) -> None:
        """
        検査結果の画像と結果情報を保存します。

        Args:
            frame: 保存する画像（NumPy 配列）
            results: 各検査領域の判定結果
            percentages: 各検査領域における対象色の割合
            trigger_states: トリガー領域の状態リスト
            trigger_percentages: トリガー領域の黒の割合リスト
            timestamp: 保存ファイル名に利用するタイムスタンプ
        """
        try:
            # 画像に検査結果のオーバーレイ描画（例：矩形、割合表示）
            clip_positions = self.settings.settings.get("clip_positions", [])
            for idx, pos in enumerate(clip_positions):
                x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
                color = (255, 0, 0) if results[idx] else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                text = f"{percentages[idx]:.2f}%"
                cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            # 画像の保存
            image_filename = os.path.join(self.image_dir, f"{timestamp}.png")
            cv2.imwrite(image_filename, frame)
            logging.info(f"画像を保存しました: {image_filename}")
            # 結果情報を JSON として保存
            results_data = {
                "timestamp": timestamp,
                "results": results,
                "percentages": percentages,
                "trigger_states": trigger_states,
                "trigger_percentages": trigger_percentages,
            }
            results_filename = os.path.join(self.json_dir, f"{timestamp}.json")
            with open(results_filename, "w", encoding="utf-8") as f:
                json.dump(results_data, f, indent=4, ensure_ascii=False)
            logging.info(f"結果情報を保存しました: {results_filename}")
        except Exception as e:
            logging.exception(f"画像の保存中にエラーが発生しました: {e}")

    def handle_fail_details(self, results: List[bool]) -> None:
        """
        不合格の場合、GPIO の FAIL_DETAIL_PINS を利用して詳細情報を出力します。

        Args:
            results: 各検査領域の判定結果
        """
        # 簡易例として、結果に応じたパターンを設定する
        pattern = [GPIO.HIGH if not res else GPIO.LOW for res in results]
        # FAIL_DETAIL_PINS 数に合わせてパターンを調整
        pattern = pattern[:len(FAIL_DETAIL_PINS)]
        for pin, state in zip(FAIL_DETAIL_PINS, pattern):
            GPIO.output(pin, state)
        # 点灯後、一定時間後にクリア
        time.sleep(self.settings.settings.get("result_output_duration", 1.0))
        for pin in FAIL_DETAIL_PINS:
            GPIO.output(pin, GPIO.LOW)

    def stop(self) -> None:
        """
        検査プロセスを停止し、GPIO をクリーンアップします。
        """
        self.stop_event.set()
        cleanup_gpio()
        logging.info("InspectionRunner を停止し、GPIO をクリーンアップしました。")
