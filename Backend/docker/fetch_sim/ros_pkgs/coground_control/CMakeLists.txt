cmake_minimum_required(VERSION 3.0.2)
project(coground_control)

find_package(catkin REQUIRED)
catkin_package()

catkin_install_python(PROGRAMS scripts/arm_command_server.py scripts/base_pose_tf.py scripts/scene_sync.py scripts/pick_place_server.py scripts/trajectory_path.py
  scripts/fake_base_driver.py scripts/base_command_server.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
install(DIRECTORY launch config DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
