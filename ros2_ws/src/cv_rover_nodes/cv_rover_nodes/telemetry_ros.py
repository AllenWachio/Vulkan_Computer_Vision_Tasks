import csv
import os
import time
from datetime import datetime

def _get_root_logs_dir():
    """
    Dynamically calculates the absolute path to the root 'logs' directory.
    This ensures logs are saved in the project root, regardless of where 
    the 'ros2 launch' command is executed from.
    """
    # Get the directory where this telemetry file lives
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate up 4 levels: cv_rover_nodes -> cv_rover_nodes -> src -> ros2_ws -> PROJECT ROOT
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
    return os.path.join(project_root, "logs")

class BalloonTelemetry:
    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = _get_root_logs_dir()
            
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(log_dir, f"ros_balloon_session_{timestamp}.csv")
        self.file = open(self.filename, mode="w", newline="")
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            "timestamp_iso", "uptime_sec", "target_color", "is_detected",
            "distance_cm", "center_error_px", "fsm_state", "output_action",
            "yolo_confidence", "color_score", "combined_score"
        ])
        self.start_time = time.time()

    def log_step(self, target_color, is_detected, distance, error, fsm_state, action, 
                 yolo_confidence=None, color_score=None, combined_score=None):
        now = datetime.now().isoformat()
        uptime = round(time.time() - self.start_time, 3)
        
        dist_val = round(distance, 2) if distance is not None else ""
        err_val = round(error, 2) if error is not None else ""
        yolo_val = round(yolo_confidence, 4) if yolo_confidence is not None else ""
        color_val = round(color_score, 4) if color_score is not None else ""
        combined_val = round(combined_score, 4) if combined_score is not None else ""

        self.writer.writerow([
            now, uptime, target_color, is_detected, dist_val, err_val, 
            fsm_state, action, yolo_val, color_val, combined_val
        ])
        self.file.flush()

    def cleanup(self):
        if not self.file.closed:
            self.file.close()

class ObjectTelemetry:
    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = _get_root_logs_dir()
            
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(log_dir, f"ros_object_session_{timestamp}.csv")
        self.file = open(self.filename, mode="w", newline="")
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            "timestamp_iso", "uptime_sec", "frame_index", "object_label",
            "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "latency_ms"
        ])
        self.start_time = time.time()
        self.frame_index = 0

    def log_frame(self, detections, latency_ms):
        now = datetime.now().isoformat()
        uptime = round(time.time() - self.start_time, 3)
        self.frame_index += 1

        # Match your exact logic: write an empty row if no detections
        if not detections:
            self.writer.writerow([
                now, uptime, self.frame_index, "", "", "", "", "", "", round(latency_ms, 3)
            ])
            self.file.flush()
            return

        # Write one row per detection
        for detection in detections:
            bbox = detection.get("bbox", ("", "", "", ""))
            self.writer.writerow([
                now, uptime, self.frame_index,
                detection.get("label", ""),
                round(detection.get("confidence", 0.0), 4),
                bbox[0], bbox[1], bbox[2], bbox[3],
                round(latency_ms, 3)
            ])
        self.file.flush()

    def cleanup(self):
        if not self.file.closed:
            self.file.close()