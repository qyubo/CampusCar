# 路况综合信息
std_msgs/Header header

# 查询区域中心点
geometry_msgs/Point center

# 查询半径（米）
float32 radius

# 该区域内的缺陷列表
DefectInfo[] defects

# 整体路况评分 [0.0, 10.0]
float32 road_quality_score

# 通行建议: safe, caution, avoid
string traffic_advice
