import os

OBJECT_MODEL_PATH = os.environ.get(
    "OBJECT_MODEL_PATH",
    "Hammer_Tennisball_Trafficcone_Weights/best.onnx",
)
OBJECT_CONF_THRESHOLD = float(os.environ.get("OBJECT_CONF_THRESHOLD", "0.35"))
OBJECT_IOU_THRESHOLD = float(os.environ.get("OBJECT_IOU_THRESHOLD", "0.45"))
OBJECT_INPUT_SIZE = int(os.environ.get("OBJECT_INPUT_SIZE", "640"))
OBJECT_ENABLED = os.environ.get("OBJECT_ENABLED", "1") != "0"
OBJECT_LABELS = ["Hammer", "Traffic Cone", "Tennis Ball"]
