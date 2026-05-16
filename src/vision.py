import cv2
import numpy as np
import logging
from src.config import HSV_BOUNDS, REAL_BALLOON_WIDTH_CM, FOCAL_LENGTH_PX

logger = logging.getLogger(__name__)

class VisionSystem:
    def __init__(self, camera_index=0, width=640, height=480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None

    def initialize(self, retries=3):
        for i in range(retries):
            logger.info(f"Attempting to initialize camera {self.camera_index} (try {i+1}/{retries})")
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                logger.info("Camera initialized successfully.")
                return True
            import time
            time.sleep(1)
        
        logger.error(f"Failed to initialize camera at index {self.camera_index}")
        return False

    def read_frame(self):
        if not self.cap or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def process_frame(self, frame, target_color_name):
        """
        Process the frame to find the target balloon color.
        Uses morphological operations to clean noise.
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        lower_bound, upper_bound = HSV_BOUNDS.get(target_color_name, ((0,0,0), (0,0,0)))
        lower_bound = np.array(lower_bound, dtype=np.uint8)
        upper_bound = np.array(upper_bound, dtype=np.uint8)

        # Create mask
        mask = cv2.inRange(hsv, lower_bound, upper_bound)

        # Morphological operations to remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        target_info = None
        if contours:
            # Find the largest contour as the balloon candidate
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)

            if area > 500: # Minimum area threshold
                x, y, w, h = cv2.boundingRect(largest_contour)
                cx, cy = x + w // 2, y + h // 2
                
                # Distance estimation (pinhole model approximation)
                # D = (W * F) / P
                distance_cm = (REAL_BALLOON_WIDTH_CM * FOCAL_LENGTH_PX) / w
                
                target_info = {
                    'x': cx,
                    'y': cy,
                    'w': w,
                    'h': h,
                    'distance_cm': distance_cm,
                    'area': area
                }

        return mask, target_info

    def cleanup(self):
        if self.cap:
            self.cap.release()
