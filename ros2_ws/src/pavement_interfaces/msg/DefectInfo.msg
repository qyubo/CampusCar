# 路面缺陷信息
std_msgs/Header header

# 缺陷唯一标识
string defect_id

# 缺陷类型: crack, pothole, rutting, depression, manhole_cover
string defect_type

# 缺陷位置（世界坐标系）
geometry_msgs/Point position

# 缺陷三维尺寸 (length, width, depth in meters)
geometry_msgs/Vector3 dimensions

# 置信度 [0.0, 1.0]
float32 confidence

# 检测来源: lidar, vision, fusion
string detection_source

# 严重程度等级: low, medium, high, critical
string severity_level

# 附加属性（JSON格式）
string attributes
