# Autonomous Balloon Rover

Provides autonomous vision tracking using OpenCV. The rover tracks the balloons in this sequence: BLACK → WHITE → PINK → YELLOW → BLUE.

## Setup Instructions

### 1. Create and Activate Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Usage

**Calibrating Colors:**
Every lighting environment is different. To find the exact HSV bounds for your balloons:

```bash
python -m src.calibrate
```

Adjust the sliders until the balloon is bright white on the mask and everything else is black. Press `q` to quit and print the values. Update `src/config.py` with these printed thresholds.

**Running in Development Mode (Laptop Webcam):**

```bash
CAMERA_INDEX=0 python -m src.main
```

**Running in Deployment Mode (Rover USB Camera):**
Connect the USB camera. Often, external USB cameras mount at index 1 or 2.

```bash
CAMERA_INDEX=1 python -m src.main
```

## Hardware Integration Notes

Open `src/rover.py`. The `RoverMockAPI` class contains stub methods (`drive_forward`, `spin_left`, `spin_right`, `stop`). Replace the logging statements in these methods with your actual hardware SDK or ROS Twist publisher logic to make the physical chassis response to the CV outputs.
