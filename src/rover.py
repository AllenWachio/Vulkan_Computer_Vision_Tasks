import time
import logging

logger = logging.getLogger(__name__)

class RoverMockAPI:
    """
    Mock interface for Rover movement. 
    Replace the logic in these methods with actual motor driver commands (e.g., ROS Twist, serial commands to Arduino, etc.)
    """
    
    def __init__(self):
        self.is_moving = False
        
    def drive_forward(self, speed=0.5):
        """
        Drive forward at the given speed (0.0 to 1.0).
        TODO: Insert motor driver / ROS integration here.
        """
        if not self.is_moving:
            logger.info(f"Rover: Moving FORWARD at speed {speed}")
            self.is_moving = True

    def spin_left(self, speed=0.3):
        """
        Spin the rover left to search for balloons.
        TODO: Insert motor driver / ROS integration here.
        """
        logger.info(f"Rover: Spinning LEFT at speed {speed}")

    def spin_right(self, speed=0.3):
        """
        Spin the rover right to align with a balloon.
        TODO: Insert motor driver / ROS integration here.
        """
        logger.info(f"Rover: Spinning RIGHT at speed {speed}")

    def stop(self):
        """
        Stop all motors.
        TODO: Insert motor driver / ROS integration here.
        """
        logger.info("Rover: STOPPING")
        self.is_moving = False
