from app.core.camera import Camera
import logging

class CameraManager:
    """
    カメラの操作をシンプルに提供するファサード。
    UI側からはこのインターフェースを通してカメラの利用が可能です。
    """
    _camera = Camera()  # シングルトンのカメラインスタンス

    @classmethod
    def capture_single_frame(cls):
        """
        カメラのコンテキスト内で画像を1枚キャプチャします。
        """
        with cls._camera.use() as cam:
            if cam is None:
                logging.error("capture_single_frame: カメラ使用権を取得できません")
                return None
            frame = cam.capture_frame()
            return frame