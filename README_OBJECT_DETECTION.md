# Object Detection Task Architecture

This document outlines how to add a second standalone computer vision task to the same repository.

The first task remains the balloon pipeline:

- balloon presence detection
- balloon color verification with HSV
- distance estimation and sequence handling

The second task is a separate object detection pipeline for:

- hammer
- traffic cone
- tennis ball

Both tasks should share the same camera hardware but remain isolated in code, configuration, and runtime entry points.

## Design goals

1. Keep the balloon task fully independent from the object detection task.
2. Allow both tasks to use the rover webcam without duplicating camera code.
3. Keep model files and thresholds separate.
4. Make it obvious which script runs which task.
5. Allow future expansion without rewriting the shared camera layer.
6. Keep telemetry separate so the balloon task and object-detection task can use different logging formats.

## Recommended folder structure

A clean split would look like this:

```text
Vulkan_Computer_Vision_Tasks/
├── README.md
├── README_OBJECT_DETECTION.md
├── .gitignore
├── requirements.txt
├── Ballon_Detection_Weights/
├── Hammer_Tennisball_Trafficcone_Weights/
├── logs/
└── src/
    ├── shared/
    │   ├── camera.py
    │   └── config_common.py
    ├── balloon_task/
    │   ├── config.py
    │   ├── telemetry.py
    │   ├── vision.py
    │   └── main.py
    └── object_task/
        ├── config.py
        ├── telemetry.py
        ├── vision.py
        └── main.py
```

## What each task would do

### Balloon task

The balloon task stays focused on the competition flow already in the repo:

- detect whether a balloon is present
- verify its color with HSV
- estimate distance from balloon size
- advance through the fixed color sequence
- emit clean action output for the motion controller

This task should continue using:

- `Ballon_Detection_Weights/best.onnx`
- the current HSV calibration workflow
- the current telemetry output format

### Object detection task

The object detection task should be a separate pipeline that only cares about object presence and class recognition.

It should:

- read frames from the same webcam abstraction
- load the `Hammer_Tennisball_Trafficcone_Weights` model
- detect hammer, traffic cone, and tennis ball in real scenes
- draw detections and labels on the frame
- optionally log detections and confidence scores

This task does not need HSV color verification unless you later want a secondary filter.

## Shared components

Some logic should be shared rather than duplicated:

### 1. Camera access

Create one shared camera module, for example `src/shared/camera.py`.

That module should:

- open the webcam
- retry if the camera is unavailable
- standardize resolution and frame reads
- provide a single interface used by both tasks

### 2. Telemetry

Use separate telemetry modules for each task so logging can evolve independently:

- `src/balloon_task/telemetry.py`
- `src/object_task/telemetry.py`

This lets the balloon task keep its current CSV-style frame records while the object-detection task can use a different schema later if needed.

At minimum, each logger can still record:

- timestamp
- task name
- model name
- detection confidence
- target label
- frame latency
- any task-specific metadata

### 3. Common config

Create a shared config file for items both tasks need:

- camera index
- frame size
- log directory
- device settings
- environment variable parsing

Each task then keeps its own model path and detection thresholds.

## Runtime entry points

The cleanest approach is to give each task its own launch script or module entry point.

For example:

```bash
python -m src.balloon_task.main
python -m src.object_task.main
```

That makes each task standalone and prevents one pipeline from accidentally depending on the other's model or configuration.

## Model handling

Both model folders should stay local and be ignored by Git.

Expected deployment paths:

- `Ballon_Detection_Weights/best.onnx`
- `Hammer_Tennisball_Trafficcone_Weights/best.onnx`

If you later export different formats, keep them isolated by task so they do not overwrite each other.

## Object detection pipeline proposal

For the hammer/traffic-cone/tennis-ball task, the vision flow should be simpler than the balloon task:

1. Capture a frame from the webcam.
2. Run the object detector model.
3. Parse all detections above threshold.
4. Draw boxes and labels on the frame.
5. Log the detections for debugging.
6. Return the detection results to the caller or display them live.

No HSV verification is required unless you choose to add an extra validation layer later.

## Why this split is important

If both tasks stay in one flat script, the code will become harder to maintain.

Separating them into standalone modules gives you:

- clearer debugging
- easier model switching
- cleaner documentation
- independent calibration paths
- less risk of one task breaking the other

## Recommended development order

1. Keep the balloon task working exactly as it is now.
2. Add the shared camera module.
3. Add the shared telemetry module.
4. Create the object detection task entry point.
5. Point it at `Hammer_Tennisball_Trafficcone_Weights`.
6. Test each task independently.
7. Only after both work, refine any shared utilities.

## Summary

The best structure is to treat the repository as a small multi-task computer vision workspace:

- one standalone balloon-color task
- one standalone object-detection task
- one shared camera layer
- separate telemetry layers for each task
- separate model folders and separate runtime entry points

That keeps the tasks independent while still letting them live in the same project.
