# Proposal: Multi-Target Visual Sequencing Architecture

## 1. The Challenge
Currently, the rover's architecture masks only the *active* target color and uses reactive control to approach it. If multiple balloons (Red, Green, Blue) are in the camera frame and the sequence requires reaching the furthest one (Red) before the closest ones (Blue, Green), the current reactive tracker faces two major issues:
1. **Blindness to Obstacles**: Masking only Red makes the rover blind to Blue and Green.
2. **Collision**: If Blue is directly in the path to Red, the rover will crash into Blue.

## 2. Using Balloon Size for Distance (Pure CV)
Yes, using the balloon's bounding box size is **the standard pure-CV approach** for monocular depth estimation when the object's real-world size is known. 
Since standard balloons are uniformly sized (e.g., ~30cm diameter), their apparent pixel width shrinks linearly as they move further away.
* **Mathematical Basis**: We use the Pinhole Camera Model equation:
  $$Distance = \frac{Real\_Width \times Focal\_Length}{Pixel\_Width}$$
* By tracking the `Pixel_Width` of Red, Green, and Blue, we can instantly sort them by distance in 3D space (`Z`-axis). For example, Blue (width = 150px) is closer than Green (width = 80px), which is closer than Red (width = 30px).

## 3. Proposed Software Architecture

To navigate to a far target while avoiding closer non-targets (while keeping purely to computer vision and no LiDAR/ultrasonic sensors), we must evolve the architecture from a simple reactive tracker to a **Local Semantic Map** with **Obstacle Avoidance**.

### A. Parallel Multi-Color Perception pipeline
Instead of providing one color to `process_frame`, the `VisionSystem` will evaluate all active masks simultaneously in a single frame. 
* **Output:** A list of detected entities:
  ```json
  [
    {"color": "blue", "distance": 1.2, "angle": 5.0, "bbox": [...]},
    {"color": "green", "distance": 3.4, "angle": -15.0, "bbox": [...]},
    {"color": "red", "distance": 6.8, "angle": 2.0, "bbox": [...]}
  ]
  ```

### B. Visual Bounding-Box Avoidance (The "Visual Bubble")
Since the terrain is flat, the camera maps linearly to a 2D floor plane. 
Any balloon that is **not** the current target must be temporarily classified as an **obstacle**.
* If the target is Red, the rover must steer towards Red's angle.
* It must project the bounding boxes of Green and Blue onto the "ground" and calculate if the rover's driving vector intersects them.

### C. Control Strategy: Artificial Potential Fields (APF)
To navigate smoothly without complex pathfinding algorithms (like A*), we can implement a highly efficient reactive control method called **Artificial Potential Fields**:
1. **Attraction**: The target (Red) generates an "attractive" force vector pulling the rover towards it.
2. **Repulsion**: The non-targets (Green and Blue) generate "repulsive" force vectors that push the rover away. Repulsion strength gets exponentially stronger as the rover gets closer to them.
3. **Resultant Vector**: By summing the attractive and repulsive vectors, the rover naturally calculates a sweeping, curved path that smoothly arcs *around* Blue and Green to arrive at Red.

## 4. Required Code Modifications
To implement this, the following changes would be made to the existing codebase:

1. **`src/vision.py`**:
   * Change `process_frame` to iterate over all sequences, perform masking, calculate distance, and return a dictionary of all visible balloons and their coordinates.
2. **`src/main.py`**:
   * Update the FSM. Instead of steering straight to $X_{error}$, calculate the repulsive forces from non-target balloons.
   * If a non-target balloon is within a "danger threshold" (e.g., distance < 2.0m and angle < 20 degrees), inject a lateral spin (right/left) to steer around it before continuing forward toward the main target.
3. **`src/config.py`**:
   * Add constants like `REPULSION_RADIUS` and `ATTRACTION_STRENGTH`.

## Update: Alignment with Official Competition Rules
**Note (June 2026):** According to the official competition statement: *"The terrain for this task will be flat and without any obstacles, so you do not need obstacle avoidance algorithms."*

Because of this explicit rule, **we can completely discard the Artificial Potential Fields (APF) and obstacle avoidance logic.** The original, simpler reactive software architecture (implemented in `src/main.py` and `src/vision.py`) is already 100% compliant with the rules to score maximum points. 

**How the current codebase satisfies the competition criteria:**
1. **Drive in correct order:** Handled by `StateMachine` iterating through `TARGET_SEQUENCE`.
2. **Stop for 5 seconds inside 1.5m:** Handled by `distance_cm <= 150.0` triggering the 5-second `HOLD_TIME_SEC` loop.
3. **No Obstacle Avoidance Needed:** We only threshold the *current* target color in the sequence and ignore others. If the rover bumps into a blue balloon while driving perfectly straight toward the black one, the rules imply this is acceptable (or the field is sparse enough that it won't happen).
4. **Partial Points for Logging/Display:** Even if the motors fail, you can score partial points because our script streams a debug window (`cv2.imshow`) overlaying bounding boxes, detected colors, and distances on the video feed.

**Conclusion:** Maintain the original Point-and-Shoot architecture! Do not add complex multi-balloon APF avoidance. Focus engineering time purely on tuning the HSV values on the field and refining the chassis motor control response.

## Summary
By using the geometric pixel width of the balloons, we can accurately synthesize a 2D map of the environment using pure computer vision. By treating out-of-sequence balloons as dynamic obstacles and applying an Artificial Potential Field, the rover can safely weave between the closer balloons (Blue, Green) to reach the target balloon (Red) first.