#!/usr/bin/env python3
"""ROS2 node for USB GNSS NMEA input and optional NTRIP RTCM output."""

import base64
import glob
import json
import socket
import time
from typing import Iterable, Optional

import rclpy
import serial
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus
from std_msgs.msg import String, UInt8MultiArray

from .nmea import GGAFix, navsat_status, parse_gga, quality_name


def serial_candidates() -> list[str]:
    patterns = [
        "/dev/serial/by-id/*if00",
        "/dev/serial/by-id/*",
        "/dev/ttyACM*",
        "/dev/ttyUSB*",
    ]
    candidates: list[str] = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if path not in candidates:
                candidates.append(path)
    return candidates


class RTKGPSNode(Node):
    """Read NMEA, publish NavSatFix, and optionally forward NTRIP RTCM."""

    def __init__(self) -> None:
        super().__init__("rtk_gps_node")
        self.declare_parameter("serial_port", "auto")
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("frame_id", "gps")
        self.declare_parameter("read_period_sec", 0.02)
        self.declare_parameter("reconnect_period_sec", 2.0)
        self.declare_parameter("status_period_sec", 1.0)
        self.declare_parameter("publish_invalid_fix", False)
        self.declare_parameter("nmea_topic", "/gps/nmea")
        self.declare_parameter("fix_topic", "/fix")
        self.declare_parameter("serial_rx_topic", "/rtk/serial_rx")
        self.declare_parameter("serial_tx_topic", "/rtk/serial_tx")
        self.declare_parameter("status_topic", "/rtk/status")
        self.declare_parameter("ntrip_enabled", False)
        self.declare_parameter("ntrip_server", "")
        self.declare_parameter("ntrip_port", 2101)
        self.declare_parameter("ntrip_mountpoint", "")
        self.declare_parameter("ntrip_user", "")
        self.declare_parameter("ntrip_password", "")
        self.declare_parameter("ntrip_gga_period_sec", 5.0)
        self.declare_parameter("ntrip_reconnect_sec", 10.0)

        self.serial_port_param = str(self.get_parameter("serial_port").value)
        self.baudrate = int(self.get_parameter("baudrate").value)
        self.frame_id = str(self.get_parameter("frame_id").value)
        self.read_period = float(self.get_parameter("read_period_sec").value)
        self.reconnect_period = float(
            self.get_parameter("reconnect_period_sec").value
        )
        self.status_period = float(self.get_parameter("status_period_sec").value)
        self.publish_invalid_fix = bool(
            self.get_parameter("publish_invalid_fix").value
        )
        self.ntrip_enabled = bool(self.get_parameter("ntrip_enabled").value)
        self.ntrip_server = str(self.get_parameter("ntrip_server").value)
        self.ntrip_port = int(self.get_parameter("ntrip_port").value)
        self.ntrip_mountpoint = str(self.get_parameter("ntrip_mountpoint").value)
        self.ntrip_user = str(self.get_parameter("ntrip_user").value)
        self.ntrip_password = str(self.get_parameter("ntrip_password").value)
        self.ntrip_gga_period = float(
            self.get_parameter("ntrip_gga_period_sec").value
        )
        self.ntrip_reconnect = float(
            self.get_parameter("ntrip_reconnect_sec").value
        )

        self.fix_pub = self.create_publisher(
            NavSatFix, str(self.get_parameter("fix_topic").value), 10
        )
        self.nmea_pub = self.create_publisher(
            String, str(self.get_parameter("nmea_topic").value), 50
        )
        self.serial_rx_pub = self.create_publisher(
            UInt8MultiArray, str(self.get_parameter("serial_rx_topic").value), 20
        )
        self.serial_tx_pub = self.create_publisher(
            UInt8MultiArray, str(self.get_parameter("serial_tx_topic").value), 20
        )
        self.status_pub = self.create_publisher(
            String, str(self.get_parameter("status_topic").value), 10
        )

        self.serial_conn: Optional[serial.Serial] = None
        self.active_port = ""
        self.ntrip_socket: Optional[socket.socket] = None
        self.ntrip_header = bytearray()
        self.ntrip_connected = False
        self.ntrip_next_retry = 0.0
        self.last_gga: Optional[GGAFix] = None
        self.last_gga_sent = 0.0
        self.serial_buffer = bytearray()
        self.last_open_attempt = 0.0
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.nmea_count = 0
        self.rtcm_count = 0
        self.last_rx_time = 0.0
        self.last_error = ""

        self.read_timer = self.create_timer(self.read_period, self._poll)
        self.status_timer = self.create_timer(self.status_period, self._publish_status)
        self.get_logger().info(
            f"RTK 节点启动，串口={self.serial_port_param}，波特率={self.baudrate}，"
            f"NTRIP={'开启' if self.ntrip_enabled else '关闭'}"
        )

    def _port_candidates(self) -> Iterable[str]:
        if self.serial_port_param.lower() != "auto":
            return [self.serial_port_param]
        return serial_candidates()

    def _open_serial(self) -> None:
        now = time.monotonic()
        if self.serial_conn is not None or now < self.last_open_attempt:
            return
        self.last_open_attempt = now + self.reconnect_period
        candidates = list(self._port_candidates())
        if not candidates:
            self.last_error = "未找到 /dev/ttyACM*、/dev/ttyUSB* 或 by-id 串口"
            return
        for port in candidates:
            try:
                connection = serial.Serial(port, self.baudrate, timeout=0)
            except (OSError, serial.SerialException) as exc:
                self.last_error = f"打开 {port} 失败: {exc}"
                continue
            self.serial_conn = connection
            self.active_port = port
            self.last_error = ""
            self.get_logger().info(f"串口已打开: {port} @ {self.baudrate}")
            return

    def _close_serial(self) -> None:
        if self.serial_conn is not None:
            try:
                self.serial_conn.close()
            except OSError:
                pass
        self.serial_conn = None
        self.active_port = ""

    def _write_serial(self, payload: bytes) -> bool:
        if self.serial_conn is None or not payload:
            return False
        try:
            self.serial_conn.write(payload)
            self.tx_bytes += len(payload)
            message = UInt8MultiArray()
            message.data = list(payload)
            self.serial_tx_pub.publish(message)
            return True
        except (OSError, serial.SerialException) as exc:
            self.last_error = f"串口写入失败: {exc}"
            self._close_serial()
            return False

    def _poll(self) -> None:
        self._open_serial()
        self._read_serial()
        self._poll_ntrip()
        self._connect_ntrip_if_ready()
        self._send_gga_to_ntrip()

    def _read_serial(self) -> None:
        if self.serial_conn is None:
            return
        try:
            waiting = min(self.serial_conn.in_waiting, 8192)
            if waiting <= 0:
                return
            payload = self.serial_conn.read(waiting)
        except (OSError, serial.SerialException) as exc:
            self.last_error = f"串口读取失败: {exc}"
            self._close_serial()
            return
        if not payload:
            return
        self.rx_bytes += len(payload)
        self.last_rx_time = time.monotonic()
        raw = UInt8MultiArray()
        raw.data = list(payload)
        self.serial_rx_pub.publish(raw)
        self.serial_buffer.extend(payload)
        if len(self.serial_buffer) > 65536:
            self.serial_buffer = self.serial_buffer[-32768:]
        while b"\n" in self.serial_buffer:
            line, _, remainder = self.serial_buffer.partition(b"\n")
            self.serial_buffer = bytearray(remainder)
            sentence = line.decode("ascii", errors="ignore").strip()
            if not sentence.startswith("$"):
                continue
            self.nmea_pub.publish(String(data=sentence))
            self.nmea_count += 1
            gga = parse_gga(sentence)
            if gga is not None:
                self._publish_fix(gga)

    def _publish_fix(self, gga: GGAFix) -> None:
        self.last_gga = gga
        if gga.quality == 0 and not self.publish_invalid_fix:
            return
        message = NavSatFix()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self.frame_id
        message.status.status = navsat_status(gga.quality)
        message.status.service = NavSatStatus.SERVICE_GPS
        message.latitude = gga.latitude
        message.longitude = gga.longitude
        message.altitude = gga.altitude
        message.position_covariance_type = NavSatFix.COVARIANCE_TYPE_DIAGONAL_KNOWN
        horizontal = max(gga.hdop, 0.1) ** 2
        message.position_covariance = [
            horizontal,
            0.0,
            0.0,
            0.0,
            horizontal,
            0.0,
            0.0,
            0.0,
            horizontal * 2.0,
        ]
        self.fix_pub.publish(message)

    def _connect_ntrip_if_ready(self) -> None:
        if not self.ntrip_enabled or self.ntrip_socket is not None:
            return
        if time.monotonic() < self.ntrip_next_retry or self.last_gga is None:
            return
        if not all((self.ntrip_server, self.ntrip_mountpoint)):
            self.last_error = "NTRIP 已开启，但 server 或 mountpoint 为空"
            return
        self.ntrip_next_retry = time.monotonic() + self.ntrip_reconnect
        try:
            sock = socket.create_connection(
                (self.ntrip_server, self.ntrip_port), timeout=5.0
            )
            credentials = base64.b64encode(
                f"{self.ntrip_user}:{self.ntrip_password}".encode()
            ).decode()
            request = (
                f"GET /{self.ntrip_mountpoint} HTTP/1.0\r\n"
                "User-Agent: rtk_gps_driver/1.0\r\n"
                "Accept: */*\r\n"
                "Connection: keep-alive\r\n"
                f"Authorization: Basic {credentials}\r\n\r\n"
            ).encode()
            sock.sendall(request)
            sock.setblocking(False)
            self.ntrip_socket = sock
            self.ntrip_header.clear()
            self.ntrip_connected = False
            self.get_logger().info(
                f"已连接 NTRIP {self.ntrip_server}:{self.ntrip_port}/{self.ntrip_mountpoint}"
            )
        except OSError as exc:
            self.last_error = f"NTRIP 连接失败: {exc}"

    def _poll_ntrip(self) -> None:
        if self.ntrip_socket is None:
            return
        try:
            while True:
                payload = self.ntrip_socket.recv(8192)
                if not payload:
                    raise ConnectionError("NTRIP 服务器已关闭连接")
                if not self.ntrip_connected:
                    self.ntrip_header.extend(payload)
                    marker = self.ntrip_header.find(b"\r\n\r\n")
                    if marker < 0:
                        if len(self.ntrip_header) > 8192:
                            raise ConnectionError("NTRIP 响应头过大或格式错误")
                        continue
                    header = bytes(self.ntrip_header[:marker]).decode(
                        "ascii", errors="ignore"
                    )
                    body = bytes(self.ntrip_header[marker + 4 :])
                    if "200" not in header:
                        raise ConnectionError(f"NTRIP 返回非 200: {header.splitlines()[:1]}")
                    self.ntrip_connected = True
                    self.get_logger().info("NTRIP 认证成功，开始转发 RTCM")
                    if body:
                        self._forward_rtcm(body)
                else:
                    self._forward_rtcm(payload)
        except BlockingIOError:
            return
        except (OSError, ConnectionError) as exc:
            self.last_error = f"NTRIP 接收停止: {exc}"
            self._close_ntrip()

    def _forward_rtcm(self, payload: bytes) -> None:
        self.rtcm_count += len(payload)
        self._write_serial(payload)

    def _send_gga_to_ntrip(self) -> None:
        if not self.ntrip_connected or self.ntrip_socket is None or self.last_gga is None:
            return
        now = time.monotonic()
        if now - self.last_gga_sent < self.ntrip_gga_period:
            return
        try:
            self.ntrip_socket.sendall((self.last_gga.sentence + "\r\n").encode())
            self.last_gga_sent = now
        except OSError as exc:
            self.last_error = f"发送 GGA 到 NTRIP 失败: {exc}"
            self._close_ntrip()

    def _close_ntrip(self) -> None:
        if self.ntrip_socket is not None:
            try:
                self.ntrip_socket.close()
            except OSError:
                pass
        self.ntrip_socket = None
        self.ntrip_connected = False

    def _publish_status(self) -> None:
        status = {
            "serial_port": self.active_port,
            "baudrate": self.baudrate,
            "serial_connected": self.serial_conn is not None,
            "ntrip_enabled": self.ntrip_enabled,
            "ntrip_connected": self.ntrip_connected,
            "rx_bytes": self.rx_bytes,
            "tx_bytes": self.tx_bytes,
            "rtcm_bytes": self.rtcm_count,
            "nmea_sentences": self.nmea_count,
            "last_fix_quality": self.last_gga.quality if self.last_gga else None,
            "last_fix_status": quality_name(self.last_gga.quality)
            if self.last_gga
            else "NO_DATA",
            "last_error": self.last_error,
        }
        self.status_pub.publish(String(data=json.dumps(status, ensure_ascii=False)))

    def close(self) -> None:
        self._close_ntrip()
        self._close_serial()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RTKGPSNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
