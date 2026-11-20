# Fetch シミュレーション環境 (ROS 1 Noetic + Gazebo 11)
FROM osrf/ros:noetic-desktop-full

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# ROS の apt 署名鍵は 2025-06 に更新されたため、ros-apt-source で登録し直す
ARG ROS_APT_SOURCE_VERSION=1.3.0
ADD https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros-apt-source_${ROS_APT_SOURCE_VERSION}.focal_all.deb /tmp/ros-apt-source.deb
RUN rm -f /etc/apt/sources.list.d/ros*.list \
 && dpkg -i /tmp/ros-apt-source.deb \
 && rm /tmp/ros-apt-source.deb \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      git \
      python3-catkin-tools \
      ros-noetic-fetch-description \
      ros-noetic-fetch-maps \
      ros-noetic-fetch-moveit-config \
      ros-noetic-fetch-navigation \
      ros-noetic-fetch-teleop \
      ros-noetic-moveit-python \
      ros-noetic-rgbd-launch \
      ros-noetic-robot-controllers \
      ros-noetic-robot-controllers-interface \
      ros-noetic-rosbridge-server \
      ros-noetic-simple-grasping \
      ros-noetic-teleop-twist-keyboard \
 && rm -rf /var/lib/apt/lists/*

# fetch_gazebo は Noetic 向けの apt 配布がないためソースからビルドする
ARG FETCH_GAZEBO_REF=gazebo11
WORKDIR /opt/fetch_ws
RUN git clone --depth 1 -b ${FETCH_GAZEBO_REF} https://github.com/fetchrobotics/fetch_gazebo.git src/fetch_gazebo \
 && touch src/fetch_gazebo/fetchit_challenge/CATKIN_IGNORE src/fetch_gazebo/fetch_simulation/CATKIN_IGNORE \
 && apt-get update \
 && rosdep update --rosdistro noetic --include-eol-distros \
 && rosdep install --from-paths src --ignore-src -y --rosdistro noetic \
 && rm -rf /var/lib/apt/lists/* \
 && source /opt/ros/noetic/setup.bash \
 && catkin_make -DCMAKE_BUILD_TYPE=Release

# Unity (VR) 連携: ROS-TCP-Endpoint (ROS 1 版) と自前ブリッジパッケージ
# (Endpoint のスクリプトは #!/usr/bin/env python なので python-is-python3 が必要)
ARG ROS_TCP_ENDPOINT_REF=v0.7.0
RUN git clone --depth 1 -b ${ROS_TCP_ENDPOINT_REF} https://github.com/Unity-Technologies/ROS-TCP-Endpoint.git src/ros_tcp_endpoint
COPY ros_pkgs/ src/
RUN chmod +x src/coground_vr_bridge/scripts/*.py \
 && apt-get update \
 && apt-get install -y --no-install-recommends python-is-python3 \
 && rosdep install --from-paths src --ignore-src -y --rosdistro noetic \
 && rm -rf /var/lib/apt/lists/* \
 && source /opt/ros/noetic/setup.bash \
 && catkin_make -DCMAKE_BUILD_TYPE=Release

# WSL2 で GPU 描画するには Mesa の d3d12 ドライバが必要。
# focal 標準の Mesa 21.2 には無いので kisak-mesa PPA の Mesa に上げる。
RUN apt-get update \
 && apt-get install -y --no-install-recommends software-properties-common mesa-utils \
 && add-apt-repository -y ppa:kisak/kisak-mesa \
 && apt-get update \
 && apt-get dist-upgrade -y \
 && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
 && echo 'source /opt/fetch_ws/devel/setup.bash' >> /root/.bashrc \
 && echo 'source /opt/fetch_ws/devel/setup.bash' > /etc/ros_env.sh
# docker exec fetch_sim bash -c '...' (非対話の bash) でも ROS の環境を読み込む
ENV BASH_ENV=/etc/ros_env.sh

ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 10000 9090
CMD ["roslaunch", "coground_vr_bridge", "vr_sim.launch"]
