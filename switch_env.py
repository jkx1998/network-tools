#!/usr/bin/env python3
import json
import subprocess
import os
import sys
import time
import argparse
import logging
from pathlib import Path
import shlex

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = BASE_DIR / "config.json"
NETPLAN_FILE = "/etc/netplan/99-dynamic-config.yaml"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

    return config


def run_cmd(cmd, check=True):
    """执行shell命令，支持列表形式避免shell注入"""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"命令失败: {e.stderr}")
        return False
    return True

def bind_driver(pci, driver):
    """绑定网卡驱动"""
    logger.info(f"尝试将 {pci} 绑定到 {driver}")

    unbind_path = Path(f"/sys/bus/pci/devices/{pci}/driver/unbind")
    if unbind_path.exists():
        try:
            with open(unbind_path, "w") as f:
                f.write(pci)
        except OSError as e:
            logger.warning(f"解绑失败: {e}")

    run_cmd(["modprobe", driver])

    bind_path = Path(f"/sys/bus/pci/drivers/{driver}/bind")
    if bind_path.exists():
        try:
            with open(bind_path, "w") as f:
                f.write(pci)
            logger.info(f"{pci} -> {driver} 绑定成功")
        except OSError:
            logger.info(f"{pci} -> {driver} 可能已绑定")


def get_interface_name(pci_addr):
    """根据 PCI 地址获取当前网卡名称"""
    try:
        path = Path(f"/sys/bus/pci/devices/{pci_addr}/net")
        if path.exists():
            interfaces = list(path.iterdir())
            if interfaces:
                return interfaces[0].name
    except Exception as e:
        logger.warning(f"获取网卡名失败 ({pci_addr}): {e}")
    return None

def generate_netplan(config, mode):
    """生成并应用 Netplan 配置"""
    logger.info(f"生成 {mode} 模式的 Netplan 配置")

    yaml_content = "network:\n  version: 2\n  renderer: NetworkManager\n"

    if mode == "linux":
        yaml_content += "  ethernets:\n"
        for group in config['groups']:
            for iface in group['interfaces']:
                name = get_interface_name(iface['pci'])
                if name:
                    yaml_content += f"    {name}:\n      dhcp4: false\n"

        yaml_content += "  bridges:\n"
        for group in config['groups']:
            yaml_content += f"    {group['bridge']}:\n"
            real_interfaces = []
            for i in group['interfaces']:
                iface_name = get_interface_name(i['pci'])
                if iface_name:
                    real_interfaces.append(iface_name)

            if real_interfaces:
                yaml_content += f"      interfaces: {str(real_interfaces)}\n"
                yaml_content += "      parameters:\n        stp: false\n        forward-delay: 0\n"
                yaml_content += "      dhcp4: false\n"

    try:
        if len(yaml_content) > 50:
            with open(NETPLAN_FILE, 'w') as f:
                f.write(yaml_content)
            os.chmod(NETPLAN_FILE, 0o600)
            run_cmd(["netplan", "apply"])
        else:
            if Path(NETPLAN_FILE).exists():
                Path(NETPLAN_FILE).unlink()
                run_cmd(["netplan", "apply"])
        logger.info("Netplan 配置已应用")
    except Exception as e:
        logger.error(f"写入配置失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="Network Tools - 网卡模式切换工具")
    parser.add_argument("mode", choices=["linux", "dpdk"], help="切换模式: linux 或 dpdk")
    parser.add_argument("-d", "--delay", type=int, default=1, help="切换后的等待时间(秒)，默认1秒")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if os.geteuid() != 0:
        sys.exit("请使用 sudo 运行")

    logger.info(f"切换到 {args.mode} 模式")
    config = load_config()

    if args.mode == "linux":
        logger.info(">>> 切换到 Linux (Ezwan) 模式")
        for group in config['groups']:
            for iface in group['interfaces']:
                bind_driver(iface['pci'], config['default_driver'])
        time.sleep(args.delay)
        generate_netplan(config, "linux")

    elif args.mode == "dpdk":
        logger.info(">>> 切换到 DPDK (TRex/VPP) 模式")
        generate_netplan(config, "dpdk")
        time.sleep(args.delay)
        for group in config['groups']:
            for iface in group['interfaces']:
                bind_driver(iface['pci'], config['dpdk_driver'])

    logger.info("切换完成")


if __name__ == "__main__":
    main()
