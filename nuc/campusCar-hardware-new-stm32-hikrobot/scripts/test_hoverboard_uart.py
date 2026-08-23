#!/usr/bin/env python3
"""
CampusCar 电调 UART 测试脚本
用途: 直接通过 USB 转 TTL 向 hoverboard 电调发送 0xABCD 命令帧
硬件: NUC → USB 转 TTL → 电调 UART
协议: hoverboard-firmware-hack-FOC 0xABCD 协议

使用方法:
    在 NUC 上运行:
        python3 scripts/test_hoverboard_uart.py

    或指定端口:
        python3 scripts/test_hoverboard_uart.py --port /dev/ttyUSB0
"""

import serial
import struct
import time
import argparse
import sys


class HoverboardTest:
    """hoverboard 电调 UART 测试器"""

    def __init__(self, port: str, baudrate: int = 115200):
        self.serial = serial.Serial(port, baudrate, timeout=1)
        self.running = True
        print(f"已连接到 {port} @ {baudrate} baud")

    def send_command(self, steer: int = 0, speed: int = 0):
        """
        发送 hoverboard 命令帧
        参数范围: steer: -1000~1000 (右负左正), speed: -1000~1000 (后退负前进正)
        协议帧格式 (小端序, 8 字节):
            [start_lo, start_hi, steer_lo, steer_hi, speed_lo, speed_hi, chk_lo, chk_hi]
        """
        # 限制范围
        steer = max(-1000, min(1000, steer))
        speed = max(-1000, min(1000, speed))

        # 校验和 = start ^ steer ^ speed (XOR, 与 hoverboard 标准协议及 NUC C++ 驱动一致)
        # 注意: Python 中负数需用 & 0xFFFF 截断为 16 位无符号, 等价于 C 的 (uint16_t)int16_t
        checksum = (0xABCD ^ (steer & 0xFFFF) ^ (speed & 0xFFFF)) & 0xFFFF

        # 小端序打包: H=uint16, h=int16
        frame = struct.pack('<HhhH', 0xABCD, steer, speed, checksum)

        # 发送
        self.serial.write(frame)
        return frame

    def read_feedback(self):
        """
        读取电调返回的反馈帧 (SerialFeedbackCompact, 16 字节)
        如果没有数据返回 None
        """
        if self.serial.in_waiting >= 16:
            data = self.serial.read(16)
            if len(data) == 16:
                # 解析 (小端序)
                start = struct.unpack_from('<H', data, 0)[0]
                cmd1 = struct.unpack_from('<h', data, 2)[0]
                cmd2 = struct.unpack_from('<h', data, 4)[0]
                speed_r = struct.unpack_from('<h', data, 6)[0]
                speed_l = struct.unpack_from('<h', data, 8)[0]
                bat_voltage = struct.unpack_from('<h', data, 10)[0]
                board_temp = struct.unpack_from('<h', data, 12)[0]
                cmd_led = struct.unpack_from('<H', data, 14)[0]

                if start == 0xABCD:
                    return {
                        'valid': True,
                        'start': f'0x{start:04X}',
                        'cmd1': cmd1,
                        'cmd2': cmd2,
                        'speed_r': speed_r,
                        'speed_l': speed_l,
                        'bat_voltage': bat_voltage,
                        'board_temp': board_temp,
                        'cmd_led': cmd_led,
                    }
        return None

    def drive_sequence(self):
        """执行测试序列: 停止 → 慢速前进 → 中速前进 → 停车 → 后退 → 停车 → 左转 → 停车 → 右转 → 停车"""
        sequence = [
            # (steer, speed, description, duration)
            (0, 0, "初始停车", 2),
            (0, 300, "慢速前进", 2),
            (0, 500, "中速前进", 2),
            (0, 0, "停车", 1),
            (0, -300, "慢速后退", 2),
            (0, 0, "停车", 1),
            (500, 0, "原地左转", 1),
            (0, 0, "停车", 1),
            (-500, 0, "原地右转", 1),
            (0, 0, "最终停车", 2),
        ]

        for steer, speed, desc, duration in sequence:
            print(f"\n>>> {desc} (steer={steer}, speed={speed})")
            self.send_command(steer, speed)
            time.sleep(0.1)  # 等待反馈

            # 读取反馈
            feedback = self.read_feedback()
            if feedback:
                print(f"    反馈: bat={feedback['bat_voltage']}V, temp={feedback['board_temp']}°C, "
                      f"speed_r={feedback['speed_r']}, speed_l={feedback['speed_l']}")
            else:
                print("    (无反馈)")

            time.sleep(duration)

        print("\n✅ 测试序列完成！")

    def interactive_mode(self):
        """交互模式: 通过键盘输入控制"""
        print("\n🎮 交互模式 (输入 q 退出, s 停车)")
        print("   格式: steer speed  (例如: 0 500 表示直行中速)")
        print("   范围: steer/speed 都是 -1000~1000")

        while self.running:
            try:
                cmd = input("\n> ").strip()
                if cmd == 'q':
                    break
                elif cmd == 's':
                    self.send_command(0, 0)
                    print("已停车")
                    continue
                elif cmd == 'test':
                    self.drive_sequence()
                    continue

                parts = cmd.split()
                if len(parts) == 2:
                    steer = int(parts[0])
                    speed = int(parts[1])
                    self.send_command(steer, speed)
                    print(f"已发送: steer={steer}, speed={speed}")

                    # 读取反馈
                    time.sleep(0.05)
                    feedback = self.read_feedback()
                    if feedback:
                        print(f"    反馈: bat={feedback['bat_voltage']}V, temp={feedback['board_temp']}°C, "
                              f"speed_r={feedback['speed_r']}, speed_l={feedback['speed_l']}")

            except ValueError as e:
                print(f"格式错误: {e}")
            except KeyboardInterrupt:
                print("\n正在停车并退出...")
                self.send_command(0, 0)
                self.running = False

    def close(self):
        """关闭串口"""
        self.send_command(0, 0)  # 安全停车
        self.serial.close()
        print("串口已关闭")


def main():
    parser = argparse.ArgumentParser(description='CampusCar hoverboard 电调 UART 测试')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='串口设备路径')
    parser.add_argument('--baudrate', type=int, default=115200, help='波特率')
    parser.add_argument('--mode', choices=['test', 'interactive'], default='test',
                        help='运行模式: test=自动测试序列, interactive=交互模式')
    args = parser.parse_args()

    # 检查串口权限
    try:
        tester = HoverboardTest(args.port, args.baudrate)
    except PermissionError:
        print(f"❌ 无权限访问 {args.port}")
        print("请运行: sudo usermod -aG dialout $USER")
        print("然后重新登录或运行: sudo chmod 666 {args.port}")
        sys.exit(1)
    except serial.SerialException as e:
        print(f"❌ 无法打开串口: {e}")
        print("请检查:")
        print("  1. USB 转 TTL 是否已插入")
        print("  2. 设备路径是否正确 (在 NUC 上用 ls /dev/ttyUSB* 查看)")
        print("  3. 权限是否足够")
        sys.exit(1)

    try:
        if args.mode == 'test':
            print("\n⚠️  请确保车轮悬空！")
            input("按回车键开始测试序列...")
            tester.drive_sequence()
        else:
            tester.interactive_mode()
    finally:
        tester.close()


if __name__ == '__main__':
    main()
