import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'cv_rover_nodes'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        # --- CORRECTED PATHS ---
        # Points to the inner cv_rover_nodes folder where launch/config actually live
        (os.path.join('share', package_name, 'launch'), glob('cv_rover_nodes/launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('cv_rover_nodes/config/*.yaml')),
    ],
    # Note: 'opencv-python' can sometimes conflict with system 'python3-opencv'. 
    # If you get build errors, remove 'opencv-python' from this list (ROS 2 handles it via apt).
    install_requires=['setuptools', 'onnxruntime', 'opencv-python', 'numpy'],
    zip_safe=True,
    maintainer='allen-wachio',
    maintainer_email='allenkizitowachio@gmail.com',
    description='CV Rover Balloon and Object Detection Nodes',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            # --- CORRECTED SPELLING ---
            # Change this to 'ballon_node' IF your file is actually named ballon_node.py.
            # (Highly recommended: Rename the file to balloon_node.py with two L's instead)
            'balloon_node = cv_rover_nodes.balloon_node:main', 
            'object_node = cv_rover_nodes.object_node:main',
        ],
    },
)