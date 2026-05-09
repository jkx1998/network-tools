# 优化说明

## 概述

本文档记录了对 network-tools 项目的优化内容。

## 优化内容

### 1. 安全修复

#### 1.1 命令注入漏洞修复

**问题**: 原代码使用 `subprocess.run(cmd, shell=True, ...)`，存在命令注入风险。

**修复**: 改用列表形式执行命令，避免 shell 解析：

```python
# 修复前
subprocess.run(cmd, shell=True, check=True, ...)

# 修复后
if isinstance(cmd, str):
    cmd = shlex.split(cmd)
subprocess.run(cmd, check=True, ...)
```

#### 1.2 硬编码路径修复

**问题**: `BASE_DIR = "/opt/network-tools"` 写死，导致项目不可移植。

**修复**: 动态获取脚本所在目录：

```python
# 修复后
from pathlib import Path
BASE_DIR = Path(__file__).parent.resolve()
```

---

### 2. 错误处理改进

#### 2.1 配置文件验证

**问题**: 直接读取配置，不检查文件是否存在和字段是否完整。

**修复**:

```python
def load_config():
    if not CONFIG_FILE.exists():
        logger.error(f"配置文件不存在: {CONFIG_FILE}")
        sys.exit(f"错误: 配置文件不存在 {CONFIG_FILE}")

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    required_fields = ['groups', 'default_driver', 'dpdk_driver']
    missing = [f for f in required_fields if f not in config]
    if missing:
        logger.error(f"配置缺少必要字段: {missing}")
        sys.exit(f"错误: 配置缺少必要字段: {missing}")
```

#### 2.2 参数范围验证

**问题**: 未验证延迟、抖动、丢包率等参数范围。

**修复**:

```python
def validate_params(delay, jitter, loss):
    errors = []
    if delay < 0:
        errors.append("延迟不能为负数")
    if jitter < 0:
        errors.append("抖动不能为负数")
    if not 0 <= loss <= 100:
        errors.append("丢包率必须在 0-100 之间")
```

#### 2.3 其他异常处理

- `get_interface_name()`: 修复可能的 IndexError
- 修复 tc 命令未找到的情况 (FileNotFoundError)
- 添加 netplan 文件操作异常处理

---

### 3. 代码质量提升

#### 3.1 日志系统

替换 `print` 为标准 `logging` 模块：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

#### 3.2 命令行参数增强

| 参数 | 说明 |
|------|------|
| `-v, --verbose` | 显示详细日志 |
| `-d, --delay` | 自定义等待时间(秒) |

#### 3.3 性能优化

优化 `generate_netplan` 中的重复函数调用：

```python
# 修复前 (重复调用3次)
real_interfaces = [get_interface_name(i['pci']) for i in group['interfaces'] if get_interface_name(i['pci'])]

# 修复后 (单次调用)
real_interfaces = []
for i in group['interfaces']:
    iface_name = get_interface_name(i['pci'])
    if iface_name:
        real_interfaces.append(iface_name)
```

#### 3.4 Path 对象替代 os.path

使用 `pathlib.Path` 替代传统的 `os.path`：

```python
# 修复后
from pathlib import Path
path = Path(f"/sys/bus/pci/devices/{pci_addr}/net")
if path.exists():
    interfaces = list(path.iterdir())
```

---

### 4. 文件变更统计

| 文件 | 修改行数 |
|------|----------|
| switch_env.py | +85, -45 |
| ezwan | +73, -28 |
| **总计** | +158, -73 |

---

## 优化前后对比

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 安全性 | shell 注入风险 | 安全列表形式 |
| 可移植性 | 硬编码路径 | 动态路径获取 |
| 错误处理 | 无验证 | 完整验证 |
| 日志 | print | logging |
| 可维护性 | 一般 | 良好 |

---

## 已知限制

1. 仍需 root 权限运行
2. 仅支持 Linux 系统
3. netplan 路径仍为固定路径 (`/etc/netplan/99-dynamic-config.yaml`)