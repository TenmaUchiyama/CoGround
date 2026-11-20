# 実機 Fetch の上で動かす確認ツール (ROS 1 Noetic, 画面なし)
# roscore / ドライバは Fetch 本体のものを使い、このコンテナはそこへつなぐだけ。
FROM ros:noetic-ros-base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# ROS の apt 署名鍵は 2025-06 に更新されたため、ros-apt-source で登録し直す (fetch_sim と同じ)
ARG ROS_APT_SOURCE_VERSION=1.3.0
ADD https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros-apt-source_${ROS_APT_SOURCE_VERSION}.focal_all.deb /tmp/ros-apt-source.deb
RUN rm -f /etc/apt/sources.list.d/ros*.list \
 && dpkg -i /tmp/ros-apt-source.deb \
 && rm /tmp/ros-apt-source.deb \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      python-is-python3 \
      ros-noetic-actionlib \
      ros-noetic-control-msgs \
      ros-noetic-diagnostic-msgs \
      ros-noetic-fetch-driver-msgs \
      ros-noetic-nav-msgs \
      ros-noetic-power-msgs \
      ros-noetic-robot-controllers-msgs \
      ros-noetic-rosnode \
      ros-noetic-rostopic \
      ros-noetic-sensor-msgs \
      ros-noetic-tf2-ros \
 && rm -rf /var/lib/apt/lists/*

# 確認ツール本体 (compose で src をマウントするので、Python の変更は再ビルド不要)
WORKDIR /opt/check_ws
COPY ros_pkgs/ src/
RUN source /opt/ros/noetic/setup.bash \
 && catkin_make -DCMAKE_BUILD_TYPE=Release

COPY ros_env.sh /etc/ros_env.sh
COPY entrypoint.sh /entrypoint.sh
COPY fetch_check.sh /usr/local/bin/fetch_check
RUN chmod +x /entrypoint.sh /usr/local/bin/fetch_check \
 && echo 'source /etc/ros_env.sh' >> /root/.bashrc
# docker exec fetch_real bash -c '...' (非対話の bash) でも ROS の環境を読み込む
ENV BASH_ENV=/etc/ros_env.sh
ENV FETCH_CHECK_REPORT_DIR=/data/reports

ENTRYPOINT ["/entrypoint.sh"]
# 段階 A は常駐するだけ。確認は docker exec で fetch_check を呼ぶ (段階 C で Web サーバーに替える)
CMD ["sleep", "infinity"]
