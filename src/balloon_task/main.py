import cv2
import time
import logging
import json

from src.balloon_task.config import TARGET_SEQUENCE, TARGET_DISTANCE_CM, HOLD_TIME_SEC, CENTER_TOLERANCE_PX
from src.balloon_task.telemetry import TelemetryLogger
from src.balloon_task.vision import VisionSystem
from src.shared.config_common import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("CV_NODE")


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
            logger.info(f"SEQUENCE_ADVANCE: Next Target -> {self.current_target()}")
        else:
            logger.info("SEQUENCE_COMPLETE: All targets reached!")


def emit_command(action, details=None):
    payload = {"action": action}
    if details:
        payload.update(details)
    logger.info(f"OUTPUT: {json.dumps(payload)}")
    return action


def main():
    vision = VisionSystem(camera_index=CAMERA_INDEX, width=CAMERA_WIDTH, height=CAMERA_HEIGHT)
    state = StateMachine()
    telemetry = TelemetryLogger()

    if not vision.initialize():
        logger.error("SYSTEM_FAILURE: Could not start camera.")
        return

    logger.info(f"SYSTEM_START: First target -> {state.current_target()}")
    logger.info(f"TELEMETRY: Logging session data to {telemetry.filename}")

    try:
        while True:
            target_color = state.current_target()
            if not target_color:
                emit_command("STOP", {"reason": "mission_complete"})
                break

            ret, frame = vision.read_frame()
            if not ret:
                logger.warning("WARN: Frame read failed")
                time.sleep(0.1)
                continue

            frame_center_x = CAMERA_WIDTH // 2
            mask, target_info = vision.process_frame(frame, target_color)

            dist_val = None
            err_val = None
            action_taken = "NONE"
            fsm_state = "HOLDING" if state.holding else "SEARCH/APPROACH"
            is_detected = bool(target_info)
            yolo_confidence = target_info.get('yolo_confidence') if target_info else None
            color_score = target_info.get('color_score') if target_info else None
            combined_score = target_info.get('combined_score') if target_info else None

            debug_frame = frame.copy()
            cv2.putText(debug_frame, f"Target: {target_color}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if target_info:
                dist_val = target_info['distance_cm']
                cx = target_info['x']
                err_val = cx - frame_center_x

                x, y = cx - target_info['w']//2, target_info['y'] - target_info['h']//2
                cv2.rectangle(debug_frame, (x, y), (x + target_info['w'], y + target_info['h']), (255, 0, 0), 2)
                cv2.putText(debug_frame, f"Dist: {int(dist_val)}cm", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

                if state.holding:
                    elapsed = time.time() - state.hold_start_time
                    cv2.putText(debug_frame, f"HOLDING: {elapsed:.1f}s", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                    if elapsed >= HOLD_TIME_SEC:
                        state.advance()
                        action_taken = "ADVANCE_SEQUENCE"
                    else:
                        action_taken = emit_command("STOP", {"reason": "holding", "time_left": round(HOLD_TIME_SEC - elapsed, 1)})
                else:
                    if dist_val <= TARGET_DISTANCE_CM:
                        action_taken = emit_command("STOP", {"reason": "target_reached", "distance_cm": round(dist_val, 1)})
                        state.holding = True
                        state.hold_start_time = time.time()
                    else:
                        if abs(err_val) > CENTER_TOLERANCE_PX:
                            if err_val > 0:
                                action_taken = emit_command("SPIN_RIGHT", {"error_px": err_val})
                            else:
                                action_taken = emit_command("SPIN_LEFT", {"error_px": err_val})
                        else:
                            action_taken = emit_command("DRIVE_FORWARD", {"distance_cm": round(dist_val, 1)})
            else:
                if not state.holding:
                    action_taken = emit_command("SEARCH", {"action": "spin_left"})
                    cv2.putText(debug_frame, "SEARCHING...", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)

            telemetry.log_step(
                target_color,
                is_detected,
                dist_val,
                err_val,
                fsm_state,
                action_taken,
                yolo_confidence=yolo_confidence,
                color_score=color_score,
                combined_score=combined_score,
            )

            cv2.imshow("CV Perception Node", debug_frame)
            cv2.imshow("CV Mask", mask)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("SYSTEM_SHUTDOWN: Manual quit")
                break

    except KeyboardInterrupt:
        logger.info("SYSTEM_SHUTDOWN: Keyboard interrupt")
    finally:
        emit_command("STOP", {"reason": "shutdown"})
        vision.cleanup()
        telemetry.cleanup()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
