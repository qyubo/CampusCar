# 缺陷演化预测
std_msgs/Header header

# 关联的缺陷ID
string defect_id

# 当前时间戳
builtin_interfaces/Time current_time

# 预测的未来尺寸（多个时间点）
geometry_msgs/Vector3[] predicted_dimensions
builtin_interfaces/Time[] prediction_timestamps

# 风险等级随时间变化
string[] risk_levels

# 推荐养护时间
builtin_interfaces/Time recommended_maintenance_time

# 预测置信度
float32 prediction_confidence
