#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/qyb413/CyberLuban"
WS="$ROOT/nuc/robot/ros2_workspace_src"
LOG_DIR="/tmp/cyberluban_orbbec_defect_logs"
PID_DIR="/tmp/cyberluban_orbbec_defect_pids"
RAW_VIEWER="/tmp/orbbec_web_viewer.py"
DETECT_VIEWER="/tmp/orbbec_detection_web_viewer.py"
MODEL="$WS/demo/models/road_damage_yolov8.pt"
CRI_OVERLAY="/tmp/cyberluban_cri_install/setup.bash"

mkdir -p "$LOG_DIR" "$PID_DIR"

usage() {
  cat <<EOF
用法: $0 {start|stop|restart|status|open|logs}

命令:
  start    启动 Orbbec 相机、缺陷识别模型、两个 Web 实时窗口
  stop     停止上述所有进程
  restart  先 stop 再 start
  status   查看 ROS2 话题、进程和窗口服务状态
  open     打开两个窗口地址提示
  logs     查看最近日志路径

窗口:
  原始相机画面:     http://localhost:8088/
  缺陷识别结果:     http://localhost:8089/
EOF
}

source_ros() {
  source /opt/ros/humble/setup.bash
  if [[ -f "$CRI_OVERLAY" ]]; then
    source "$CRI_OVERLAY"
  fi
  export PYTHONPATH="$WS/src/cri_perception/vision_defect_detector:${PYTHONPATH:-}"
}

write_raw_viewer() {
  cat > "$RAW_VIEWER" <<'PY'
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2, numpy as np, rclpy
from sensor_msgs.msg import Image

latest_jpeg = None
latest_info = "waiting for image"
lock = threading.Lock()

class NodeWrap:
    def __init__(self):
        rclpy.init(args=None)
        self.node = rclpy.create_node("orbbec_web_jpeg_viewer")
        self.node.create_subscription(Image, "/camera/color/image_raw", self.cb, 10)
    def cb(self, msg):
        global latest_jpeg, latest_info
        h, w = msg.height, msg.width
        data = np.frombuffer(msg.data, dtype=np.uint8)
        enc = msg.encoding.lower()
        if enc == "rgb8":
            img = cv2.cvtColor(data.reshape((h, w, 3)), cv2.COLOR_RGB2BGR)
        elif enc == "bgr8":
            img = data.reshape((h, w, 3))
        elif enc in ("mono8", "8uc1"):
            img = data.reshape((h, w))
        else:
            latest_info = "unsupported encoding " + msg.encoding
            return
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            with lock:
                latest_jpeg = buf.tobytes()
                latest_info = f"{w}x{h} {msg.encoding} stamp={msg.header.stamp.sec}.{msg.header.stamp.nanosec:09d}"
    def spin(self):
        rclpy.spin(self.node)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): return
    def _send(self, code, content_type, body=b""):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD" and body:
            self.wfile.write(body)
    def do_HEAD(self):
        if self.path.startswith("/frame.jpg"):
            with lock: frame = latest_jpeg
            self._send(200 if frame is not None else 503, "image/jpeg", frame or b"")
        elif self.path == "/status":
            self._send(200, "text/plain; charset=utf-8", latest_info.encode("utf-8"))
        else:
            self._send(200, "text/html; charset=utf-8")
    def do_GET(self):
        global latest_jpeg, latest_info
        if self.path.startswith("/frame.jpg"):
            with lock: frame = latest_jpeg
            if frame is None:
                self._send(503, "text/plain; charset=utf-8", b"waiting for image")
                return
            self._send(200, "image/jpeg", frame)
            return
        if self.path == "/status":
            self._send(200, "text/plain; charset=utf-8", latest_info.encode("utf-8"))
            return
        body = """<!doctype html><html><head><meta charset='utf-8'><title>Orbbec Raw Viewer</title><style>body{background:#111;color:#eee;font-family:sans-serif;margin:20px}img{max-width:100%;border:1px solid #555}</style></head><body><h2>Orbbec 原始实时画面</h2><p id='status'>loading</p><img id='image' src='/frame.jpg'><script>function tick(){var t=Date.now();document.getElementById('image').src='/frame.jpg?t='+t;fetch('/status').then(function(r){return r.text();}).then(function(x){document.getElementById('status').textContent=x;}).catch(function(){document.getElementById('status').textContent='等待服务';});}setInterval(tick,200);tick();</script></body></html>""".encode("utf-8")
        self._send(200, "text/html; charset=utf-8", body)

node = NodeWrap()
threading.Thread(target=node.spin, daemon=True).start()
print("Orbbec raw web viewer running: http://localhost:8088/", flush=True)
ThreadingHTTPServer(("0.0.0.0", 8088), Handler).serve_forever()
PY
}

write_detect_viewer() {
  cat > "$DETECT_VIEWER" <<'PY'
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2, numpy as np, rclpy
from sensor_msgs.msg import Image

latest_jpeg = None
latest_info = "waiting for detection image"
lock = threading.Lock()

class NodeWrap:
    def __init__(self):
        rclpy.init(args=None)
        self.node = rclpy.create_node("orbbec_detection_web_viewer")
        self.node.create_subscription(Image, "/perception/detection_image", self.cb, 10)
    def cb(self, msg):
        global latest_jpeg, latest_info
        h, w = msg.height, msg.width
        data = np.frombuffer(msg.data, dtype=np.uint8)
        enc = msg.encoding.lower()
        if enc == "rgb8":
            img = cv2.cvtColor(data.reshape((h, w, 3)), cv2.COLOR_RGB2BGR)
        elif enc == "bgr8":
            img = data.reshape((h, w, 3))
        elif enc in ("mono8", "8uc1"):
            img = data.reshape((h, w))
        else:
            latest_info = "unsupported encoding " + msg.encoding
            return
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            with lock:
                latest_jpeg = buf.tobytes()
                latest_info = f"/perception/detection_image {w}x{h} {msg.encoding} stamp={msg.header.stamp.sec}.{msg.header.stamp.nanosec:09d}"
    def spin(self):
        rclpy.spin(self.node)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): return
    def _send(self, code, content_type, body=b""):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD" and body:
            self.wfile.write(body)
    def do_HEAD(self):
        if self.path.startswith("/frame.jpg"):
            with lock: frame = latest_jpeg
            self._send(200 if frame is not None else 503, "image/jpeg", frame or b"")
        elif self.path == "/status":
            self._send(200, "text/plain; charset=utf-8", latest_info.encode("utf-8"))
        else:
            self._send(200, "text/html; charset=utf-8")
    def do_GET(self):
        global latest_jpeg, latest_info
        if self.path.startswith("/frame.jpg"):
            with lock: frame = latest_jpeg
            if frame is None:
                self._send(503, "text/plain; charset=utf-8", b"waiting for detection image")
                return
            self._send(200, "image/jpeg", frame)
            return
        if self.path == "/status":
            self._send(200, "text/plain; charset=utf-8", latest_info.encode("utf-8"))
            return
        body = """<!doctype html><html><head><meta charset='utf-8'><title>Orbbec Defect Viewer</title><style>body{background:#111;color:#eee;font-family:sans-serif;margin:20px}img{max-width:100%;border:1px solid #555}</style></head><body><h2>Orbbec 缺陷识别结果</h2><p id='status'>loading</p><img id='image' src='/frame.jpg'><script>function tick(){var t=Date.now();document.getElementById('image').src='/frame.jpg?t='+t;fetch('/status').then(function(r){return r.text();}).then(function(x){document.getElementById('status').textContent=x;}).catch(function(){document.getElementById('status').textContent='等待服务';});}setInterval(tick,250);tick();</script></body></html>""".encode("utf-8")
        self._send(200, "text/html; charset=utf-8", body)

node = NodeWrap()
threading.Thread(target=node.spin, daemon=True).start()
print("Orbbec detection web viewer running: http://localhost:8089/", flush=True)
ThreadingHTTPServer(("0.0.0.0", 8089), Handler).serve_forever()
PY
}

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

start_bg() {
  local name="$1"
  local cmd="$2"
  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"
  if is_running "$pid_file"; then
    echo "$name 已运行，PID $(cat "$pid_file")"
    return
  fi
  nohup bash -lc "$cmd" > "$log_file" 2>&1 &
  echo $! > "$pid_file"
  echo "$name 已启动，PID $(cat "$pid_file")，日志 $log_file"
}

stop_one() {
  local name="$1"
  local pid_file="$PID_DIR/$name.pid"
  if is_running "$pid_file"; then
    kill "$(cat "$pid_file")" 2>/dev/null || true
    sleep 1
    if is_running "$pid_file"; then
      kill -9 "$(cat "$pid_file")" 2>/dev/null || true
    fi
    echo "$name 已停止"
  fi
  rm -f "$pid_file"
}

start_all() {
  write_raw_viewer
  write_detect_viewer
  fuser -k 8088/tcp >/dev/null 2>&1 || true
  fuser -k 8089/tcp >/dev/null 2>&1 || true
  start_bg camera "source /opt/ros/humble/setup.bash && ros2 launch orbbec_camera orbbec_camera.launch.py camera_model:=gemini330_series usb_port:=3-1 enable_depth:=true enable_color:=true"
  sleep 6
  start_bg detector "source /opt/ros/humble/setup.bash; source $CRI_OVERLAY 2>/dev/null || true; export PYTHONPATH=$WS/src/cri_perception/vision_defect_detector:\${PYTHONPATH:-}; python3 -m vision_defect_detector.vision_defect_detector_node --ros-args -p image_topic:=/camera/color/image_raw -p model_path:=$MODEL -p confidence_threshold:=0.25 -p input_size:=640 -p device:=cpu -p enable_visualization:=true"
  start_bg raw_viewer "source /opt/ros/humble/setup.bash; python3 $RAW_VIEWER"
  start_bg detect_viewer "source /opt/ros/humble/setup.bash; source $CRI_OVERLAY 2>/dev/null || true; python3 $DETECT_VIEWER"
  echo
  echo "已启动。窗口："
  echo "  原始相机画面: http://localhost:8088/"
  echo "  缺陷识别结果: http://localhost:8089/"
}

stop_all() {
  stop_one detect_viewer
  stop_one raw_viewer
  stop_one detector
  stop_one camera
  pkill -f "orbbec_detection_web_viewer.py" 2>/dev/null || true
  pkill -f "orbbec_web_viewer.py" 2>/dev/null || true
  pkill -f "vision_defect_detector_node" 2>/dev/null || true
  pkill -f "orbbec_camera" 2>/dev/null || true
  pkill -f "component_container_mt" 2>/dev/null || true
  echo "全部已停止"
}

status_all() {
  echo "进程状态:"
  for name in camera detector raw_viewer detect_viewer; do
    pid_file="$PID_DIR/$name.pid"
    if is_running "$pid_file"; then
      echo "  $name: running PID $(cat "$pid_file")"
    else
      echo "  $name: stopped"
    fi
  done
  echo
  echo "窗口状态:"
  echo -n "  8088 原始画面: "
  curl -s --max-time 2 http://localhost:8088/status || echo -n "不可用"
  echo
  echo -n "  8089 识别结果: "
  curl -s --max-time 2 http://localhost:8089/status || echo -n "不可用"
  echo
  echo
  echo "ROS2 话题:"
  bash -lc 'source /opt/ros/humble/setup.bash; source /tmp/cyberluban_cri_install/setup.bash 2>/dev/null || true; ros2 topic list -t | grep -E "camera/color/image_raw|perception/detection_image|perception/vision_defects" || true; ros2 topic info /camera/color/image_raw 2>/dev/null || true; ros2 topic info /perception/detection_image 2>/dev/null || true; ros2 topic info /perception/vision_defects 2>/dev/null || true'
}

case "${1:-}" in
  start) start_all ;;
  stop) stop_all ;;
  restart) stop_all; sleep 1; start_all ;;
  status) status_all ;;
  open)
    echo "原始相机画面: http://localhost:8088/"
    echo "缺陷识别结果: http://localhost:8089/"
    ;;
  logs)
    echo "$LOG_DIR"
    ls -lh "$LOG_DIR" || true
    ;;
  *) usage; exit 1 ;;
esac
