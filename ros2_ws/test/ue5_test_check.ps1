# UE5虚实联动测试 - Windows端快速检查脚本
# 使用方法: 在PowerShell中运行此脚本

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "UE5虚实联动测试 - 环境检查工具" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查UE5工程是否存在
Write-Host "[1/5] 检查UE5工程..." -ForegroundColor Yellow
$UEProjectPath = "C:\Users\xzx15\Desktop\CyberLuban\CyberLubanTwin\CyberLubanTwin.uproject"
if (Test-Path $UEProjectPath) {
    Write-Host "  ✓ UE5工程文件存在" -ForegroundColor Green
} else {
    Write-Host "  ✗ UE5工程文件未找到: $UEProjectPath" -ForegroundColor Red
}

# 2. 提示输入Ubuntu IP地址
Write-Host ""
Write-Host "[2/5] 网络连通性测试..." -ForegroundColor Yellow
$UbuntuIP = Read-Host "  请输入Ubuntu机器的IP地址 (例如: 192.168.1.100)"

if ($UbuntuIP) {
    # Ping测试
    Write-Host "  测试网络连通性..." -ForegroundColor Gray
    $pingResult = Test-Connection -ComputerName $UbuntuIP -Count 2 -Quiet
    
    if ($pingResult) {
        Write-Host "  ✓ 网络连通正常 (Ping成功)" -ForegroundColor Green
        
        # 测试9090端口（rosbridge）
        Write-Host "  测试rosbridge端口(9090)..." -ForegroundColor Gray
        $portTest = Test-NetConnection -ComputerName $UbuntuIP -Port 9090 -WarningAction SilentlyContinue
        
        if ($portTest.TcpTestSucceeded) {
            Write-Host "  ✓ rosbridge端口可访问 (9090端口开放)" -ForegroundColor Green
            Write-Host "  → Ubuntu端rosbridge已启动" -ForegroundColor Cyan
        } else {
            Write-Host "  ✗ 无法连接到9090端口" -ForegroundColor Red
            Write-Host "  → 请在Ubuntu端启动rosbridge:" -ForegroundColor Yellow
            Write-Host "    ros2 launch rosbridge_server rosbridge_websocket_launch.xml" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ✗ 网络不通 (Ping失败)" -ForegroundColor Red
        Write-Host "  → 请确认Ubuntu机器在线且IP地址正确" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ 跳过网络测试" -ForegroundColor Yellow
}

# 3. 检查ROS2工作空间
Write-Host ""
Write-Host "[3/5] 检查ROS2工作空间..." -ForegroundColor Yellow
$ROS2Workspace = "C:\Users\xzx15\Desktop\CyberLuban\campus_road_inspection_ws"
if (Test-Path $ROS2Workspace) {
    Write-Host "  ✓ ROS2工作空间存在" -ForegroundColor Green
    
    # 检查关键文件
    $keyFiles = @(
        "$ROS2Workspace\src\ue5_bridge\ue5_bridge\ue5_bridge_node.py",
        "$ROS2Workspace\src\cri_msgs\msg\UE5State.msg",
        "$ROS2Workspace\src\cri_msgs\msg\UE5Command.msg"
    )
    
    $allExist = $true
    foreach ($file in $keyFiles) {
        if (-not (Test-Path $file)) {
            Write-Host "  ✗ 缺少文件: $file" -ForegroundColor Red
            $allExist = $false
        }
    }
    
    if ($allExist) {
        Write-Host "  ✓ 关键文件完整" -ForegroundColor Green
    }
} else {
    Write-Host "  ✗ ROS2工作空间未找到" -ForegroundColor Red
}

# 4. 生成UE5配置建议
Write-Host ""
Write-Host "[4/5] UE5 ROSIntegration 配置建议..." -ForegroundColor Yellow
if ($UbuntuIP) {
    Write-Host "  在UE5中配置以下参数:" -ForegroundColor Cyan
    Write-Host "  -----------------------------------" -ForegroundColor Gray
    Write-Host "  ROSBridge Server Host: $UbuntuIP" -ForegroundColor White
    Write-Host "  ROSBridge Server Port: 9090" -ForegroundColor White
    Write-Host "  Protocol: ws://" -ForegroundColor White
    Write-Host "  -----------------------------------" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  配置路径:" -ForegroundColor Cyan
    Write-Host "  编辑 → 项目设置 → 插件 → ROS Integration" -ForegroundColor Gray
}

# 5. 生成启动命令文档
Write-Host ""
Write-Host "[5/5] Ubuntu端启动命令参考..." -ForegroundColor Yellow
Write-Host "  在Ubuntu终端中依次执行:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Terminal 1: 启动rosbridge" -ForegroundColor Gray
Write-Host "  ros2 launch rosbridge_server rosbridge_websocket_launch.xml" -ForegroundColor White
Write-Host ""
Write-Host "  # Terminal 2: 启动UE5桥接" -ForegroundColor Gray
Write-Host "  source ~/campus_road_inspection_ws/install/setup.bash" -ForegroundColor White
Write-Host "  ros2 run ue5_bridge ue5_bridge_node" -ForegroundColor White
Write-Host ""
Write-Host "  # Terminal 3: 启动感知链路(可选)" -ForegroundColor Gray
Write-Host "  ros2 launch cri_bringup perception.launch.py" -ForegroundColor White
Write-Host ""

# 总结
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "检查完成！" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "1. 确保Ubuntu端rosbridge运行中" -ForegroundColor White
Write-Host "2. 在UE5中配置上述ROSIntegration参数" -ForegroundColor White
Write-Host "3. 启动UE5并点击Play" -ForegroundColor White
Write-Host "4. 查看UE5输出日志确认连接成功" -ForegroundColor White
Write-Host ""
Write-Host "详细测试指南: docs\UE5_MVP_TEST.md" -ForegroundColor Cyan
Write-Host ""

# 可选：保存配置到文件
$saveConfig = Read-Host "是否保存UE5配置到文件? (y/n)"
if ($saveConfig -eq 'y' -and $UbuntuIP) {
    $configContent = @"
# UE5 ROSIntegration 配置
# 生成时间: $(Get-Date)

Ubuntu IP: $UbuntuIP
rosbridge端口: 9090
WebSocket URL: ws://$UbuntuIP:9090

# 在UE5项目设置中配置:
- ROSBridge Server Host: $UbuntuIP
- ROSBridge Server Port: 9090
- Protocol: ws://

# 订阅话题(实车→UE5):
- /ue5/robot_state (cri_msgs/UE5State)

# 发布话题(UE5→实车):
- /ue5/command (cri_msgs/UE5Command)
"@
    
    $configPath = "C:\Users\xzx15\Desktop\CyberLuban\ue5_config.txt"
    $configContent | Out-File -FilePath $configPath -Encoding UTF8
    Write-Host "✓ 配置已保存到: $configPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
