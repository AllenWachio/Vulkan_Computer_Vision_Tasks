# Autonomous Balloon Rover

This project is a vision pipeline for an autonomous rover that detects balloons in the sequence BLACK → WHITE → PINK → YELLOW → BLUE, verifies the color with HSV, estimates distance, and emits clean action messages for a separate motion controller.

For the second standalone computer vision task that detects hammer, traffic cone, and tennis ball objects, see [README_OBJECT_DETECTION.md](README_OBJECT_DETECTION.md).

## What the system does

The current runtime is a two-stage detector:

1. **YOLO11 / ONNX** finds candidate balloon regions in the frame.
2. **OpenCV HSV + contour checks** verifies the target color only inside each YOLO ROI.

That means the system does **not** scan the entire frame with HSV alone during autonomous mode. If the model does not propose a balloon region, the frame is treated as having no valid target.

## Repository layout

- `src/balloon_task/main.py`: balloon state machine, frame loop, hold timer, and action output
- `src/balloon_task/vision.py`: YOLO candidate detection, ROI color verification, and distance estimation
- `src/balloon_task/config.py`: balloon HSV bounds, camera settings, model path, and thresholds
- `src/balloon_task/telemetry.py`: balloon-task CSV logging for debugging
- `src/object_task/main.py`: standalone object-detection entry point
- `src/shared/camera.py`: shared webcam helper
- `src/object_task/telemetry.py`: object-task logging for debugging
- `tools/calibrate.py`: interactive HSV calibration helper
- `tools/calibrate_focal.py`: focal length calibration helper

## Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Put the model in the expected location

The runtime expects the ONNX export of your trained balloon detector at:

```bash
Ballon_Detection_Weights/best.onnx
```

If you want to use a different path, set `YOLO_MODEL_PATH` in the environment before launch.

## How to run

### Development mode with a laptop webcam

```bash
CAMERA_INDEX=0 python -m src.balloon_task.main
```

### Deployment mode with the rover USB camera

```bash
CAMERA_INDEX=1 python -m src.balloon_task.main
```

### Color calibration

Use this when tuning HSV bounds for the current lighting:

```bash
python -m tools.calibrate
```

### Focal length calibration

Use this to improve the 1.5 m distance estimate:

```bash
python -m tools.calibrate_focal
```

## How Calibration Works

There are two calibration steps in this project, and both matter for reliable detection.

### 1. HSV color calibration

This step tunes the color ranges used by the OpenCV detector.

Run:

```bash
python -m tools.calibrate
```

What happens during calibration:

1. The camera opens a live preview.
2. You adjust the HSV sliders until the target balloon is clearly isolated in the mask.
3. The goal is to make the balloon appear white in the mask and the background appear black.
4. When the mask looks correct, press `q` to print the final HSV bounds.
5. Copy those bounds into `src/balloon_task/config.py` if you need to replace the default values.

Why this matters:

- lighting changes can shift the apparent color of a balloon
- different cameras interpret color slightly differently
- a good calibration reduces false positives and missed detections

### 2. Focal length calibration

This step tunes the distance estimate used by the pinhole camera model.

Run:

```bash
python -m tools.calibrate_focal
```

What happens during calibration:

1. Place a balloon at a known distance, usually 100 cm from the camera.
2. Draw a box around the balloon in the preview window.
3. The script uses the known real-world balloon width and the measured pixel width to calculate `FOCAL_LENGTH_PX`.
4. Copy the printed focal length into `src/balloon_task/config.py`.

Why this matters:

- the stop distance depends on the accuracy of the focal length
- if the focal length is wrong, the rover may stop too early or too late
- calibrating on the actual camera improves consistency more than using a guessed value

## Why HSV Is Used

The project uses HSV instead of raw BGR or RGB because HSV separates color from brightness.

### What HSV means

- **Hue** describes the actual color, such as red, blue, or yellow
- **Saturation** describes how strong or pure the color is
- **Value** describes brightness

### Why that helps

Color detection in BGR is sensitive to lighting because all three channels mix color and brightness together. A shadow, glare, or exposure change can make the same balloon look very different in RGB/BGR space.

HSV is more stable for this task because:

1. the balloon color is mostly represented by Hue
2. brightness changes mostly affect the Value channel instead of the color identity
3. thresholds are easier to tune for specific target colors

### How HSV is used in this project

After YOLO finds a candidate balloon region, the code:

1. crops the region of interest
2. converts that crop from BGR to HSV
3. applies the target color bounds from `src/balloon_task/config.py`
4. creates a binary mask where matching pixels are white and everything else is black
5. cleans the mask with erosion and dilation
6. checks the resulting contour to make sure the object is large and valid enough to be treated as a balloon

This gives the system a two-stage filter:

- YOLO decides whether the object looks like a balloon
- HSV decides whether that balloon is the correct color

That combination is much more reliable than trying to use color alone.

## Detection pipeline

The core color logic in `src/balloon_task/vision.py` works like this:

1. The camera frame is captured in BGR.
2. YOLO11 proposes balloon candidate bounding boxes.
3. The code crops each YOLO box to an ROI.
4. The ROI is converted to HSV.
5. The target color bounds from `src/balloon_task/config.py` are applied.
6. Morphological operations remove noise.
7. Contours are used to confirm a strong object region.
8. The balloon width is used in the pinhole approximation:

```text
Distance = (Real Balloon Width × Focal Length) / Pixel Width
```

## Autonomous behavior

`src/balloon_task/main.py` tracks the target sequence and only advances when:

- the correct balloon color is detected
- the estimated distance is at or below 1.5 m
- the rover holds position for 5 seconds

Instead of sending motor commands directly, the script prints JSON-style action messages to stdout. This keeps the vision stack decoupled from the motor-control stack.

Example output:

```json
OUTPUT: {"action": "SPIN_RIGHT", "error_px": 125}
OUTPUT: {"action": "DRIVE_FORWARD", "distance_cm": 240.2}
OUTPUT: {"action": "STOP", "reason": "target_reached", "distance_cm": 149.0}
```

## Telemetry

Each run creates a new CSV file in `logs/` with timestamped frame records. The log includes:

- timestamp
- uptime
- target color
- detection flag
- distance estimate
- center error
- FSM state
- emitted action

This is useful for debugging false detections, distance tuning, and camera/model issues.

## Edge-device notes

The trained model is intended for deployment as ONNX rather than running PyTorch directly at runtime. Keep the original `.pt` files for retraining only, and deploy the `.onnx` export on edge hardware.

Recommended runtime behavior:

- use the ONNX model on the device
- keep batch size at 1
- keep the camera resolution modest
- use telemetry to watch inference time and false positives

## Git and model files

The repository ignores model artifacts and generated logs. Keep the weight files local or distribute them through a release artifact instead of committing them to Git.
