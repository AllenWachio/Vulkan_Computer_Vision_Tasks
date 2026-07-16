import rclpy
import cv2
import numpy as np
import time
import csv
import sys
import os

from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from cv_bridge import CvBridge
from datetime import datetime
from .telemetry_ros import BalloonTelemetry


# --- NOW YOU CAN IMPORT YOUR EXTERNAL FILES ---
from .vision.balloon_vision import BalloonDetector


class BalloonNode(Node):
    def __init__(self):
        super().__init__('balloon_perception_node')
        
        # 1. Declare Parameters (Matching your YAML file)
        self.declare_parameter('target_sequence', ['BLACK', 'WHITE', 'PINK', 'YELLOW', 'BLUE'])
        self.declare_parameter('target_distance_cm', 150.0)
        self.declare_parameter('hold_time_sec', 5.0)
        self.declare_parameter('center_tolerance_px', 50)
        
        # YOLO Params
        self.declare_parameter('yolo_model_path', 'Ballon_Detection_Weights/best.onnx')
        self.declare_parameter('yolo_conf_threshold', 0.35)
        self.declare_parameter('yolo_iou_threshold', 0.45)
        self.declare_parameter('yolo_input_size', 640)
        
        # Distance Estimation Params
        self.declare_parameter('real_balloon_width_cm', 30.0)
        self.declare_parameter('focal_length_px', 600.0)
        
        # Color Verification Params
        self.declare_parameter('color_mask_min_ratio', 0.08)
        self.declare_parameter('color_combined_score_threshold', 0.35)
        
        # HSV Bounds
        self.declare_parameter('hsv_black_lower', [0, 0, 0])
        self.declare_parameter('hsv_black_upper', [180, 255, 60])
        self.declare_parameter('hsv_white_lower', [0, 0, 200])
        self.declare_parameter('hsv_white_upper', [180, 40, 255])
        self.declare_parameter('hsv_pink_lower', [145, 50, 50])
        self.declare_parameter('hsv_pink_upper', [170, 255, 255])
        self.declare_parameter('hsv_yellow_lower', [20, 100, 100])
        self.declare_parameter('hsv_yellow_upper', [40, 255, 255])
        self.declare_parameter('hsv_blue_lower', [100, 100, 50])
        self.declare_parameter('hsv_blue_upper', [130, 255, 255])
        
        # 2. Load Parameters into instance variables for efficiency
        self.sequence = self.get_parameter('target_sequence').value
        self.target_dist = self.get_parameter('target_distance_cm').value
        self.hold_time = self.get_parameter('hold_time_sec').value
        self.center_tol = self.get_parameter('center_tolerance_px').value
        
        self.color_mask_min_ratio = self.get_parameter('color_mask_min_ratio').value
        self.color_combined_score_threshold = self.get_parameter('color_combined_score_threshold').value
        self.focal_length_px = self.get_parameter('focal_length_px').value
        self.real_balloon_width_cm = self.get_parameter('real_balloon_width_cm').value
        
        # Build HSV_BOUNDS dictionary dynamically from parameters
        self.hsv_bounds = {
            'BLACK': (self.get_parameter('hsv_black_lower').value, self.get_parameter('hsv_black_upper').value),
            'WHITE': (self.get_parameter('hsv_white_lower').value, self.get_parameter('hsv_white_upper').value),
            'PINK': (self.get_parameter('hsv_pink_lower').value, self.get_parameter('hsv_pink_upper').value),
            'YELLOW': (self.get_parameter('hsv_yellow_lower').value, self.get_parameter('hsv_yellow_upper').value),
            'BLUE': (self.get_parameter('hsv_blue_lower').value, self.get_parameter('hsv_blue_upper').value),
        }
        
        # 3. Setup ROS Interfaces
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.state_pub = self.create_publisher(String, '/balloon_state', 10)
        
        # --- CHANGE IS HERE: Updated topic name to match the new CSI camera node ---
        self.image_sub = self.create_subscription(
            Image, 
            '/camera/image_raw',  # Changed from '/camera/color/image_raw'
            self.image_callback, 
            10
        )
        self.bridge = CvBridge()
        
        # 4. Initialize Perception
        model_path = self.get_parameter('yolo_model_path').value
        conf_thresh = self.get_parameter('yolo_conf_threshold').value
        iou_thresh = self.get_parameter('yolo_iou_threshold').value
        input_size = self.get_parameter('yolo_input_size').value
        
        self.detector = BalloonDetector(
            model_path, 
            conf_threshold=conf_thresh, 
            iou_threshold=iou_thresh, 
            input_size=input_size
        )
        
        # 5. State Machine Variables
        self.current_idx = 0
        self.holding = False
        self.hold_start_time = 0.0
        
        # 2. Initialize the telemetry logger
        self.telemetry = BalloonTelemetry()
        self.get_logger().info(f"Telemetry logging to: {self.telemetry.filename}")

    def _verify_color_in_roi(self, frame, bbox, target_color_name, detection_confidence):
        """Adapted from vision.py to use cached ROS 2 parameters."""
        x1, y1, x2, y2 = bbox
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None, None

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_bound, upper_bound = self.hsv_bounds.get(target_color_name, ((0, 0, 0), (0, 0, 0)))
        lower_bound = np.array(lower_bound, dtype=np.uint8)
        upper_bound = np.array(upper_bound, dtype=np.uint8)

        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)

        roi_area = float(roi.shape[0] * roi.shape[1])
        if roi_area <= 0:
            return None, None

        mask_ratio = cv2.countNonZero(mask) / roi_area
        if mask_ratio < self.color_mask_min_ratio:
            return None, None

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None

        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        if area <= 500:
            return None, None

        contour_x, contour_y, contour_w, contour_h = cv2.boundingRect(largest_contour)
        contour_area_ratio = area / roi_area
        combined_score = (0.6 * detection_confidence) + (0.3 * mask_ratio) + (0.1 * min(1.0, contour_area_ratio))

        if combined_score < self.color_combined_score_threshold:
            return None, None

        center_x = x1 + contour_x + contour_w // 2
        center_y = y1 + contour_y + contour_h // 2
        
        # Distance calculation using cached parameters
        distance_cm = (self.real_balloon_width_cm * self.focal_length_px) / max(contour_w, 1)

        target_info = {
            'x': center_x,
            'y': center_y,
            'w': contour_w,
            'h': contour_h,
            'distance_cm': distance_cm,
            'area': area,
            'yolo_confidence': detection_confidence,
            'color_score': mask_ratio,
            'combined_score': combined_score,
            'source': 'yolo_roi',
            'bbox': (x1, y1, x2, y2),
        }

        # Build full mask for debugging/visualization if needed later
        full_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        full_mask[y1:y2, x1:x2] = mask
        return full_mask, target_info

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"cv_bridge failed: {e}")
            return
            
        target_color = self.sequence[self.current_idx] if self.current_idx < len(self.sequence) else None
        
        twist = Twist()
        state_msg = String()
        action_taken = "NONE"
        dist_val = None
        err_val = None
        is_detected = False
        
        # Telemetry variables
        yolo_conf = None
        color_score = None
        combined_score = None
        
        if target_color:
            # --- RUN PERCEPTION PIPELINE ---
            detections = self.detector.detect(frame)
            best_target = None

            for detection in detections:
                mask, target_info = self._verify_color_in_roi(
                    frame,
                    detection['bbox'],
                    target_color,
                    detection['confidence'],
                )
                if target_info is None:
                    continue

                # Keep the detection with the highest combined score
                if best_target is None or target_info['combined_score'] > best_target['combined_score']:
                    best_target = target_info

            target_info = best_target
            
            if target_info:
                is_detected = True
                dist_val = target_info['distance_cm']
                err_val = target_info['x'] - (frame.shape[1] // 2)
                
                yolo_conf = target_info.get('yolo_confidence')
                color_score = target_info.get('color_score')
                combined_score = target_info.get('combined_score')
                
                # --- STATE MACHINE LOGIC ---
                if self.holding:
                    elapsed = time.time() - self.hold_start_time
                    if elapsed >= self.hold_time:
                        self.current_idx += 1
                        self.holding = False
                        next_target = self.sequence[self.current_idx] if self.current_idx < len(self.sequence) else "DONE"
                        self.get_logger().info(f"SEQUENCE_ADVANCE: Next Target -> {next_target}")
                        action_taken = "ADVANCE"
                    else:
                        action_taken = "STOP_HOLD"
                        state_msg.data = f"HOLDING ({self.hold_time - elapsed:.1f}s)"
                else:
                    if dist_val <= self.target_dist:
                        self.holding = True
                        self.hold_start_time = time.time()
                        action_taken = "STOP_TARGET"
                        state_msg.data = "TARGET_REACHED"
                    else:
                        if abs(err_val) > self.center_tol:
                            if err_val > 0:
                                twist.angular.z = -0.5  # SPIN RIGHT
                                action_taken = "SPIN_RIGHT"
                            else:
                                twist.angular.z = 0.5   # SPIN LEFT
                                action_taken = "SPIN_LEFT"
                            state_msg.data = action_taken
                        else:
                            twist.linear.x = 0.2        # DRIVE FORWARD
                            action_taken = "DRIVE_FORWARD"
                            state_msg.data = action_taken
            else:
                # No balloon detected
                if not self.holding:
                    twist.angular.z = 0.3               # SEARCH (Spin slowly)
                    action_taken = "SEARCH"
                    state_msg.data = "SEARCHING"
        else:
            self.get_logger().info("Mission Complete!")
            state_msg.data = "MISSION_COMPLETE"
            
        # Publish Commands
        self.cmd_vel_pub.publish(twist)
        self.state_pub.publish(state_msg)
        
        # 3. Log the step at the very end of the callback
        self.telemetry.log_step(
            target_color=target_color,
            is_detected=is_detected,
            distance=dist_val,
            error=err_val,
            fsm_state=state_msg.data, # Or whatever string represents your FSM state
            action=action_taken,
            yolo_confidence=yolo_conf,
            color_score=color_score,
            combined_score=combined_score
        )

    def destroy_node(self):
        self.telemetry.cleanup()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = BalloonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()