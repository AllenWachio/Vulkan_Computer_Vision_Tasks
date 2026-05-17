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

## How Color Detection Works

The core of the balloon color detection and tracking is located in `src/vision.py` within the `process_frame` method. Here is a step-by-step breakdown of the computer vision pipeline:

1. **Color Space Conversion**: The camera captures frames in the BGR (Blue, Green, Red) color space. The code converts this to the **HSV** (Hue, Saturation, Value) color space using `cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)`. HSV separates color/tint (Hue) from lighting intensity (Value), making it much more robust against shadows and changing lighting conditions than standard RGB.
2. **Thresholding (Masking)**: Using the pre-calibrated lower and upper bounds defined in `src/config.py`, `cv2.inRange()` creates a binary mask. It evaluates every pixel in the image: if a pixel's HSV values fall within the limits for the required color, it turns white on the mask. Everything else turns black.
3. **Morphological Noise Reduction**: Glare or background objects often cause tiny specks of false positives (noise). The code cleans the mask using **Erosion** (`cv2.erode()`) to strip away these tiny speckles, followed immediately by **Dilation** (`cv2.dilate()`) to restore the mass/size of the actual balloon region.
4. **Contour Extraction**: With a clean mask, the script finds the outer boundaries of the white blobs using `cv2.findContours()`.
5. **Distance & Target Selection**: It looks for the largest contour (by pixel area) and assumes this is the closest target balloon. It then wraps it in a bounding box (`cv2.boundingRect()`). The width of this bounding box is plugged into a simple Pinhole Camera approximation map (`Distance = (Real_Width * Focal_Length) / Pixel_Width`) to determine how far away the balloon is, allowing the rover to know when it has reached the 1.5-meter hold threshold.
