# network-tools

Linux 网络工具包，提供网卡驱动模式切换和 WAN 弱网模拟两大功能。

## 功能

- **switch_env.py** — 在 Linux 网络模式和 DPDK (VFIO/UIO) 模式之间一键切换网卡驱动
- **ezwan** — 基于 `tc netem` 的极简 WAN 模拟器，可控制延迟、抖动和丢包率

## 适用场景

- 网络性能测试：模拟广域网延迟和丢包
- DPDK / TRex / VPP 开发：快速切换网卡驱动模式
- 弱网环境测试：模拟移动网络、跨国链路等恶劣网络条件

## 环境要求

- Linux 系统
- Python 3.6+
- root 权限
- iproute2（提供 `tc` 命令）
- NetworkManager

## 快速开始

### 安装

```bash
git clone https://github.com/jkx1998/network-tools.git
cd network-tools
pip install -r requirements.txt  # 仅 pytest，生产环境无需
```

### 切换网卡模式

```bash
# 切换到 Linux 模式（常规网络）
sudo python3 switch_env.py linux

# 切换到 DPDK 模式（TRex/VPP 使用）
sudo python3 switch_env.py dpdk

# 显示详细日志
sudo python3 switch_env.py linux -v

# 自定义切换后等待时间（秒）
sudo python3 switch_env.py dpdk --delay 3
```

### WAN 弱网模拟

```bash
# 延迟 100ms + 丢包 5%
sudo ./ezwan -i eth1 --delay 100 --loss 5

# 延迟 50ms + 抖动 10ms
sudo ./ezwan -i eth1 --delay 50 --jitter 10

# 仅查看状态
sudo ./ezwan -i eth1 --status

# 重置为正常网络
sudo ./ezwan -i eth1 --reset
```

## 配置文件

编辑 `config.json`：

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
                {"pci": "0000:01:00.0", "linux_name": "uplink1"},
                {"pci": "0000:02:00.0", "linux_name": "uplink2"}
            ]
        }
    ]
}
```

| 字段 | 说明 |
|------|------|
| `default_driver` | Linux 模式下的网卡驱动（如 igb, igc, ixgbe） |
| `dpdk_driver` | DPDK 模式驱动（如 vfio-pci, uio_pci_generic） |
| `groups` | 网卡组，每组包含网桥名和 PCI 接口列表 |

## 运行测试

不需要 root 权限，纯逻辑验证，不操作真实网卡：

```bash
pip install pytest
python3 -m pytest tests/ -v
```

详见 [tests/README_TEST.md](tests/README_TEST.md)。

## 项目结构

```
network-tools/
├── switch_env.py       # 网卡驱动模式切换
├── ezwan               # WAN 弱网模拟器
├── config.json          # 配置文件
├── README.md
├── OPTIMIZATION.md      # 优化说明
├── USAGE.md             # 详细使用手册
└── tests/
    ├── README_TEST.md   # 测试说明书
    ├── conftest.py      # 共享测试数据
    ├── test_switch_env.py
    └── test_ezwan.py
```

## 文档索引

| 文档 | 内容 |
|------|------|
| [USAGE.md](USAGE.md) | 完整使用手册，含配置详解和常见问题 |
| [OPTIMIZATION.md](OPTIMIZATION.md) | 优化记录，含代码变更细节 |
| [tests/README_TEST.md](tests/README_TEST.md) | 小白测试操作指南 |

## 注意事项

- 需要 root 权限运行
- 切换网卡驱动会导致网络短暂中断
- 远程 SSH 操作前请确保有本地终端备援
- 建议先在测试环境验证
