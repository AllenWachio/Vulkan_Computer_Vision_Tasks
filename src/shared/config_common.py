import os

CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 0))
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", 640))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", 480))
LOG_DIR = os.environ.get("LOG_DIR", "logs")
