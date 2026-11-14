#!/usr/bin/env python3
# 使い方: python3 Backend/scripts/check_unity_connection.py [IP]   (既定 127.0.0.1)
# 結果に /unity/joint_states の件数が出れば Unity からも接続できる
# ROS-TCP-Connector と同じ手順で Endpoint に接続し、/unity/joint_states を購読できるか確かめる
import json, socket, struct, sys, time
host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
def frame(dest, payload):
    d = dest.encode()
    return struct.pack("<I", len(d)) + d + struct.pack("<I", len(payload)) + payload
def recv_exact(s, n):
    b = b""
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c: raise EOFError
        b += c
    return b
s = socket.create_connection((host, 10000), timeout=5)
s.sendall(frame("__subscribe", json.dumps({"topic": "/unity/joint_states", "message_name": "sensor_msgs/JointState"}).encode()))
counts = {}
t0 = time.time()
while time.time() - t0 < 3:
    n = struct.unpack("<I", recv_exact(s, 4))[0]
    dest = recv_exact(s, n).decode()
    m = struct.unpack("<I", recv_exact(s, 4))[0]
    recv_exact(s, m)
    counts[dest] = counts.get(dest, 0) + 1
print(counts)
