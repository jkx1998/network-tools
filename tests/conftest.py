"""共享测试工具"""

import json
import sys
from pathlib import Path
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

SAMPLE_CONFIG = {
    "mgmt_interface": "enp6s18",
    "default_driver": "igc",
    "dpdk_driver": "vfio-pci",
    "groups": [
        {
            "name": "wan_pair_1",
            "bridge": "br0",
            "interfaces": [
                {"pci": "0000:01:00.0", "linux_name": "uplink1"},
                {"pci": "0000:02:00.0", "linux_name": "uplink2"},
            ],
        },
        {
            "name": "wan_pair_2",
            "bridge": "br1",
            "interfaces": [
                {"pci": "0000:03:00.0", "linux_name": "uplink3"},
                {"pci": "0000:04:00.0", "linux_name": "uplink4"},
            ],
        },
    ],
}


def write_temp_config(path, config=None):
    """将配置写入临时 JSON 文件"""
    if config is None:
        config = SAMPLE_CONFIG
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f)


def capture_stderr():
    """捕获 stderr 输出的上下文管理器占位"""
    return StringIO()
