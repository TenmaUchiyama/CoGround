cmake_minimum_required(VERSION 3.0.2)
project(coground_vr_bridge)

find_package(catkin REQUIRED)
catkin_package()

catkin_install_python(PROGRAMS scripts/model_pose_relay.py scripts/world_odom_tf.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
install(DIRECTORY launch rviz DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
