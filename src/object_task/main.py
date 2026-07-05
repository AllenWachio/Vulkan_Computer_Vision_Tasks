import logging
import time

import cv2

from src.object_task.telemetry import TelemetryLogger
from src.object_task.vision import ObjectVisionSystem
from src.shared.camera import SharedCamera
from src.shared.config_common import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("OBJECT_NODE")


def main():
    camera = SharedCamera(camera_index=CAMERA_INDEX, width=CAMERA_WIDTH, height=CAMERA_HEIGHT)
    vision = ObjectVisionSystem()
    telemetry = TelemetryLogger()

    if not camera.open():
        logger.error("SYSTEM_FAILURE: Could not start camera.")
        return

    logger.info("SYSTEM_START: Object detection task ready.")
    logger.info("TELEMETRY: Logging session data to %s", telemetry.filename)

    try:
        while True:
            start_time = time.time()
            ret, frame = camera.read()
            if not ret:
                logger.warning("WARN: Frame read failed")
                time.sleep(0.1)
                continue

            detections = vision.process_frame(frame)
            latency_ms = (time.time() - start_time) * 1000.0
            telemetry.log_frame(detections, latency_ms)

            debug_frame = frame.copy()
            for detection in detections:
                x1, y1, x2, y2 = detection["bbox"]
                label = detection["label"]
                confidence = detection["confidence"]
                cv2.rectangle(debug_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    debug_frame,
                    f"{label}: {confidence:.2f}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

            if not detections:
                cv2.putText(
                    debug_frame,
                    "No objects detected",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow("Object Detection Task", debug_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("SYSTEM_SHUTDOWN: Manual quit")
                break

    except KeyboardInterrupt:
        logger.info("SYSTEM_SHUTDOWN: Keyboard interrupt")
    finally:
        camera.close()
        telemetry.cleanup()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
