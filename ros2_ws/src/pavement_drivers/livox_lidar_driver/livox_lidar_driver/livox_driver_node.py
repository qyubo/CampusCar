#!/usr/bin/env python3
"""
Livox Mid-360S 雷达驱动节点
- 对接 Livox SDK，输出标准化的 3D 点云话题
- 发布: /livox/pointcloud (sensor_msgs/PointCloud2)
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
import struct


class LivoxDriverNode(Node):
    def __init__(self):
        super().__init__('livox_driver_node')
        
        # 参数声明
        self.declare_parameter('device_ip', '192.168.1.100')
        self.declare_parameter('data_port', 56000)
        self.declare_parameter('frame_id', 'livox_frame')
        self.declare_parameter('publish_rate', 10.0)
        
        # 获取参数
        self.device_ip = self.get_parameter('device_ip').value
        self.data_port = self.get_parameter('data_port').value
        self.frame_id = self.get_parameter('frame_id').value
        self.publish_rate = self.get_parameter('publish_rate').value
        
        # 发布点云
        self.pointcloud_pub = self.create_publisher(PointCloud2, '/livox/pointcloud', 10)
        
        # 定时器（占位，实际应该在回调中发布）
        self.timer = self.create_timer(1.0 / self.publish_rate, self.publish_pointcloud)
        
        # TODO: 初始化 Livox SDK 连接
        self.get_logger().info(f'Livox 雷达驱动节点已启动，设备IP: {self.device_ip}')
        self.get_logger().warn('当前为占位模式，需要对接 Livox SDK')
    
    def publish_pointcloud(self):
        """发布点云数据（占位，实际需要从SDK获取）"""
        msg = PointCloud2()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        
        # 点云字段定义: x, y, z, intensity
        msg.fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name='intensity', offset=12, datatype=PointField.FLOAT32, count=1),
        ]
        
        msg.point_step = 16
        msg.height = 1
        msg.width = 0  # TODO: 实际点数
        msg.is_bigendian = False
        msg.is_dense = True
        msg.row_step = msg.point_step * msg.width
        msg.data = b''  # TODO: 实际点云数据
        
        self.pointcloud_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = LivoxDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
