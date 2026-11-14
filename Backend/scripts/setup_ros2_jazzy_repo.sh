#!/usr/bin/env bash
# ROS 2 Jazzy の apt リポジトリを登録する（Ubuntu 24.04 Noble 用）
# 使い方: sudo bash scripts/setup_ros2_jazzy_repo.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "sudo で実行してください: sudo bash $0" >&2
  exit 1
fi

. /etc/os-release
if [[ "${UBUNTU_CODENAME:-}" != "noble" ]]; then
  echo "ROS 2 Jazzy は Ubuntu 24.04 (noble) 向けです。現在: ${UBUNTU_CODENAME:-unknown}" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

# 1. UTF-8 ロケール
apt-get update
apt-get install -y locales
locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# 2. universe リポジトリ有効化
apt-get install -y software-properties-common curl
add-apt-repository -y universe

# 3. ros2-apt-source パッケージ（鍵 + sources 設定）を導入
ROS_APT_SOURCE_VERSION=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F '"tag_name"' | awk -F'"' '{print $4}')
DEB="/tmp/ros2-apt-source.deb"
curl -fL -o "$DEB" \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.${UBUNTU_CODENAME}_all.deb"
dpkg -i "$DEB"
rm -f "$DEB"

# 4. パッケージリスト更新 & 既存パッケージ更新（Jazzy 導入前に推奨）
apt-get update
apt-get upgrade -y

echo
echo "ROS 2 Jazzy のリポジトリ登録が完了しました (ros2-apt-source ${ROS_APT_SOURCE_VERSION})。"
echo "インストール例:"
echo "  sudo apt install -y ros-jazzy-desktop   # GUI込み (rviz2 等)"
echo "  sudo apt install -y ros-jazzy-ros-base  # 最小構成"
echo "  sudo apt install -y ros-dev-tools       # colcon, rosdep 等の開発ツール"
