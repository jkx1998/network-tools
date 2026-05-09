# network-tools 使用手册

## 简介

network-tools 是一个 Linux 网络工具包，提供两个主要功能：
1. **switch_env.py** - 网卡驱动模式切换工具（Linux/DPDK）
2. **ezwan** - 简易 WAN 模拟器（网络延迟/丢包控制）

## 环境要求

- Linux 系统
- Python 3.6+
- root 权限
- 已安装 iproute2 (tc 命令)
- 已安装 NetworkManager

---

## 配置文件

### config.json 格式

```json
{
    "mgmt_interface": "enp6s18",
    "default_driver": "igc",
    "dpdk_driver": "vfio-pci",
    "groups": [
        {
            "name": "wan_pair_1",
            "bridge": "br0",
            "interfaces": [
                {
                    "pci": "0000:01:00.0",
                    "linux_name": "uplink1"
                }
            ]
        }
    ]
}
```

### 配置字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| mgmt_interface | 否 | 管理接口名称 |
| default_driver | 是 | Linux 模式网卡驱动（如 igb, ixgbe, igc） |
| dpdk_driver | 是 | DPDK 模式驱动（如 vfio-pci, uio_pci_generic） |
| groups | 是 | 网卡组列表 |

### groups 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | 组名称 |
| bridge | 是 | 网桥名称 |
| interfaces | 是 | 接口列表，每个包含 pci 地址 |

---

## switch_env.py - 网卡模式切换

### 功能

在 Linux 网络模式和 DPDK 模式之间切换网卡驱动。

### 使用方法

```bash
# 切换到 Linux (Ezwan) 模式
sudo python3 switch_env.py linux

# 切换到 DPDK (TRex/VPP) 模式
sudo python3 switch_env.py dpdk
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| mode | 切换模式：`linux` 或 `dpdk` | 必填 |
| -d, --delay | 切换后的等待时间(秒) | 1 |
| -v, --verbose | 显示详细日志 | 关闭 |

### 示例

```bash
# 切换到 Linux 模式，等待 2 秒
sudo python3 switch_env.py linux -d 2

# 切换到 DPDK 模式，显示详细日志
sudo python3 switch_env.py dpdk -v

# 完整参数示例
sudo python3 switch_env.py linux -d 3 -v
```

### 工作流程

**切换到 Linux 模式**:
1. 绑定网卡到 default_driver
2. 生成 Netplan 配置创建网桥
3. 应用 Netplan 配置

**切换到 DPDK 模式**:
1. 清除 Netplan 配置释放网卡
2. 绑定网卡到 dpdk_driver

---

## ezwan - WAN 模拟器

### 功能

模拟广域网环境，可控制网络延迟、抖动和丢包率。

### 使用方法

```bash
# 设置延迟 100ms，丢包率 5%
sudo ./ezwan -i eth1 --delay 100 --loss 5

# 设置延迟 50ms，抖动 10ms，丢包 2%
sudo ./ezwan -i eth1 --delay 50 --jitter 10 --loss 2

# 查看当前规则状态
sudo ./ezwan -i eth1 --status

# 重置规则（清除所有限制）
sudo ./ezwan -i eth1 --reset
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| -i, --interface | 目标网卡名称 | 必填 |
| --delay | 网络延迟 (毫秒 ms) | 0 |
| --jitter | 延迟抖动 (毫秒 ms) | 0 |
| --loss | 丢包率 (百分比 %) | 0 |
| --reset | 清除所有模拟规则 | False |
| --status | 查看当前规则状态 | False |
| -v, --verbose | 显示详细日志 | False |

### 参数范围

| 参数 | 最小值 | 最大值 |
|------|--------|--------|
| delay | 0 | 无限制 |
| jitter | 0 | 无限制 |
| loss | 0 | 100 |

### 示例

```bash
# 模拟 50ms 延迟
sudo ./ezwan -i eth1 --delay 50

# 模拟 100ms 延迟 + 20ms 抖动
sudo ./ezwan -i eth1 --delay 100 --jitter 20

# 模拟 10% 丢包率
sudo ./ezwan -i eth1 --loss 10

# 模拟复杂弱网环境：200ms延迟 + 30ms抖动 + 5%丢包
sudo ./ezwan -i eth1 --delay 200 --jitter 30 --loss 5

# 查看状态
sudo ./ezwan -i eth1 --status

# 重置为正常网络
sudo ./ezwan -i eth1 --reset
```

---

## 常见问题

### Q1: 提示 "请使用 sudo 运行"

两个工具都需要 root 权限，请使用 `sudo` 运行。

### Q2: 网卡 PCI 地址如何查看？

```bash
# 查看网卡 PCI 地址
lspci | grep -i ethernet

# 或查看具体网卡
ls -la /sys/bus/pci/devices/
```

### Q3: ezwan 提示 "tc 命令未找到"

确保已安装 iproute2：
```bash
# Debian/Ubuntu
sudo apt install iproute2

# RHEL/CentOS
sudo yum install iproute
```

### Q4: switch_env.py 提示配置文件不存在

确保 config.json 在脚本同一目录，或以符号链接方式映射：
```bash
sudo ln -s /path/to/network-tools/config.json /opt/network-tools/config.json
```

### Q5: 切换到 DPDK 模式后无法上网

正常的，DPDK 模式下网卡不再使用常规网络协议栈。需要切换回 Linux 模式：
```bash
sudo python3 switch_env.py linux
```

---

## 日志级别

使用 `-v` 参数可以查看详细日志：

```bash
# 开启详细日志
sudo ./ezwan -i eth1 --delay 100 -v

# 输出示例
2024-01-01 12:00:00,000 - INFO - 正在清除 eth1 上的规则...
2024-01-01 12:00:00,001 - INFO - eth1 规则已重置
2024-01-01 12:00:00,002 - INFO - 应用规则: tc qdisc add dev eth1 root netem delay 100ms
2024-01-01 12:00:00,010 - INFO - 成功应用规则到 eth1!
```

---

## 注意事项

1. **谨慎操作**: 切换网卡驱动会导致网络中断
2. **远程操作**: 如果通过 SSH 连接，请确保有本地终端备援
3. **DPDK 模式**: 切换后网卡不再有常规网络功能
4. **测试环境**: 建议先在测试环境验证