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

# Control limits
CENTER_TOLERANCE_PX = 50 # Tolerance to consider the balloon centered
