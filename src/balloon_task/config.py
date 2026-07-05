import os

# Balloon Color Sequence
TARGET_SEQUENCE = ['BLACK', 'WHITE', 'PINK', 'YELLOW', 'BLUE']

# HSV Bounds (Lower, Upper) - Pre-tuned approximations, will need calibration for real environment
HSV_BOUNDS = {
    'BLACK': ((0, 0, 0), (180, 255, 60)),
    'WHITE': ((0, 0, 200), (180, 40, 255)),
    'PINK': ((145, 50, 50), (170, 255, 255)),
    'YELLOW': ((20, 100, 100), (40, 255, 255)),
    'BLUE': ((100, 100, 50), (130, 255, 255))
}

# Distance Estimation settings
# Distance = (RealWidth * FocalLength) / PixelWidth
REAL_BALLOON_WIDTH_CM = 30.0
# Approximate focal length in pixels (calibrate based on your camera)
FOCAL_LENGTH_PX = 600.0
TARGET_DISTANCE_CM = 150.0 # 1.5 meters
HOLD_TIME_SEC = 5.0 # Stop for 5 seconds

# Camera setup
# Set env var CAMERA_INDEX=1 for USB cam, default to 0 for laptop webcam
CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', 0))
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# YOLO11 balloon detector settings
# Runtime uses the ONNX export so the rover does not need PyTorch at inference time.
YOLO_MODEL_PATH = os.environ.get(
    'YOLO_MODEL_PATH',
    'Ballon_Detection_Weights/best.onnx'
)
YOLO_CONF_THRESHOLD = float(os.environ.get('YOLO_CONF_THRESHOLD', '0.35'))
YOLO_IOU_THRESHOLD = float(os.environ.get('YOLO_IOU_THRESHOLD', '0.45'))
YOLO_INPUT_SIZE = int(os.environ.get('YOLO_INPUT_SIZE', '640'))
YOLO_ENABLED = os.environ.get('YOLO_ENABLED', '1') != '0'

# ROI verification thresholds used after YOLO proposes a balloon candidate.
COLOR_MASK_MIN_RATIO = float(os.environ.get('COLOR_MASK_MIN_RATIO', '0.08'))
COLOR_COMBINED_SCORE_THRESHOLD = float(os.environ.get('COLOR_COMBINED_SCORE_THRESHOLD', '0.35'))

# Control limits
CENTER_TOLERANCE_PX = 50 # Tolerance to consider the balloon centered
