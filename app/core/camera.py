import cv2
import os
import logging
import subprocess
from contextlib import contextmanager

class Camera:
    """
    シングルトンとしてカメラインスタンスを管理。
    """
    _instance = None
    _is_initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, scanning_count: int = 30) -> None:
        if not self._is_initialized:
            logging.debug("Camera.__init__ 開始: scanning_count=%s", scanning_count)
            self.scanning_count = scanning_count
            self.cap = None
            self.device = None
            self._in_use = False  # 使用中フラグ
            if not self._open_camera():
                logging.error("カメラの初期化に失敗しました")
            Camera._is_initialized = True

    def _open_camera(self) -> bool:
        """
        利用可能なカメラデバイスをスキャンしてオープンします。
        """
        for i in range(self.scanning_count):
            device_path = f"/dev/video{i}"
            if os.path.exists(device_path):
                logging.debug("デバイスチェック: %s 発見", device_path)
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    self.cap = cap
                    self.device = device_path
                    logging.info("カメラデバイス %s をオープンしました", device_path)
                    return True
                else:
                    logging.error("カメラデバイス %s のオープンに失敗しました", device_path)
        logging.error("_open_camera: 利用可能なカメラが見つかりませんでした。")
        return False

    def find_and_open(self) -> bool:
        """
        既存の _open_camera() を呼び出して、利用可能なカメラデバイスを探し、オープンします。
        """
        return self._open_camera()

    @contextmanager
    def use(self):
        """
        カメラ使用のためのコンテキストマネージャ。
        利用時に _in_use フラグをセットし、処理後は自動的に解放します。
        """
        if self._in_use:
            logging.warning("カメラは既に使用中です")
            yield None
        else:
            self._in_use = True
            try:
                yield self
            finally:
                self._in_use = False
                logging.debug("カメラ使用権を自動解放しました")

    def acquire(self) -> bool:
        """
        カメラの使用権を取得するメソッド。
        Returns:
            bool: 使用権取得に成功した場合 True、既に使用中の場合 False
        """
        if self._in_use:
            logging.warning("acquire: カメラは既に使用中です。")
            return False
        self._in_use = True
        logging.debug("acquire: カメラ使用権を取得しました。")
        return True

    def capture_frame(self):
        """
        オープン済みのカメラから1枚の画像（BGR形式）をキャプチャします。
        """
        if self.cap is None or not self.cap.isOpened():
            logging.error("capture_frame: カメラがオープンされていません。")
            return None

        ret, frame = self.cap.read()
        if not ret:
            logging.error("フレームの読み取りに失敗しました")
            return None
        logging.info("capture_frame: 画像キャプチャ成功")
        return frame

    def release_camera(self) -> None:
        """
        カメラリソースを完全に解放する場合のメソッド。
        (通常は自動解放により管理します)
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logging.info("カメラを解放しました")

    def set_white_balance(self, value: int) -> None:
        """
        ホワイトバランス温度を設定します。

        Args:
            value (int): 設定する温度値
        """
        logging.debug("set_white_balance 開始: value=%s", value)
        if not hasattr(self, "device"):
            logging.error("set_white_balance: 使用中のカメラデバイスが設定されていません。")
            return
        try:
            subprocess.run(["v4l2-ctl", "-d", self.device, "--set-ctrl", "white_balance_automatic=0"],
                           check=True)
            logging.debug("ホワイトバランス自動制御をオフに設定")
            subprocess.run(["v4l2-ctl", "-d", self.device, "--set-ctrl", f"white_balance_temperature={value}"],
                           check=True)
            logging.info("ホワイトバランス温度を %s に設定完了", value)
        except subprocess.CalledProcessError as e:
            logging.error("ホワイトバランスの設定に失敗: %s", str(e))
        logging.debug("set_white_balance 完了")

    def set_brightness(self, value: int) -> None:
        """
        明るさを設定します。

        Args:
            value (int): 設定する明るさの値
        """
        logging.debug("set_brightness 開始: value=%s", value)
        if not hasattr(self, "device"):
            logging.error("set_brightness: 使用中のカメラデバイスが設定されていません。")
            return
        try:
            subprocess.run(["v4l2-ctl", "-d", self.device, "--set-ctrl", f"brightness={value}"],
                           check=True)
            logging.info("明るさの設定が完了しました。")
        except subprocess.CalledProcessError as e:
            logging.error("明るさの設定に失敗: %s", str(e))
        logging.debug("set_brightness 完了")

    def set_contrast(self, value: int) -> None:
        """
        コントラストを設定します。

        Args:
            value (int): 設定するコントラスト値
        """
        logging.debug("set_contrast 開始: value=%s", value)
        if not hasattr(self, "device"):
            logging.error("set_contrast: 使用中のカメラデバイスが設定されていません。")
            return
        try:
            subprocess.run(["v4l2-ctl", "-d", self.device, "--set-ctrl", f"contrast={value}"],
                           check=True)
            logging.info("コントラストの設定が完了しました。")
        except subprocess.CalledProcessError as e:
            logging.error("コントラストの設定に失敗: %s", str(e))
        logging.debug("set_contrast 完了")

    def set_saturation(self, value: int) -> None:
        """
        彩度を設定します。

        Args:
            value (int): 設定する彩度値
        """
        logging.debug("set_saturation 開始: value=%s", value)
        if not hasattr(self, "device"):
            logging.error("set_saturation: 使用中のカメラデバイスが設定されていません。")
            return
        try:
            subprocess.run(["v4l2-ctl", "-d", self.device, "--set-ctrl", f"saturation={value}"],
                           check=True)
            logging.info("彩度の設定が完了しました。")
        except subprocess.CalledProcessError as e:
            logging.error("彩度の設定に失敗: %s", str(e))
        logging.debug("set_saturation 完了")

    def set_resolution_scale(self, value: int) -> None:
        """
        解像度スケールの設定（多くのUSBカメラは直接変更不可）。

        Args:
            value (int): 設定する解像度スケール値
        """
        logging.debug("set_resolution_scale 開始: value=%s", value)
        logging.info("解像度スケールを %s に設定します。", value)
        # 実際にハードウェア制御する場合はここに記述
        logging.debug("set_resolution_scale 完了")

# ---------------------------
# 外部ユーティリティ関数
# ---------------------------
def force_release_device(device: str) -> None:
    """
    指定されたカメラデバイスの利用中プロセスを、現在のプロセスを除外して強制終了します。

    Args:
        device (str): 解放対象のデバイスパス（例: '/dev/video0'）
    """
    logging.debug("force_release_device 開始: device=%s", device)
    try:
        result = subprocess.run(["sudo", "fuser", device],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        pids = result.stdout.strip().split()
        logging.debug("fuser 結果: stdout=%s, stderr=%s", result.stdout.strip(), result.stderr.strip())
        current_pid = str(os.getpid())
        filtered_pids = [pid for pid in pids if pid != current_pid]
        if filtered_pids:
            logging.info("%s は以下のプロセスが使用中 (除外: 自プロセス %s): %s", 
                         device, current_pid, " ".join(filtered_pids))
            subprocess.run(["sudo", "fuser", "-k", device], check=True)
            logging.info("%s の使用中プロセスを強制終了しました。", device)
        else:
            logging.info("%s は使用中のプロセスがありません。", device)
    except Exception as e:
        logging.error("%s の解放処理に失敗しました: %s", device, str(e))
    logging.debug("force_release_device 完了")

def capture_single_frame():
    """
    利用可能なカメラから1枚の画像（BGR形式）をキャプチャします。
    Returns:
        numpy.ndarray or None: 撮影した画像、失敗した場合は None
    """
    logging.debug("capture_single_frame 開始")
    camera = Camera()  # シングルトンインスタンスを取得
    frame = None
    
    with camera.use() as cam:
        if cam is not None:
            frame = cam.capture_frame()
            if frame is not None:
                logging.info("capture_single_frame: 画像キャプチャ成功")
            else:
                logging.error("capture_single_frame: 画像キャプチャに失敗")
    
    logging.debug("capture_single_frame 完了")
    return frame