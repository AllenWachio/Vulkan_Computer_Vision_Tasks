import cv2
import time
import logging
from src.config import TARGET_SEQUENCE, TARGET_DISTANCE_CM, HOLD_TIME_SEC, CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CENTER_TOLERANCE_PX
from src.rover import RoverMockAPI
from src.vision import VisionSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StateMachine:
    def __init__(self):
        self.sequence = TARGET_SEQUENCE
        self.current_idx = 0
        self.holding = False
        self.hold_start_time = 0

    def current_target(self):
        if self.current_idx < len(self.sequence):
            return self.sequence[self.current_idx]
        return None

    def advance(self):
        self.current_idx += 1
        self.holding = False
        if self.current_target():
            logger.info(f"Advancing state. New target: {self.current_target()}")
        else:
            logger.info("All targets reached! Sequence complete.")

def main():
    rover = RoverMockAPI()
    vision = VisionSystem(camera_index=CAMERA_INDEX, width=CAMERA_WIDTH, height=CAMERA_HEIGHT)
    state = StateMachine()

    if not vision.initialize():
        logger.error("Exiting due to camera failure.")
        return

    logger.info(f"Starting mission. First target: {state.current_target()}")

    try:
        while True:
            target_color = state.current_target()
            if not target_color:
                rover.stop()
                break # Mission complete

            ret, frame = vision.read_frame()
            if not ret:
                logger.warning("Frame read failed.")
                time.sleep(0.1)
                continue

            frame_center_x = CAMERA_WIDTH // 2
            
            # Process vision
            mask, target_info = vision.process_frame(frame, target_color)

            # Draw UI on debug frame
            debug_frame = frame.copy()
            cv2.putText(debug_frame, f"Target: {target_color}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if target_info:
                distance = target_info['distance_cm']
                cx = target_info['x']
                
                # Draw bounding box
                x, y = cx - target_info['w']//2, target_info['y'] - target_info['h']//2
                cv2.rectangle(debug_frame, (x, y), (x + target_info['w'], y + target_info['h']), (255, 0, 0), 2)
                cv2.putText(debug_frame, f"Dist: {int(distance)}cm", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

                if state.holding:
                    elapsed = time.time() - state.hold_start_time
                    cv2.putText(debug_frame, f"HOLDING: {elapsed:.1f}s", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    if elapsed >= HOLD_TIME_SEC:
                        state.advance()
                else:
                    # Navigation Logic
                    if distance <= TARGET_DISTANCE_CM:
                        rover.stop()
                        logger.info(f"Target {target_color} reached at {distance:.1f} cm. Stopping for {HOLD_TIME_SEC} seconds.")
                        state.holding = True
                        state.hold_start_time = time.time()
                    else:
                        # Simple alignment (proportional control mock)
                        error_x = cx - frame_center_x
                        if abs(error_x) > CENTER_TOLERANCE_PX:
                            if error_x > 0:
                                rover.spin_right()
                            else:
                                rover.spin_left()
                        else:
                            rover.drive_forward()
            else:
                # No target found
                if not state.holding:
                    rover.spin_left() # Search behavior
                    cv2.putText(debug_frame, "SEARCHING...", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

            # Show windows
            cv2.imshow("Rover View", debug_frame)
            cv2.imshow("Mask View", mask)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("Manual shutdown triggered.")
                break

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt.")
    finally:
        rover.stop()
        vision.cleanup()
        cv2.destroyAllWindows()
        logger.info("Shutdown complete.")

if __name__ == '__main__':
    main()
