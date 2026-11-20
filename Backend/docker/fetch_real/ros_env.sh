# ROS の環境 (entrypoint / docker exec / fetch_check の全部で読む)
source /opt/ros/noetic/setup.bash
source /opt/check_ws/devel/setup.bash
# compose で値なしで渡した ROS_HOSTNAME / ROS_IP は空文字になり、rospy が警告するので消す
[ -z "${ROS_HOSTNAME:-}" ] && unset ROS_HOSTNAME
[ -z "${ROS_IP:-}" ] && unset ROS_IP
true
