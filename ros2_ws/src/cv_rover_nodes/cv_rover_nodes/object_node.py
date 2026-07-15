import time
import rclpy
import csv
import os
import cv2
import json
import sys

from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from cv_bridge import CvBridge
from datetime import datetime
from .telemetry_ros import ObjectTelemetry

# 1. Get the directory where this current node file lives
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Navigate up 4 levels to reach the project root directory
# Path: cv_rover_nodes (1) -> cv_rover_nodes (2) -> src (3) -> ros2_ws (4) -> PROJECT ROOT
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))

# 3. Add the project root to Python's path if it isn't already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- NOW YOU CAN IMPORT YOUR EXTERNAL FILES ---
from src.object_task.vision import ObjectDetector

class ObjectNode(Node):
    def __init__(self):
        super().__init__('object_detection_node')
        
        # 1. Declare Parameters
        self.declare_parameter('model_path', 'Hammer_Tennisball_Trafficcone_Weights/best.onnx')
        self.declare_parameter('conf_threshold', 0.35)
        self.declare_parameter('iou_threshold', 0.45)
        self.declare_parameter('input_size', 640)
        self.declare_parameter('object_labels', ["Traffic Cone", "Hammer", "Tennis Ball"])
        self.declare_parameter('enable_debug_image', True)
        
        # 2. Load Parameters
        self.model_path = self.get_parameter('model_path').value
        self.conf_threshold = self.get_parameter('conf_threshold').value
        self.iou_threshold = self.get_parameter('iou_threshold').value
        self.input_size = self.get_parameter('input_size').value
        self.enable_debug_image = self.get_parameter('enable_debug_image').value
        
        # 3. Setup ROS Interfaces
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw', self.image_callback, 10
        )
        self.det_pub = self.create_publisher(
            Detection2DArray, '/object_detections', 10
        )
        
        # Optional: Debug image publisher (replaces cv2.imshow)
        if self.enable_debug_image:
            self.debug_pub = self.create_publisher(
                Image, '/object_detection/debug_image', 10
            )
            
        self.bridge = CvBridge()
        
        # 4. Initialize Perception
        self.detector = ObjectDetector(
            model_path=self.model_path,
            conf_threshold=self.conf_threshold,
            iou_threshold=self.iou_threshold,
            input_size=self.input_size
        )
        # 2. Initialize the telemetry logger
        self.telemetry = ObjectTelemetry()
        self.get_logger().info(f"Telemetry logging to: {self.telemetry.filename}")
    
    def setup_telemetry(self):
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = open(f"logs/object_detection_{timestamp}.csv", mode="w", newline="")
        self.writer = csv.writer(self.csv_file)
        # Log timestamp, latency, number of detections, and a JSON string of the detections for easy parsing
        self.writer.writerow(["timestamp", "latency_ms", "num_detections", "detection_details"])

    def image_callback(self, msg):
        start_time = time.time()
        
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"cv_bridge failed: {e}")
            return
            
        # Run detection
        detections = self.detector.detect(frame)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000.0
        
        # Build ROS 2 Detection2DArray message
        det_array = Detection2DArray()
        det_array.header.stamp = self.get_clock().now().to_msg()
        det_array.header.frame_id = "camera_link" # Adjust to your actual camera frame ID
        
        detection_details = []
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label = det['label']
            confidence = det['confidence']
            
            # Populate Detection2D message
            d = Detection2D()
            d.bbox.center.position.x = float(x1 + x2) / 2.0
            d.bbox.center.position.y = float(y1 + y2) / 2.0
            d.bbox.size_x = float(x2 - x1)
            d.bbox.size_y = float(y2 - y1)
            
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = label
            hyp.hypothesis.score = float(confidence)
            d.results.append(hyp)
            
            det_array.detections.append(d)
            detection_details.append({"label": label, "confidence": round(confidence, 3), "bbox": [x1, y1, x2, y2]})
            
        # Publish Detections
        self.det_pub.publish(det_array)
        
        # Optional: Publish Debug Image (Replaces cv2.imshow)
        if self.enable_debug_image:
            debug_frame = frame.copy()
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                label = det['label']
                confidence = det['confidence']
                
                cv2.rectangle(debug_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    debug_frame,
                    f"{label}: {confidence:.2f}",
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

            if not detections:
                cv2.putText(
                    debug_frame,
                    "No objects detected",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )
            
            debug_msg = self.bridge.cv2_to_imgmsg(debug_frame, encoding="bgr8")
            debug_msg.header.stamp = self.get_clock().now().to_msg()
            debug_msg.header.frame_id = "camera_link"
            self.debug_pub.publish(debug_msg)
            
        self.telemetry.log_frame(detections, latency_ms)

    def destroy_node(self):
        self.telemetry.cleanup()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = ObjectNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("SYSTEM_SHUTDOWN: Keyboard interrupt")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()