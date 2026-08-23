# Orbbec RGBD 相机与缺陷识别操作说明

本文档记录 Orbbec Gemini 336L RGBD 相机接入 ROS2、调用缺陷识别模型、打开实时图像窗口的常用操作。

## 一、窗口地址

原始相机画面：

```text
http://localhost:8088/
```

缺陷识别结果：

```text
http://localhost:8089/
```

对应 ROS2 话题：

```text
/camera/color/image_raw
/perception/detection_image
/perception/vision_defects
/perception/geolocated_vision_defects
```

## 二、一键控制脚本

控制脚本位置：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh
```

### 启动全部

启动 Orbbec 相机、缺陷识别模型、原始画面窗口和识别结果窗口：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh start
```

启动后打开：

```text
http://localhost:8088/
http://localhost:8089/
```

### 停止全部

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh stop
```

### 重启全部

如果窗口显示异常、服务不可用、图像不刷新，优先执行：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh restart
```

### 查看状态

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh status
```

正常时应看到类似：

```text
/camera/color/image_raw        Publisher count: 1
/perception/detection_image    Publisher count: 1
/perception/vision_defects     Publisher count: 1
```

### 查看窗口地址

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh open
```

### 查看日志

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh logs
```

日志目录：

```bash
/tmp/cyberluban_orbbec_defect_logs
```

## 三、手动启动命令

一般使用一键控制脚本即可。下面命令仅用于调试。

### 1. 启动 Orbbec 相机并回传 ROS2

```bash
source /opt/ros/humble/setup.bash
ros2 launch orbbec_camera orbbec_camera.launch.py camera_model:=gemini330_series usb_port:=3-1 enable_depth:=true enable_color:=true
```

相机成功连接时会看到类似：

```text
Device Orbbec Gemini 336L connected
color Frame - Width: 1280 Height: 720 fps: 10 Format: MJPG
depth Frame - Width: 1280 Height: 720 fps: 10 Format: Y16
```

### 2. 启动缺陷识别模型

```bash
source /opt/ros/humble/setup.bash
source /tmp/cyberluban_cri_install/setup.bash
export PYTHONPATH=/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/src/cri_perception/vision_defect_detector:$PYTHONPATH
python3 -m vision_defect_detector.vision_defect_detector_node --ros-args \
  -p image_topic:=/camera/color/image_raw \
  -p model_path:=/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/demo/models/road_damage_yolov8.pt \
  -p confidence_threshold:=0.25 \
  -p input_size:=640 \
  -p device:=cpu \
  -p enable_visualization:=true
```

模型成功启动时会看到类似：

```text
YOLO 模型加载成功
订阅图像: /camera/color/image_raw
发布: /perception/vision_defects, /perception/detection_image
```

### 3. 启动原始图像窗口

```bash
source /opt/ros/humble/setup.bash
python3 /tmp/orbbec_web_viewer.py
```

打开：

```text
http://localhost:8088/
```

### 4. 启动缺陷识别结果窗口

```bash
source /opt/ros/humble/setup.bash
source /tmp/cyberluban_cri_install/setup.bash
python3 /tmp/orbbec_detection_web_viewer.py
```

打开：

```text
http://localhost:8089/
```

## 四、缺陷地理定位链路

新增的地理定位节点用于把视觉缺陷从像素点转成地面点，再映射到 GPS。

### 启动方式

推荐直接走感知总启动文件：

```bash
ros2 launch cri_bringup perception.launch.py
```

或单独启动地理定位节点：

```bash
ros2 launch sensor_fusion geolocation.launch.py
```

### 输入话题

```text
/perception/vision_defects
/camera/color/camera_info
/fix
/servo_command
/rtk/status
```

### 输出话题

```text
/perception/geolocated_vision_defects
```

### 当前接口约定

- 相机外参按三个舵机档位分组配置
- 先不硬编码真实角度
- 以 `[x, y, z, roll, pitch, yaw]` 表示位姿
- 平移单位是 m，角度默认按 `deg` 解释，可通过 `pose_angle_unit` 改成 `rad`
- 外参矩阵必须是 `T_camera_to_base`，也就是“相机坐标系 -> 机器人基座坐标系”
- `ground_plane_z` 代表机器人基座坐标系中的地面高度，通常填 `0.0`
- 像素点先反投影到地面，再映射到经纬度
- 缺陷框四个角也会做投影，用于估算实际地面大小
- 若缺少 RTK、内参或外参，仍会透传缺陷，并在 `attributes` 里标记原因

### 参数文件

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/src/cri_perception/sensor_fusion/config/geolocation_params.yaml
```

### 你需要先确认的标定项

- 相机内参：`/camera/color/camera_info`
- 舵机三个档位的外参：`servo_pose_tfs_json`
- 外参方向：必须确认是 `T_camera_to_base`
- 地面高度：`ground_plane_z`
- 角度单位：`pose_angle_unit`
- RTK 航向：当前先用 `heading_deg` 占位，后续可接 IMU 或实时航向

### 启动后验证

先看数据是否到了：

```bash
ros2 topic echo /fix --once
ros2 topic echo /camera/color/camera_info --once
ros2 topic echo /perception/vision_defects --once
ros2 topic echo /perception/geolocated_vision_defects --once
```

如果 `/perception/geolocated_vision_defects` 里出现：

- `geolocation_status: ok`
- `ground_point_base_m`
- `gps_lat_lon_alt`
- `projected_bbox_ground_m`
- `actual_bbox_size_m`

说明投影链路已经跑通。

### 结果字段说明

- `position.x = longitude`
- `position.y = latitude`
- `position.z = altitude`
- `dimensions.x / dimensions.y` 可写入投影后的地面实际尺寸
- `attributes` 里会附带：
  - `ground_point_base_m`
  - `gps_lat_lon_alt`
  - `projected_bbox_ground_m`
  - `actual_bbox_size_m`

## 五、固定经纬度线路跟随

如果你的线路是固定的，推荐直接用固定经纬度航点跟随接口。

### 启动方式

```bash
ros2 launch cri_bringup algorithm.launch.py
```

这个启动文件里会同时启动：
- 世界模型
- 动态路面地图
- 固定经纬度线路跟随节点

### 航点配置文件

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/src/cri_algorithm/dynamic_roadmap/config/fixed_waypoint_follower_params.yaml
```

### 你需要填的内容

把里面的 `waypoints_json` 改成你的固定线路，例如：

```yaml
waypoints_json: >-
  [
    [30.123456, 114.123456],
    [30.123500, 114.123600]
  ]
```

格式支持：
- `[latitude, longitude]`
- `{latitude: xx, longitude: yy}`

### 运行逻辑

- 节点订阅 `/fix`
- 实时知道小车当前位置
- 逐个对齐固定航点
- 通过 `/cmd_vel` 控制底盘前进
- 到达一个点后自动切下一个点

### 当前的能力边界

这条接口已经够你先用固定路线跑起来，但如果要更稳，需要后面再补：
- 航向角更准确的来源
- 更好的速度控制
- 到点停靠判定
- 转弯减速策略

## 六、手动停止命令

### 停止全部相关进程

```bash
pkill -f "orbbec_camera"
pkill -f "component_container"
pkill -f "vision_defect_detector"
pkill -f "orbbec_web_viewer"
pkill -f "orbbec_detection_web_viewer"
```

### 只停止显示窗口

```bash
pkill -f "orbbec_web_viewer"
pkill -f "orbbec_detection_web_viewer"
```

### 只停止识别模型

```bash
pkill -f "vision_defect_detector"
```

### 只停止相机驱动

```bash
pkill -f "orbbec_camera"
pkill -f "component_container"
```

## 七、常用检查命令

### 查看相机是否被 USB 识别

```bash
lsusb | grep -iE "orbbec|2bc5"
```

正常设备示例：

```text
Orbbec Gemini 336L
```

### 查看 ROS2 图像话题

```bash
source /opt/ros/humble/setup.bash
ros2 topic list | grep -E "camera|perception"
```

### 查看原始相机话题状态

```bash
source /opt/ros/humble/setup.bash
ros2 topic info /camera/color/image_raw
```

正常应包含：

```text
Publisher count: 1
```

### 查看识别结果图像话题状态

```bash
source /opt/ros/humble/setup.bash
source /tmp/cyberluban_cri_install/setup.bash
ros2 topic info /perception/detection_image
```

正常应包含：

```text
Publisher count: 1
```

### 查看缺陷识别消息

```bash
source /opt/ros/humble/setup.bash
source /tmp/cyberluban_cri_install/setup.bash
ros2 topic echo /perception/vision_defects --once
```

如果输出：

```yaml
defects: []
```

表示模型正在运行，但当前画面没有检测到缺陷目标。

## 八、导航接口说明

你说的“发一串经纬度坐标，让机器人沿着这些点动”，是可以做的，而且现在已经有一个固定航点跟随接口雏形。

### 现有基础

- 底盘驱动订阅 `/cmd_vel`
- 底盘发布 `/odom` 和 `/chassis_pose`
- RTK 发布 `/fix`
- 动态路面地图节点已有缺陷查询和绕行服务

### 可行实现方式

#### 方案 A：自定义经纬度跟随节点

输入一串经纬度点，例如：

```json
[
  [30.123456, 114.123456],
  [30.123500, 114.123600]
]
```

节点内部做三步：
1. 用 `/fix` 作为当前位置
2. 把目标经纬度转成本地 ENU/平面坐标
3. 生成 `/cmd_vel` 或路径点，驱动底盘前进

这条路最直接，也最适合你现在这套 RTK + 底盘架构。

#### 方案 B：接 Nav2

如果后面要做更完整的路径规划、避障、到点停靠，就把经纬度先转成本地地图坐标，再交给 Nav2 的 waypoint / navigate 接口。

### 目前的结论

- **可以做接口**
- **可以先按经纬度列表输入**
- **现在更适合先做“经纬度 -> 本地坐标 -> 底盘运动”接口**
- 如果要“真正沿点自动导航”，还需要：
  - 实时航向角
  - 当前定位融合
  - 目标点容差
  - 速度控制逻辑
  - 可能的避障逻辑

如果你愿意，我下一步可以直接给你补一个“经纬度 waypoint 跟随节点”的接口骨架。

## 六、故障处理

### 1. 8089 显示服务不可用

优先执行：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh restart
```

然后检查：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh status
```

### 2. 画面不刷新

检查图像帧接口：

```bash
curl -I http://localhost:8088/frame.jpg
curl -I http://localhost:8089/frame.jpg
```

正常应返回：

```text
HTTP/1.0 200 OK
Content-Type: image/jpeg
```

### 3. 相机打开失败或 UVC 报错

先停止旧进程：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh stop
```

再重新启动：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh start
```

如果仍失败，检查是否有旧进程占用：

```bash
ps -ef | grep -iE "orbbec_camera|component_container|vision_defect_detector" | grep -v grep
```

### 4. USB 权限问题

如果日志中出现 USB 权限或 `uvc_open failed`，确认 udev 规则已生效：

```bash
sudo cp /opt/ros/humble/share/orbbec_camera/udev/99-obsensor-libusb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

执行后拔插一次相机。

临时授权方式：

```bash
sudo chmod a+rw /dev/bus/usb/003/002
```

注意：设备路径可能随拔插变化，实际路径以 `lsusb` 和 `/dev/bus/usb/` 为准。

## 七、开机自启动

### 自启动服务部署

将视觉链路设置为开机自启动：

```bash
sudo cp /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_autostart.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now orbbec_defect_autostart.service
```

执行后，系统每次启动时会自动运行 Orbbec 相机和缺陷识别链路。

### 自启动服务管理

查看服务状态：

```bash
systemctl status orbbec_defect_autostart.service
```

查看是否已设置开机自启：

```bash
systemctl is-enabled orbbec_defect_autostart.service
```

启动服务：

```bash
sudo systemctl start orbbec_defect_autostart.service
```

停止服务：

```bash
sudo systemctl stop orbbec_defect_autostart.service
```

重启服务：

```bash
sudo systemctl restart orbbec_defect_autostart.service
```

取消开机自启：

```bash
sudo systemctl disable orbbec_defect_autostart.service
```

查看系统日志：

```bash
journalctl -u orbbec_defect_autostart.service -f
```

### 自启动逻辑说明

自启动链路由三层组成：

1. **systemd 服务**：`/etc/systemd/system/orbbec_defect_autostart.service`
   - 开机后由 systemd 启动
   - 以用户 `qyb413` 身份运行
   - 失败后会自动重启（`Restart=always`）

2. **自启动脚本**：`/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_autostart.sh`
   - 调用一键控制脚本启动全部服务
   - 保持运行状态，不退出

3. **一键控制脚本**：`/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/orbbec_defect_control.sh`
   - 启动 Orbbec 相机节点（ROS2 launch）
   - 启动缺陷识别模型节点
   - 启动原始画面网页服务（8088 端口）
   - 启动识别结果网页服务（8089 端口）

启动顺序：

```text
系统开机
  -> systemd 启动 orbbec_defect_autostart.service
  -> 运行 orbbec_defect_autostart.sh
  -> 调用 orbbec_defect_control.sh start
  -> 启动相机（等待 6 秒）
  -> 启动识别模型
  -> 启动两个网页服务
  -> 自动发布 /camera/color/image_raw
  -> 自动发布 /perception/detection_image 和 /perception/vision_defects
```

开机后等待约 10-15 秒，浏览器打开 `http://localhost:8088/` 和 `http://localhost:8089/` 即可看到实时画面。

### 检查开机自启动是否生效

查看 ROS2 节点：

```bash
source /opt/ros/humble/setup.bash
ros2 node list
```

应看到：

```text
/camera/camera
/camera/camera_container
/vision_defect_detector_node
/orbbec_web_jpeg_viewer
/orbbec_detection_web_viewer
```

查看图像话题：

```bash
ros2 topic info /camera/color/image_raw
```

应看到：

```text
Publisher count: 1
Subscription count: 2
```

查看图像频率：

```bash
ros2 topic hz /camera/color/image_raw
```

正常应输出实时频率（例如 `average rate: 30.0`）。

## 八、相机标定

### 为什么需要标定

为了把图像中的缺陷像素坐标转换为真实世界的地面坐标（结合 RTK GPS 得到经纬度），需要标定相机的内参和畸变系数。

标定内容：
- **内参矩阵 K**：焦距 fx, fy，光心 cx, cy
- **畸变系数**：径向畸变 k1, k2, k3，切向畸变 p1, p2

### 准备棋盘格标定板

打印一个棋盘格标定板：
- **内角点数量**：8x6（9x7 格子）
- **方格大小**：25mm x 25mm
- **打印要求**：
  - 使用 A4 纸打印
  - 贴在硬纸板或亚克力板上保持平整
  - 方格边界清晰，黑白对比度高

在线生成棋盘格：https://calib.io/pages/camera-calibration-pattern-generator

### 运行标定脚本

确保相机正在运行：

```bash
systemctl status orbbec_defect_autostart.service
```

或手动启动：

```bash
source /opt/ros/humble/setup.bash
source /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/install/setup.bash
ros2 launch hikrobot_camera orbbec_camera.launch.py
```

启动标定工具：

```bash
/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/scripts/calibrate_orbbec_camera.sh
```

### 标定步骤

1. **移动棋盘格**：
   - 在相机前移动棋盘格到不同位置（左、右、上、下）
   - 改变距离（远、近）
   - 改变角度（倾斜、旋转）

2. **观察指示条**：
   - **X**：不同 X 位置（左右移动）
   - **Y**：不同 Y 位置（上下移动）
   - **Size**：不同距离（前后移动）
   - **Skew**：不同倾斜角度

3. **开始标定**：
   - 等待所有指示条变绿
   - 点击 `CALIBRATE` 按钮
   - 等待计算完成（约 10-30 秒）

4. **保存结果**：
   - 点击 `SAVE` 按钮
   - 标定文件会自动保存到配置目录

### 应用标定结果

标定完成后，修改配置文件：

```bash
nano /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/src/cri_drivers/hikrobot_camera/config/orbbec_params.yaml
```

修改 `camera_info_url` 参数：

```yaml
camera_info_url: "/home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/src/cri_drivers/hikrobot_camera/config/orbbec_color_camera_info.yaml"
```

重新编译并重启：

```bash
cd /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src
colcon build --packages-select hikrobot_camera
sudo systemctl restart orbbec_defect_autostart.service
```

验证标定是否生效：

```bash
source /opt/ros/humble/setup.bash
source /home/qyb413/CyberLuban/nuc/robot/ros2_workspace_src/install/setup.bash
ros2 topic echo --once /camera/color/camera_info
```

应该看到内参矩阵 `k` 和畸变系数 `d` 有非零值。

## 九、ROS2 可视化工具

### 使用 RViz 查看图像

安装 RViz（如果未安装）：

```bash
sudo apt update
sudo apt install ros-humble-rviz2 -y
```

启动 RViz：

```bash
source /opt/ros/humble/setup.bash
rviz2
```

在 RViz 中添加图像显示：

1. 点击左下角 `Add`
2. 选择 `By topic`
3. 找到 `/camera/color/image_raw` 或 `/perception/detection_image`
4. 选择 `Image` 类型
5. 点击 `OK`

### 使用 rqt_image_view 查看图像

安装 rqt_image_view：

```bash
sudo apt update
sudo apt install ros-humble-rqt-image-view -y
```

启动 rqt_image_view：

```bash
source /opt/ros/humble/setup.bash
ros2 run rqt_image_view rqt_image_view
```

在下拉菜单中选择话题：
- `/camera/color/image_raw`：原始相机画面
- `/perception/detection_image`：缺陷识别标注画面

### 使用 rqt 查看话题和节点

安装完整 rqt 工具集：

```bash
sudo apt update
sudo apt install ros-humble-rqt* -y
```

启动 rqt：

```bash
source /opt/ros/humble/setup.bash
rqt
```

常用插件：
- `Plugins -> Topics -> Topic Monitor`：监控话题发布频率
- `Plugins -> Visualization -> Image View`：查看图像
- `Plugins -> Introspection -> Node Graph`：查看节点拓扑

## 九、当前链路

```text
Orbbec Gemini 336L
  -> /camera/color/image_raw
  -> vision_defect_detector_node
  -> /perception/vision_defects
  -> /perception/detection_image
  -> Web 实时窗口 8088/8089
```
