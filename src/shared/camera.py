import cv2
import logging
import time

logger = logging.getLogger(__name__)


class SharedCamera:
    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None

    def open(self, retries=3, retry_delay_sec=1.0):
        for attempt in range(retries):
            logger.info(
                "Attempting to initialize camera %s (try %s/%s)",
                self.camera_index,
                attempt + 1,
                retries,
            )
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                logger.info("Camera initialized successfully.")
                return True
            time.sleep(retry_delay_sec)

        logger.error("Failed to initialize camera at index %s", self.camera_index)
        return False

    def read(self):
        if not self.cap or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None
