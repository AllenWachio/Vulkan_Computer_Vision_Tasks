from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_dir = get_package_share_directory('cv_rover_nodes')
    param_file = os.path.join(pkg_dir, 'config', 'params.yaml')

    return LaunchDescription([
        # 1. Camera Driver (Uncomment and configure based on your hardware)
        # Node(
        #     package='v4l2_camera',
        #     executable='v4l2_camera_node',
        #     name='camera',
        #     parameters=[{'image_width': 640, 'image_height': 480}]
        # ),
        
        # 2. Balloon Node
        Node(
            package='cv_rover_nodes',
            executable='balloon_node',
            name='balloon_perception_node',
            parameters=[param_file],
            output='screen'
        ),
        
        # 3. Object Node
        Node(
            package='cv_rover_nodes',
            executable='object_node',
            name='object_detection_node',
            parameters=[param_file],
            output='screen'
        )
    ])