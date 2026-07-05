# Vulkan Computer Vision

This repository contains two standalone computer-vision tasks that share the same camera layer but stay separate in code, configuration, and runtime entry points:

1. A balloon rover pipeline that detects balloons in the sequence BLACK → WHITE → PINK → YELLOW → BLUE, verifies color with HSV, estimates distance, and emits action messages.
2. An object-detection pipeline that recognizes hammer, traffic cone, and tennis ball targets.

The balloon task remains the original autonomous competition flow. The object task is a simpler detector that focuses on object presence and class recognition.

## Project Overview

The balloon runtime is a two-stage detector:

1. YOLO11 / ONNX finds candidate balloon regions in the frame.
2. OpenCV HSV plus contour checks verifies the target color only inside each YOLO ROI.

That means the balloon pipeline does not scan the full frame with HSV alone. If the model does not propose a balloon region, the frame is treated as having no valid target.

The object-detection runtime is simpler:

1. Capture a frame from the webcam.
2. Run the object detector model.
3. Parse detections above threshold.
4. Draw boxes and labels on the frame.
5. Log the detections for debugging.

## Repository Layout

- `src/balloon_task/main.py`: balloon state machine, frame loop, hold timer, and action output
- `src/balloon_task/vision.py`: YOLO candidate detection, ROI color verification, and distance estimation
- `src/balloon_task/config.py`: balloon HSV bounds, camera settings, model path, and thresholds
- `src/balloon_task/telemetry.py`: balloon-task CSV logging for debugging
- `src/object_task/main.py`: standalone object-detection entry point
- `src/object_task/vision.py`: object detector, class mapping, and frame postprocessing
- `src/object_task/config.py`: object model path, class labels, and thresholds
- `src/object_task/telemetry.py`: object-task logging for debugging
- `src/shared/camera.py`: shared webcam helper used by both tasks
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

### 3. Put the model files in the expected locations

The repository expects these ONNX exports:

```bash
Ballon_Detection_Weights/best.onnx
Hammer_Tennisball_Trafficcone_Weights/best.onnx
```

If you want to use different paths, set the corresponding environment variables before launch.

## How to Run

### Balloon task

Development mode with a laptop webcam:

```bash
CAMERA_INDEX=0 python -m src.balloon_task.main
```

Deployment mode with the rover USB camera:

```bash
CAMERA_INDEX=1 python -m src.balloon_task.main
```

### Object-detection task

Run the object detector with the same camera setup:

```bash
CAMERA_INDEX=0 python -m src.object_task.main
```

If needed, set `OBJECT_MODEL_PATH`, `OBJECT_CONF_THRESHOLD`, `OBJECT_IOU_THRESHOLD`, or `OBJECT_INPUT_SIZE` in the environment before launch.

## Balloon Task Details

The balloon pipeline detects target regions, verifies color, and estimates distance from the bounding-box width.

### Why HSV is used

HSV separates color from brightness, which makes the color check more robust under changing lighting.

- Hue describes the actual color.
- Saturation describes color strength.
- Value describes brightness.

After YOLO finds a candidate balloon region, the code:

1. crops the region of interest
2. converts the crop from BGR to HSV
3. applies the target color bounds from `src/balloon_task/config.py`
4. creates a binary mask
5. cleans the mask with erosion and dilation
6. checks the resulting contour to confirm a valid balloon region

### Calibration

There are two calibration steps in the balloon workflow.

HSV color calibration:

```bash
python -m tools.calibrate
```

Use this to tune the target color bounds for the current lighting and camera.
The tool opens three windows: the live camera feed, the binary HSV mask, and the masked result. You move the HSV trackbars until the target balloon stays white in the mask while the background stays black. When it looks right, press `q` and copy the printed lower and upper HSV bounds into `src/balloon_task/config.py`.

Focal length calibration:

```bash
python -m tools.calibrate_focal
```

Use this to improve the distance estimate in the pinhole camera model. The tool asks you to place a balloon about 1 meter from the camera, then draw a box around the balloon width with the ROI selector. It uses the pinhole equation $F = (P \times D) / W$ to compute the focal length in pixels, where $P$ is the measured pixel width, $D$ is the known distance, and $W$ is the real balloon width from the config. Copy the printed value into `src/balloon_task/config.py`.

In practice, this means:

1. HSV calibration is for color filtering.
2. Focal-length calibration is for distance estimation.
3. Both should be redone if you change cameras or lighting significantly.

The object-detection task does not need HSV or focal-length calibration unless you later add a similar size- or color-based filter.

### Autonomous behavior

`src/balloon_task/main.py` advances through the target sequence only when:

- the correct balloon color is detected
- the estimated distance is at or below 1.5 m
- the rover holds position for 5 seconds

Instead of sending motor commands directly, the script prints JSON-style action messages to stdout. That keeps the vision stack decoupled from the motor-control stack.

## Object-Detection Task Details

The object task is a separate pipeline that focuses on class recognition rather than HSV color verification.

It should:

1. Read frames from the shared webcam abstraction.
2. Load the `Hammer_Tennisball_Trafficcone_Weights` model.
3. Detect hammer, traffic cone, and tennis ball in real scenes.
4. Draw detections and labels on the frame.
5. Log detections and confidence scores for debugging.

The class labels are defined in `src/object_task/config.py`. If object names appear swapped in the UI, the first thing to check is the label order versus the model's class index order.

## Telemetry

Each task writes its own CSV log under `logs/`.

- Balloon telemetry tracks the target color, distance estimate, FSM state, and emitted action.
- Object telemetry tracks the detected label, confidence, bounding box, and frame latency.

This separation keeps the debugging output clean and lets the two tasks evolve independently.

## Model Handling

Both model folders should stay local and be ignored by Git.

- `Ballon_Detection_Weights/best.onnx`
- `Hammer_Tennisball_Trafficcone_Weights/best.onnx`

The `.pt` files are useful for retraining, but the runtime should use the ONNX exports.

## Why the Split Matters

Keeping the two tasks separate makes the project easier to maintain.

- clearer debugging
- easier model switching
- cleaner documentation
- independent calibration paths
- less risk of one task breaking the other

## Git and Generated Files

The repository ignores model artifacts and generated logs. Keep the weight files local or distribute them through a release artifact instead of committing them to Git.

## Troubleshooting

### Camera does not open

If the preview window never appears or the script exits early, check:

- that `CAMERA_INDEX` points to the correct device
- that no other app is already using the webcam
- that the shared camera helper can read frames on your system

### Model file is missing

If the detector logs that the model file was not found, verify these paths exist:

- `Ballon_Detection_Weights/best.onnx`
- `Hammer_Tennisball_Trafficcone_Weights/best.onnx`

You can also point the runtime at a different file by setting the matching environment variable before launch.

### Import or runtime errors

If Python cannot import `cv2` or `onnxruntime`, reinstall the dependencies with:

```bash
pip install -r requirements.txt
```

### Swapped object labels

If hammer and traffic cone appear swapped, the most likely cause is class-index order in the exported model versus the hardcoded labels in `src/object_task/config.py`. Check that the ONNX export uses the same class ordering as the runtime label list.

### Calibration results look wrong

If HSV calibration is not isolating the balloon cleanly, retune the trackbars under the current lighting and camera exposure. If distance estimates look off, rerun the focal-length calibration with the balloon measured at the correct real-world distance.
