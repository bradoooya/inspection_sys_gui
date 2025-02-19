import torch
import torch.nn as nn
import torchvision.transforms as transforms
import logging
import cv2
import numpy as np

class MLModuleTorch:
    def __init__(self, model_path: str = "app/models/model.pt") -> None:
        self.model_path = model_path
        self.model = None
        self.device = torch.device("cpu")  # Raspberry Pi では通常 CPU を利用
        self.load_model()

    def load_model(self) -> None:
        try:
            # torch.load でモデルをロード
            self.model = torch.load(self.model_path, map_location=self.device)
            self.model.eval()  # 推論モードに設定
            logging.info(f"モデルをロードしました: {self.model_path}")
        except Exception as e:
            logging.error(f"モデルのロードに失敗しました: {e}")
            self.model = None

    def predict(self, image: np.ndarray) -> torch.Tensor:
        if self.model is None:
            logging.error("モデルがロードされていません。予測を実行できません。")
            return torch.Tensor()
        try:
            # 前処理: 例として、画像を224x224にリサイズしてテンソルに変換
            image_resized = cv2.resize(image, (224, 224))
            # OpenCVはBGRなので、必要に応じRGBに変換
            image_rgb = cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB)
            transform = transforms.Compose([
                transforms.ToTensor(),  # [0,255] → [0,1] に変換し、チャネルを先頭に
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
            ])
            input_tensor = transform(image_rgb)
            input_tensor = input_tensor.unsqueeze(0)  # バッチ次元を追加

            with torch.no_grad():
                output = self.model(input_tensor)
            logging.debug(f"予測結果: {output}")
            return output
        except Exception as e:
            logging.error(f"予測中にエラーが発生しました: {e}")
            return torch.Tensor()

    def train_model(self, train_data: torch.Tensor, labels: torch.Tensor, epochs: int = 10) -> None:
        if self.model is None:
            logging.error("モデルがロードされていません。学習を実行できません。")
            return
        try:
            self.model.train()
            optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
            criterion = nn.CrossEntropyLoss()
            for epoch in range(epochs):
                optimizer.zero_grad()
                outputs = self.model(train_data)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                logging.info(f"Epoch {epoch+1}/{epochs} - Loss: {loss.item()}")
            # 再学習後、モデルを保存
            torch.save(self.model, self.model_path)
            logging.info(f"モデルの再学習が完了し、保存されました: {self.model_path}")
        except Exception as e:
            logging.error(f"モデルの再学習中にエラーが発生しました: {e}")
