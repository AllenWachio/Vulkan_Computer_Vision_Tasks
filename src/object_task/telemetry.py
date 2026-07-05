import csv
import os
import time
from datetime import datetime


class TelemetryLogger:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(log_dir, f"object_session_{timestamp}.csv")

        self.file = open(self.filename, mode="w", newline="")
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            "timestamp_iso",
            "uptime_sec",
            "frame_index",
            "object_label",
            "confidence",
            "bbox_x1",
            "bbox_y1",
            "bbox_x2",
            "bbox_y2",
            "latency_ms",
        ])
        self.start_time = time.time()
        self.frame_index = 0

    def log_frame(self, detections, latency_ms):
        now = datetime.now().isoformat()
        uptime = round(time.time() - self.start_time, 3)
        self.frame_index += 1

        if not detections:
            self.writer.writerow([
                now,
                uptime,
                self.frame_index,
                "",
                "",
                "",
                "",
                "",
                "",
                round(latency_ms, 3),
            ])
            self.file.flush()
            return

        for detection in detections:
            bbox = detection.get("bbox", ("", "", "", ""))
            self.writer.writerow([
                now,
                uptime,
                self.frame_index,
                detection.get("label", ""),
                round(detection.get("confidence", 0.0), 4),
                bbox[0],
                bbox[1],
                bbox[2],
                bbox[3],
                round(latency_ms, 3),
            ])

        self.file.flush()

    def cleanup(self):
        self.file.close()
