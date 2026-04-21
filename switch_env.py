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
    
    # 统一使用变量名 yaml_content
    yaml_content = "network:\n  version: 2\n  renderer: networkd\n"
    
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
            real_interfaces = [get_interface_name(i['pci']) for i in group['interfaces'] if get_interface_name(i['pci'])]
            if real_interfaces:
                yaml_content += f"      interfaces: {str(real_interfaces)}\n"
                yaml_content += "      parameters:\n        stp: false\n        forward-delay: 0\n"
                yaml_content += "      dhcp4: false\n"
    
    try:
        # 如果是 dpdk 模式且没有任何内容，或者 linux 模式下，统一写入
        # 如果 yaml_content 内容只有头部，说明没有接口，那就不需要生成文件
        if len(yaml_content) > 50: # 50 是 basic header 的长度
            with open(NETPLAN_FILE, 'w') as f:
                f.write(yaml_content)
            os.chmod(NETPLAN_FILE, 0o600)
            run_cmd("netplan apply")
        else:
            if os.path.exists(NETPLAN_FILE):
                os.remove(NETPLAN_FILE)
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
