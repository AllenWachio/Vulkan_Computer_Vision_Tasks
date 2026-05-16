import cv2
import numpy as np
from src.config import CAMERA_INDEX

def nothing(x):
    pass

def calibrate_camera():
    """
    A simple UI tool to adjust HSV bounds.
    """
    cv2.namedWindow('Calibration')
    cv2.createTrackbar('H Min', 'Calibration', 0, 179, nothing)
    cv2.createTrackbar('S Min', 'Calibration', 0, 255, nothing)
    cv2.createTrackbar('V Min', 'Calibration', 0, 255, nothing)
    cv2.createTrackbar('H Max', 'Calibration', 179, 179, nothing)
    cv2.createTrackbar('S Max', 'Calibration', 255, 255, nothing)
    cv2.createTrackbar('V Max', 'Calibration', 255, 255, nothing)

    cap = cv2.VideoCapture(CAMERA_INDEX)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        h_min = cv2.getTrackbarPos('H Min', 'Calibration')
        s_min = cv2.getTrackbarPos('S Min', 'Calibration')
        v_min = cv2.getTrackbarPos('V Min', 'Calibration')
        h_max = cv2.getTrackbarPos('H Max', 'Calibration')
        s_max = cv2.getTrackbarPos('S Max', 'Calibration')
        v_max = cv2.getTrackbarPos('V Max', 'Calibration')

        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])

        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(frame, frame, mask=mask)

        cv2.imshow('Original', frame)
        cv2.imshow('Mask', mask)
        cv2.imshow('Calibration', result)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print(f"Final Bounds: Lower: {lower.tolist()} | Upper: {upper.tolist()}")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    calibrate_camera()
