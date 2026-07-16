import logging
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from src.object_task.config import (
    OBJECT_MODEL_PATH,
    OBJECT_CONF_THRESHOLD,
    OBJECT_IOU_THRESHOLD,
    OBJECT_INPUT_SIZE,
    OBJECT_ENABLED,
    OBJECT_LABELS,
)

logger = logging.getLogger(__name__)


class ObjectDetector:
    def __init__(self, model_path, conf_threshold=0.35, iou_threshold=0.45, input_size=640):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.session = None
        self.input_name = None
        self.output_names = None
        self.enabled = False
        self._initialize()

    def _initialize(self):
        model_file = Path(self.model_path)
        if not model_file.exists():
            logger.warning("Object detector disabled because model file was not found: %s", self.model_path)
            return

        try:
            self.session = ort.InferenceSession(str(model_file), providers=["CPUExecutionProvider"])
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            self.enabled = True
            logger.info("Object detector initialized from %s", self.model_path)
        except Exception:
            logger.exception("Failed to initialize object detector from %s", self.model_path)

    @staticmethod
    def _letterbox(image, new_size=640, color=(114, 114, 114)):
        original_height, original_width = image.shape[:2]
        scale = min(new_size / original_height, new_size / original_width)
        resized_width = int(round(original_width * scale))
        resized_height = int(round(original_height * scale))
        pad_width = new_size - resized_width
        pad_height = new_size - resized_height
        pad_left = pad_width // 2
        pad_top = pad_height // 2

        resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)
        padded = cv2.copyMakeBorder(
            resized,
            pad_top,
            pad_height - pad_top,
            pad_left,
            pad_width - pad_left,
            cv2.BORDER_CONSTANT,
            value=color,
        )
        return padded, scale, pad_left, pad_top

    def detect(self, frame):
        if not self.enabled:
            return []

        padded, scale, pad_left, pad_top = self._letterbox(frame, self.input_size)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        blob = rgb.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None, ...]

        outputs = self.session.run(self.output_names, {self.input_name: blob})[0]
        predictions = np.squeeze(outputs)
        if predictions.ndim == 1:
            predictions = predictions[None, ...]
        if predictions.shape[0] < predictions.shape[1] and predictions.shape[0] in (5, 6, 7, 8):
            predictions = predictions.T

        detections = []
        for row in predictions:
            if row.shape[0] < 5:
                continue

            x_center, y_center, box_width, box_height = row[:4]
            score = float(row[4]) if row.shape[0] == 5 else float(np.max(row[4:]))
            if score < self.conf_threshold:
                continue

            x1 = (x_center - box_width / 2.0 - pad_left) / scale
            y1 = (y_center - box_height / 2.0 - pad_top) / scale
            x2 = (x_center + box_width / 2.0 - pad_left) / scale
            y2 = (y_center + box_height / 2.0 - pad_top) / scale

            x1 = int(max(0, min(frame.shape[1] - 1, round(x1))))
            y1 = int(max(0, min(frame.shape[0] - 1, round(y1))))
            x2 = int(max(0, min(frame.shape[1], round(x2))))
            y2 = int(max(0, min(frame.shape[0], round(y2))))

            if x2 <= x1 or y2 <= y1:
                continue

            class_scores = row[4:]
            class_id = int(np.argmax(class_scores)) if row.shape[0] > 5 else 0
            label = OBJECT_LABELS[class_id] if class_id < len(OBJECT_LABELS) else f"class_{class_id}"

            detections.append({
                "bbox": (x1, y1, x2, y2),
                "confidence": score,
                "class_id": class_id,
                "label": label,
            })

        if not detections:
            return []

        boxes = [[det["bbox"][0], det["bbox"][1], det["bbox"][2] - det["bbox"][0], det["bbox"][3] - det["bbox"][1]] for det in detections]
        confidences = [det["confidence"] for det in detections]
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)
        if len(indices) == 0:
            return []

        selected = []
        for index in np.array(indices).flatten():
            selected.append(detections[int(index)])
        return selected


class ObjectVisionSystem:
    def __init__(self):
        self.detector = ObjectDetector(
            OBJECT_MODEL_PATH,
            conf_threshold=OBJECT_CONF_THRESHOLD,
            iou_threshold=OBJECT_IOU_THRESHOLD,
            input_size=OBJECT_INPUT_SIZE,
        ) if OBJECT_ENABLED else None

    def process_frame(self, frame):
        if not self.detector or not self.detector.enabled:
            return []
        return self.detector.detect(frame)
