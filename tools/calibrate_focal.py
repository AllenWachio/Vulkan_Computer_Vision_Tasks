import cv2
import numpy as np
import logging
from src.config import CAMERA_INDEX, REAL_BALLOON_WIDTH_CM

logger = logging.getLogger("CalibrateFocal")
logging.basicConfig(level=logging.INFO, format='%(message)s')

def calibrate_focal_length():
    """
    Calculates exact focal length in pixels using the Pinhole Camera Model.
    Equation: F = (Pixel_Width * Known_Distance) / Real_Width
    """
    KNOWN_DISTANCE_CM = 100.0  # Put the balloon exactly 1 meter away

    logger.info("=== FOCAL LENGTH CALIBRATION ===")
    logger.info(f"1. Place a balloon exactly {KNOWN_DISTANCE_CM}cm (1.0m) away from the camera.")
    logger.info("2. Select a colored object you have already tuned HSV for, or just hold the balloon up to clear background.")
    logger.info("3. Click and drag a bounding box around the width of the balloon on the camera feed.")
    logger.info("4. Press ENTER to confirm, or 'c' to cancel/redraw.")
    logger.info("================================")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        logger.error("Failed to open camera.")
        return

    ret, frame = cap.read()
    if not ret:
        logger.error("Failed to read frame.")
        return

    # Let the user select the ROI (Region of Interest)
    # The cv2.selectROI will pause execution and let the user draw a box
    logger.info("A window will open. Click and drag a box around the edges of the balloon, then press SPACE or ENTER.")
    bbox = cv2.selectROI("Select Balloon Width", frame, fromCenter=False, showCrosshair=True)
    
    cv2.destroyWindow("Select Balloon Width")
    cap.release()

    x, y, w, h = bbox
    if w <= 0:
        logger.error("Invalid selection. Exiting.")
        return

    pixel_width = w
    
    # Calculate focal length
    # F = (P * D) / W
    focal_length = (pixel_width * KNOWN_DISTANCE_CM) / REAL_BALLOON_WIDTH_CM

    logger.info(f"\n--- CALIBRATION RESULTS ---")
    logger.info(f"Real Balloon Width: {REAL_BALLOON_WIDTH_CM} cm")
    logger.info(f"Known Distance    : {KNOWN_DISTANCE_CM} cm")
    logger.info(f"Measured Px Width : {pixel_width} px")
    logger.info(f"---------------------------")
    logger.info(f"==> FOCAL_LENGTH_PX = {focal_length:.1f} <==")
    logger.info(f"---------------------------")
    logger.info(f"ACTION: Copy this value and replace FOCAL_LENGTH_PX in 'src/config.py'.")

if __name__ == "__main__":
    calibrate_focal_length()
