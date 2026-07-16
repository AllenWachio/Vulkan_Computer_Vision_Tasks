import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_dir = get_package_share_directory('cv_rover_nodes')
    param_file = os.path.join(pkg_dir, 'config', 'params.yaml')

    # --- 1. DECLARE LAUNCH ARGUMENTS ---
    task_arg = DeclareLaunchArgument(
        'task', default_value='balloon', 
        description='Which task to run: "balloon" or "object"'
    )
    cam_arg = DeclareLaunchArgument(
        'camera', default_value='v4l2', 
        description='Which camera platform to use: "v4l2", "jetson", or "rpi"'
    )

    # --- 2. CREATE CONDITIONS ---
    is_balloon = PythonExpression(["'", LaunchConfiguration('task'), "' == 'balloon'"])
    is_object  = PythonExpression(["'", LaunchConfiguration('task'), "' == 'object'"])

    is_v4l2   = PythonExpression(["'", LaunchConfiguration('camera'), "' == 'v4l2'"])
    is_jetson = PythonExpression(["'", LaunchConfiguration('camera'), "' == 'jetson'"])
    is_rpi    = PythonExpression(["'", LaunchConfiguration('camera'), "' == 'rpi'"])

    # --- 3. CAMERA NODES (Only one will run based on the 'camera' argument) ---
    
    # Option A: Standard V4L2 (For Ubuntu / USB Webcams / V4L2-compatible CSI)
    v4l2_node = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='camera',
        parameters=[{
            'image_size': [640, 480],  # Forces 640x480 natively!
            'video_device': '/dev/video0'
        }],
        remappings=[
            ('/image_raw', '/camera/image_raw'), 
            ('/camera_info', '/camera/camera_info')
        ],
        condition=IfCondition(is_v4l2),
        output='screen'
    )

    # Option B: Custom Node for NVIDIA Jetson (CSI)
    jetson_node = Node(
        package='cv_rover_nodes',
        executable='csi_camera_node',
        name='camera',
        parameters=[{
            'width': 640, 'height': 480, 'framerate': 30.0,
            'camera_type': 'jetson' # Tells the python node which pipeline to build
        }],
        condition=IfCondition(is_jetson),
        output='screen'
    )

    # Option C: Custom Node for Raspberry Pi (CSI / libcamera)
    rpi_node = Node(
        package='cv_rover_nodes',
        executable='csi_camera_node',
        name='camera',
        parameters=[{
            'width': 640, 'height': 480, 'framerate': 30.0,
            'camera_type': 'rpi' # Tells the python node which pipeline to build
        }],
        condition=IfCondition(is_rpi),
        output='screen'
    )

    # --- 4. PERCEPTION NODES (Only one will run based on the 'task' argument) ---
    
    balloon_node = Node(
        package='cv_rover_nodes',
        executable='balloon_node',
        name='balloon_perception_node',
        parameters=[param_file],
        condition=IfCondition(is_balloon),
        output='screen'
    )
    
    object_node = Node(
        package='cv_rover_nodes',
        executable='object_node',
        name='object_detection_node',
        parameters=[param_file],
        condition=IfCondition(is_object),
        output='screen'
    )

    return LaunchDescription([
        task_arg, 
        cam_arg,
        v4l2_node, 
        jetson_node, 
        rpi_node,
        balloon_node, 
        object_node
    ])

"""
SCENARIOS:
Scenario A: You are on a Jetson, doing Object task
ros2 launch cv_rover_nodes cv_rover.launch.py task:=object camera:=jetson

Scenario B: You are on a Jetson, doing Balloon task
ros2 launch cv_rover_nodes cv_rover.launch.py task:=balloon camera:=jetson

Scenario C: You are on a Raspberry Pi, doing Balloon task
ros2 launch cv_rover_nodes cv_rover.launch.py task:=balloon camera:=rpi

Scenario D: You are on Ubuntu with a V4L2 camera, doing Balloon task
ros2 launch cv_rover_nodes cv_rover.launch.py task:=balloon camera:=v4l2
"""