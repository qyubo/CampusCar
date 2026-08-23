# 实车 -> UE5 虚拟端状态同步
std_msgs/Header header

# 机器人位姿
geometry_msgs/PoseStamped robot_pose

# 当前速度
geometry_msgs/Twist current_velocity

# 电池电量 [0.0, 100.0]
float32 battery_level

# 系统状态: idle, inspecting, navigating, charging, error
string system_status

# 最新检测到的缺陷
DefectArray recent_defects

# 路面点云数据（可选，按需发送）
sensor_msgs/PointCloud2 lidar_pointcloud
