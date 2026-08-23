# UE5 虚拟端 -> 实车控制指令
std_msgs/Header header

# 速度指令（线速度 m/s，角速度 rad/s）
geometry_msgs/Twist velocity_command

# 控制模式: manual, auto, emergency_stop
string control_mode

# 目标航点（可选）
geometry_msgs/PoseStamped[] target_waypoints
