import cv2
import numpy as np
import logging
from pathlib import Path

import onnxruntime as ort

from src.balloon_task.config import (
    HSV_BOUNDS,
    REAL_BALLOON_WIDTH_CM,
    FOCAL_LENGTH_PX,
    YOLO_MODEL_PATH,
    YOLO_CONF_THRESHOLD,
    YOLO_IOU_THRESHOLD,
    YOLO_INPUT_SIZE,
    YOLO_ENABLED,
    COLOR_MASK_MIN_RATIO,
    COLOR_COMBINED_SCORE_THRESHOLD,
)
from src.shared.camera import SharedCamera

logger = logging.getLogger(__name__)


class BalloonDetector:
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
            logger.warning("YOLO detector disabled because model file was not found: %s", self.model_path)
            return

        try:
            self.session = ort.InferenceSession(str(model_file), providers=['CPUExecutionProvider'])
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            self.enabled = True
            logger.info("YOLO detector initialized from %s", self.model_path)
        except Exception:
            logger.exception("Failed to initialize YOLO detector from %s", self.model_path)

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

            detections.append({
                'bbox': (x1, y1, x2, y2),
                'confidence': score,
            })

        if not detections:
            return []

        boxes = [[det['bbox'][0], det['bbox'][1], det['bbox'][2] - det['bbox'][0], det['bbox'][3] - det['bbox'][1]] for det in detections]
        confidences = [det['confidence'] for det in detections]
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)

        if len(indices) == 0:
            return []

        selected = []
        for index in np.array(indices).flatten():
            selected.append(detections[int(index)])
        return selected


class VisionSystem:
    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None
        self.camera = SharedCamera(camera_index=camera_index, width=width, height=height)
        self.detector = BalloonDetector(
            YOLO_MODEL_PATH,
            conf_threshold=YOLO_CONF_THRESHOLD,
            iou_threshold=YOLO_IOU_THRESHOLD,
            input_size=YOLO_INPUT_SIZE,
        ) if YOLO_ENABLED else None

    def initialize(self, retries=3):
        opened = self.camera.open(retries=retries)
        if opened:
            self.cap = self.camera.cap
        return opened

    def read_frame(self):
        return self.camera.read()

    @staticmethod
    def _build_mask_from_roi(frame_shape, bbox, roi_mask):
        full_mask = np.zeros(frame_shape[:2], dtype=np.uint8)
        x1, y1, x2, y2 = bbox
        full_mask[y1:y2, x1:x2] = roi_mask
        return full_mask

    def _verify_color_in_roi(self, frame, bbox, target_color_name, detection_confidence):
        x1, y1, x2, y2 = bbox
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None, None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        lower_bound, upper_bound = HSV_BOUNDS.get(target_color_name, ((0, 0, 0), (0, 0, 0)))
        lower_bound = np.array(lower_bound, dtype=np.uint8)
        upper_bound = np.array(upper_bound, dtype=np.uint8)

        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)

        roi_area = float(roi.shape[0] * roi.shape[1])
        if roi_area <= 0:
            return None, None

        mask_ratio = cv2.countNonZero(mask) / roi_area
        if mask_ratio < COLOR_MASK_MIN_RATIO:
            return None, None

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None

        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        if area <= 500:
            return None, None

        contour_x, contour_y, contour_w, contour_h = cv2.boundingRect(largest_contour)
        contour_area_ratio = area / roi_area
        combined_score = (0.6 * detection_confidence) + (0.3 * mask_ratio) + (0.1 * min(1.0, contour_area_ratio))

        if combined_score < COLOR_COMBINED_SCORE_THRESHOLD:
            return None, None

        center_x = x1 + contour_x + contour_w // 2
        center_y = y1 + contour_y + contour_h // 2
        distance_cm = (REAL_BALLOON_WIDTH_CM * FOCAL_LENGTH_PX) / max(contour_w, 1)

        target_info = {
            'x': center_x,
            'y': center_y,
            'w': contour_w,
            'h': contour_h,
            'distance_cm': distance_cm,
            'area': area,
            'yolo_confidence': detection_confidence,
            'color_score': mask_ratio,
            'combined_score': combined_score,
            'source': 'yolo_roi',
            'bbox': (x1, y1, x2, y2),
        }

        full_mask = self._build_mask_from_roi(frame.shape, bbox, mask)
        return full_mask, target_info

    def process_frame(self, frame, target_color_name):
        if self.detector and self.detector.enabled:
            detections = self.detector.detect(frame)
            best_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            best_target = None

            for detection in detections:
                mask, target_info = self._verify_color_in_roi(
                    frame,
                    detection['bbox'],
                    target_color_name,
                    detection['confidence'],
                )
                if target_info is None:
                    continue

                if best_target is None or target_info['combined_score'] > best_target['combined_score']:
                    best_target = target_info
                    best_mask = mask

            if best_target is not None:
                return best_mask, best_target

            return np.zeros(frame.shape[:2], dtype=np.uint8), None

        return np.zeros(frame.shape[:2], dtype=np.uint8), None

    def cleanup(self):
        self.camera.close()
