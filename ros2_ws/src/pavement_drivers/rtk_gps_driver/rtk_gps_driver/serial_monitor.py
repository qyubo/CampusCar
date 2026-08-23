#!/usr/bin/env python3
"""Terminal monitor for inspecting GNSS NMEA and binary RTCM serial traffic."""

import argparse
import glob
import sys
import time

import serial

from .nmea import parse_gga, quality_name


def candidates() -> list[str]:
    paths: list[str] = []
    for pattern in (
        "/dev/serial/by-id/*if00",
        "/dev/serial/by-id/*",
        "/dev/ttyACM*",
        "/dev/ttyUSB*",
    ):
        for path in sorted(glob.glob(pattern)):
            if path not in paths:
                paths.append(path)
    return paths


def open_port(path: str, baudrate: int) -> tuple[serial.Serial, str]:
    paths = candidates() if path.lower() == "auto" else [path]
    if not paths:
        raise RuntimeError("没有找到可用的 USB 串口")
    errors = []
    for candidate in paths:
        try:
            return serial.Serial(candidate, baudrate, timeout=0.2), candidate
        except (OSError, serial.SerialException) as exc:
            errors.append(f"{candidate}: {exc}")
    raise RuntimeError("所有串口均无法打开:\n  " + "\n  ".join(errors))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="auto", help="串口路径，默认 auto")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--duration", type=float, default=0.0, help="运行秒数，0 表示持续")
    parser.add_argument("--send-text", action="append", default=[], help="打开后发送文本，可重复")
    parser.add_argument("--send-hex", action="append", default=[], help="打开后发送十六进制，如 47 50")
    parser.add_argument("--quiet-raw", action="store_true", help="只显示 NMEA、统计和状态")
    args = parser.parse_args(argv)

    try:
        connection, port = open_port(args.port, args.baudrate)
    except (RuntimeError, serial.SerialException) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    print(f"✅ 已打开 {port} @ {args.baudrate}")
    print("按 Ctrl+C 退出；NMEA 显示为文本，RTCM/二进制显示为 HEX。")
    for text in args.send_text:
        payload = text.encode()
        connection.write(payload)
        print(f"TX TEXT {len(payload)} bytes: {text!r}")
    for value in args.send_hex:
        payload = bytes.fromhex(value)
        connection.write(payload)
        print(f"TX HEX {len(payload)} bytes: {payload.hex(' ')}")

    started = time.monotonic()
    total = 0
    lines = 0
    last_report = started
    try:
        while not args.duration or time.monotonic() - started < args.duration:
            payload = connection.read(4096)
            if payload:
                total += len(payload)
                if not args.quiet_raw:
                    text = payload.decode("ascii", errors="replace").replace("\r", "\\r").replace("\n", "\\n")
                    print(f"RX {len(payload)} bytes: {text} | HEX {payload.hex(' ')}", flush=True)
                for line in payload.splitlines():
                    sentence = line.decode("ascii", errors="ignore").strip()
                    if not sentence.startswith("$"):
                        continue
                    lines += 1
                    fix = parse_gga(sentence)
                    if fix:
                        print(
                            f"NMEA GGA: lat={fix.latitude:.8f} lon={fix.longitude:.8f} "
                            f"alt={fix.altitude:.2f} quality={quality_name(fix.quality)} "
                            f"sat={fix.satellites} hdop={fix.hdop}",
                            flush=True,
                        )
            if time.monotonic() - last_report >= 5.0:
                print(f"STATUS: RX={total} bytes, NMEA={lines} sentences", flush=True)
                last_report = time.monotonic()
    except KeyboardInterrupt:
        print("\n已退出。")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
