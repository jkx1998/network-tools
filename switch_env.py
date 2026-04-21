#!/usr/bin/env python3
import json
import subprocess
import os
import sys
import time


#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = "/opt/network-tools" 
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
NETPLAN_FILE = "/etc/netplan/99-dynamic-config.yaml"

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def run_cmd(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"[-] 命令失败: {cmd}\n{e.stderr.decode().strip()}")

def bind_driver(pci, driver):
    unbind_path = f"/sys/bus/pci/devices/{pci}/driver/unbind"
    if os.path.exists(unbind_path):
        try:
            with open(unbind_path, "w") as f:
                f.write(pci)
        except OSError:
            pass
    
    run_cmd(f"modprobe {driver}")
    bind_path = f"/sys/bus/pci/drivers/{driver}/bind"
    if os.path.exists(bind_path):
        try:
            with open(bind_path, "w") as f:
                f.write(pci)
            print(f"[+] {pci} -> {driver} 绑定成功")
        except OSError:
            print(f"[*] {pci} -> {driver} 可能已绑定")


def get_interface_name(pci_addr):
    """根据 PCI 地址获取当前网卡名称"""
    try:
        # 在 /sys/bus/pci/devices/PCI_ADDR/net/ 下面就是网卡名
        path = f"/sys/bus/pci/devices/{pci_addr}/net"
        if os.path.exists(path):
            return os.listdir(path)[0] # 返回第一个找到的名字
    except Exception:
        pass
    return None

def generate_netplan(config, mode):
    print(f"[*] 生成 {mode} 模式的 Netplan 配置...")

    ethernets = {}
    bridges = {}

    # 管理口始终保留，防止 netplan apply 重置管理接口导致 SSH 断开
    mgmt = config.get("mgmt_interface")
    if mgmt:
        ethernets[mgmt] = "      dhcp4: false\n      optional: true\n"

    if mode == "linux":
        for group in config['groups']:
            for iface in group['interfaces']:
                name = get_interface_name(iface['pci'])
                if name:
                    ethernets[name] = "      dhcp4: false\n      optional: true\n"

        for group in config['groups']:
            real_interfaces = [get_interface_name(i['pci']) for i in group['interfaces'] if get_interface_name(i['pci'])]
            if real_interfaces:
                bridges[group['bridge']] = (
                    f"      interfaces: {str(real_interfaces)}\n"
                    "      parameters:\n        stp: false\n        forward-delay: 0\n"
                    "      dhcp4: false\n"
                    "      optional: true\n"
                )

    yaml_content = "network:\n  version: 2\n  renderer: NetworkManager\n"
    if ethernets:
        yaml_content += "  ethernets:\n"
        for name, cfg in ethernets.items():
            yaml_content += f"    {name}:\n{cfg}"
    if bridges:
        yaml_content += "  bridges:\n"
        for name, cfg in bridges.items():
            yaml_content += f"    {name}:\n{cfg}"

    try:
        with open(NETPLAN_FILE, 'w') as f:
            f.write(yaml_content)
        os.chmod(NETPLAN_FILE, 0o600)
        run_cmd("netplan apply")
        print("[+] Netplan 配置已应用")
    except Exception as e:
        print(f"[-] 写入配置失败: {e}")

def main():
    if os.geteuid() != 0:
        sys.exit("请使用 sudo 运行")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["linux", "dpdk"])
    args = parser.parse_args()
    config = load_config()

    if args.mode == "linux":
        print(">>> 切换到 Linux (Ezwan) 模式")
        for group in config['groups']:
            for iface in group['interfaces']:
                bind_driver(iface['pci'], config['default_driver'])
        time.sleep(1)
        generate_netplan(config, "linux")
        
    elif args.mode == "dpdk":
        print(">>> 切换到 DPDK (TRex/VPP) 模式")
        generate_netplan(config, "dpdk") # 先释放网卡
        time.sleep(1)
        for group in config['groups']:
            for iface in group['interfaces']:
                bind_driver(iface['pci'], config['dpdk_driver'])

if __name__ == "__main__":
    main()
