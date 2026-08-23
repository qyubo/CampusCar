#!/usr/bin/env python3
"""
UE5 虚实双向桥接节点（对接 CampusBrain / ROSIntegration 插件）
- 实车 → UE5: 发布 /R2UTopic_Pos (geometry_msgs/Pose) 机器人位姿
- UE5 → 实车: 订阅 /U2RTopic_Command (geometry_msgs/Twist) 控制指令 → /cmd_vel
- 同时保留 /ue5/robot_state (pavement_interfaces/UE5State) 供 ROS2 内部使用
rosbridge_websocket 自动将 /R2UTopic_Pos 和 /U2RTopic_Command 桥接给 Windows 端 UE5
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Pose, Point, Quaternion, PoseStamped
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from pavement_interfaces.msg import DefectArray, UE5Command, UE5State


class UE5BridgeNode(Node):
    def __init__(self):
        super().__init__('ue5_bridge_node')

        # ── UE5 → 实车: 接收控制指令 ──
        # CampusBrain 通过 rosbridge 发布 /U2RTopic_Command (Twist)
        self.ue5_cmd_sub = self.create_subscription(
            Twist, '/U2RTopic_Command', self.ue5_command_callback, 10)
        # 兼容旧接口
        self.ue5_legacy_cmd_sub = self.create_subscription(
            UE5Command, '/ue5/command', self.ue5_legacy_command_callback, 10)
        # 转发到实际底盘
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # ── 实车 → UE5: 发送位姿 ──
        # CampusBrain 通过 rosbridge 订阅 /R2UTopic_Pos (Pose)
        self.r2u_pos_pub = self.create_publisher(Pose, '/R2UTopic_Pos', 10)
        # 同时保留旧接口
        self.ue5_state_pub = self.create_publisher(UE5State, '/ue5/robot_state', 10)

        # ── 订阅实车状态 ──
        # 标准命名（实车运行时）
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        # 兼容测试命名（ros2_test_publisher.py 发布的）
        self.vehicle_pose_sub = self.create_subscription(
            PoseStamped, '/vehicle/pose', self.vehicle_pose_callback, 10)
        
        self.defect_sub = self.create_subscription(
            DefectArray, '/perception/fused_defects', self.defect_callback, 10)
        self.pc_sub = self.create_subscription(
            PointCloud2, '/livox/pointcloud', self.pc_callback, 10)

        # 状态缓存
        self.robot_pose = PoseStamped()
        self.recent_defects = DefectArray()
        self.pointcloud = PointCloud2()

        # 定时发布（10Hz → UE5 端位姿更新）
        self.timer = self.create_timer(0.1, self.publish_state)

        self.get_logger().info('UE5 桥接节点已启动 (CampusBrain rosbridge 模式)')
        self.get_logger().info('  发送 → /R2UTopic_Pos (geometry_msgs/Pose)')
        self.get_logger().info('  接收 ← /U2RTopic_Command (geometry_msgs/Twist) → /cmd_vel')
        self.get_logger().info('  订阅 ← /odom 或 /vehicle/pose (兼容模式)')

    def ue5_command_callback(self, msg: Twist):
        """接收 CampusBrain 控制指令，转发到 /cmd_vel"""
        self.cmd_vel_pub.publish(msg)
        self.get_logger().debug(
            f'UE5指令: linear=({msg.linear.x:.2f},{msg.linear.y:.2f},{msg.linear.z:.2f}) '
            f'angular=({msg.angular.x:.2f},{msg.angular.y:.2f},{msg.angular.z:.2f})')

    def ue5_legacy_command_callback(self, msg: UE5Command):
        """兼容旧接口 pavement_interfaces/UE5Command"""
        if msg.control_mode == 'manual':
            self.cmd_vel_pub.publish(msg.velocity_command)
        elif msg.control_mode == 'emergency_stop':
            self.cmd_vel_pub.publish(Twist())

    def odom_callback(self, msg: Odometry):
        """标准 /odom 话题回调"""
        self.robot_pose.header = msg.header
        self.robot_pose.pose = msg.pose.pose

    def vehicle_pose_callback(self, msg: PoseStamped):
        """兼容 /vehicle/pose 话题回调（测试用）"""
        self.robot_pose = msg
        self.get_logger().debug(
            f'收到位姿: x={msg.pose.position.x:.2f}, '
            f'y={msg.pose.position.y:.2f}, z={msg.pose.position.z:.2f}')

    def defect_callback(self, msg: DefectArray):
        self.recent_defects = msg

    def pc_callback(self, msg: PointCloud2):
        self.pointcloud = msg

    def publish_state(self):
        """定时发布机器人状态到 UE5"""
        # 1. 发送 Pose 到 CampusBrain (主通道)
        pose_msg = Pose()
        pose_msg.position = self.robot_pose.pose.position
        pose_msg.orientation = self.robot_pose.pose.orientation
        self.r2u_pos_pub.publish(pose_msg)

        # 2. 保留旧接口 UE5State
        state_msg = UE5State()
        state_msg.header.stamp = self.get_clock().now().to_msg()
        state_msg.robot_pose = self.robot_pose
        state_msg.system_status = 'inspecting'
        state_msg.battery_level = 85.0
        state_msg.recent_defects = self.recent_defects
        state_msg.lidar_pointcloud = self.pointcloud
        self.ue5_state_pub.publish(state_msg)


def main(args=None):
    rclpy.init(args=args)
    node = UE5BridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
