import os
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv
from ultralytics import YOLO


class SegmentationModel:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.model = None
        self.number_of_parts = 10  # depends on the model

    def _prepare_model(self):
        if self.model is None:
            self.model = YOLO(self.model_path)

    @staticmethod
    def _undone_yolo_letterbox(mask, target_height: int, target_width: int):
        mask_np = mask.data.cpu().numpy().squeeze()
        mask_height, mask_width = mask_np.shape

        # スケール計算 (アスペクト比を維持しつつ最大化)
        rh = target_height / mask_height
        rw = target_width / mask_width
        r = max(rh, rw)

        # マスクをリサイズ
        mask_resized = cv2.resize(
            mask_np,
            (int(mask_width * r), int(mask_height * r)),
            interpolation=cv2.INTER_LINEAR,
        )

        # 中央に合わせる
        h_diff = max(0, mask_resized.shape[0] - target_height)
        w_diff = max(0, mask_resized.shape[1] - target_width)

        top, bottom = h_diff // 2, h_diff - (h_diff // 2)
        left, right = w_diff // 2, w_diff - (w_diff // 2)

        # スライスで中央配置
        mask_cropped = mask_resized[
            top : -bottom if bottom > 0 else None, left : -right if right > 0 else None
        ]

        return mask_cropped.astype(bool)

    def predict(self, image: np.ndarray) -> np.ndarray:
        self._prepare_model()
        results = self.model(image)

        h, w = image.shape[:2]
        parts = {i: np.zeros((h, w), dtype=bool) for i in range(self.number_of_parts)}

        for result in results:
            if not result.boxes or not result.masks:
                continue
            for box, mask in zip(result.boxes, result.masks):
                part_id = int(box.cls)
                parts[part_id] = np.bitwise_or(
                    parts[part_id],
                    self._undone_yolo_letterbox(mask, h, w),
                )

        labeled_image = np.zeros((h, w), dtype=np.uint8)
        for part_id, mask in parts.items():
            if np.any(mask):
                labeled_image[mask] = part_id + 1

        return labeled_image

    def segment_image(self, input_path: Path, output_path: Path):
        image = cv2.imread(str(input_path))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        labeled_image = self.predict(image)
        cv2.imwrite(output_path, labeled_image)
        # cv2.imwrite(output_path, (labeled_image+ 1) * 10)


if __name__ == "__main__":
    load_dotenv()

    model = SegmentationModel(model_path=os.environ["SEGMENTATION_MODEL"])
    input_path = Path("work/workset1/images/00003.png").resolve()
    model.segment_image(
        input_path, input_path.parent.parent / "sam" / (input_path.stem + ".png")
    )

