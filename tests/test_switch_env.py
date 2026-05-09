"""switch_env.py 单元测试"""

import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from unittest import mock
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.conftest import SAMPLE_CONFIG, write_temp_config


class TestLoadConfig:
    """测试配置文件加载和验证"""

    def test_load_valid_config(self, tmp_path):
        """加载合法的配置文件"""
        import switch_env
        config_file = tmp_path / "config.json"
        write_temp_config(config_file)
        monkeypatch_path = patch.object(switch_env, "CONFIG_FILE", config_file)

        with monkeypatch_path:
            config = switch_env.load_config()
            assert config["default_driver"] == "igc"
            assert len(config["groups"]) == 2

    def test_config_missing_file(self, tmp_path):
        """配置文件不存在时应退出"""
        import switch_env
        config_file = tmp_path / "nonexistent.json"
        monkeypatch_path = patch.object(switch_env, "CONFIG_FILE", config_file)

        with monkeypatch_path:
            try:
                switch_env.load_config()
                assert False, "应该抛出 SystemExit"
            except SystemExit as e:
                assert "配置文件不存在" in str(e.code)

    def test_config_missing_required_fields(self, tmp_path):
        """配置文件缺少必要字段时应退出"""
        import switch_env
        config_file = tmp_path / "bad_config.json"
        write_temp_config(config_file, {"groups": []})

        monkeypatch_path = patch.object(switch_env, "CONFIG_FILE", config_file)
        with monkeypatch_path:
            try:
                switch_env.load_config()
                assert False, "应该抛出 SystemExit"
            except SystemExit as e:
                assert "default_driver" in str(e.code)

    def test_config_empty_groups(self, tmp_path):
        """groups 为空列表也是合法的"""
        import switch_env
        config_file = tmp_path / "empty_groups.json"
        write_temp_config(config_file, {
            "default_driver": "igc",
            "dpdk_driver": "vfio-pci",
            "groups": [],
        })

        monkeypatch_path = patch.object(switch_env, "CONFIG_FILE", config_file)
        with monkeypatch_path:
            config = switch_env.load_config()
            assert config["groups"] == []


class TestRunCmd:
    """测试命令执行"""

    def test_run_cmd_success(self):
        """run_cmd 在命令成功时返回 True"""
        import switch_env
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = switch_env.run_cmd(["echo", "hello"])
            assert result is True

    def test_run_cmd_failure(self):
        """run_cmd 在命令失败时返回 False"""
        import switch_env
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "cmd", stderr="error message"
            )
            result = switch_env.run_cmd(["false"])
            assert result is False

    def test_run_cmd_string_input(self):
        """run_cmd 接受字符串输入并转为列表"""
        import switch_env
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            switch_env.run_cmd("netplan apply")
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            # 确认被拆分成了列表
            assert isinstance(args[0], list)


class TestGetInterfaceName:
    """测试根据 PCI 地址获取网卡名"""

    def test_interface_found(self):
        """PCI 路径存在且有网卡目录"""
        import switch_env
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_net_dir = MagicMock()
        mock_net_dir.name = "eth0"
        mock_path.iterdir.return_value = [mock_net_dir]

        with patch.object(Path, "__new__", return_value=mock_path):
            result = switch_env.get_interface_name("0000:01:00.0")
            assert result == "eth0"

    def test_interface_not_found(self):
        """PCI 路径不存在"""
        import switch_env
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False

        def make_path(cls, p):
            return mock_path

        with patch.object(Path, "__new__", return_value=mock_path):
            result = switch_env.get_interface_name("0000:ff:00.0")
            assert result is None

    def test_interface_empty_dir(self):
        """PCI 路径存在但 net 目录为空"""
        import switch_env
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.iterdir.return_value = []

        with patch.object(Path, "__new__", return_value=mock_path):
            result = switch_env.get_interface_name("0000:01:00.0")
            assert result is None


class TestGenerateNetplan:
    """测试 Netplan 配置生成"""

    def assert_yaml_structure(self, content):
        """验证 Netplan YAML 基本结构"""
        assert "network:" in content
        assert "version: 2" in content
        assert "renderer: NetworkManager" in content

    def test_linux_mode_generates_bridges(self, tmp_path):
        """Linux 模式生成网桥配置"""
        import switch_env
        netplan_file = tmp_path / "netplan.yaml"

        def fake_get_interface_name(pci):
            mapping = {
                "0000:01:00.0": "eth0",
                "0000:02:00.0": "eth1",
                "0000:03:00.0": "eth2",
                "0000:04:00.0": "eth3",
            }
            return mapping.get(pci)

        with patch.object(switch_env, "NETPLAN_FILE", str(netplan_file)):
            with patch.object(switch_env, "get_interface_name", side_effect=fake_get_interface_name):
                with patch.object(switch_env, "run_cmd", return_value=True):
                    with patch("os.chmod"):
                        switch_env.generate_netplan(SAMPLE_CONFIG, "linux")

        content = netplan_file.read_text()
        self.assert_yaml_structure(content)
        assert "bridges:" in content
        assert "br0" in content
        assert "br1" in content
        assert "eth0" in content
        assert "dhcp4: false" in content

    def test_dpdk_mode_minimal_content(self, tmp_path):
        """DPDK 模式只生成最小配置（仅头部）"""
        import switch_env
        netplan_file = tmp_path / "netplan.yaml"

        with patch.object(switch_env, "NETPLAN_FILE", str(netplan_file)):
            with patch.object(switch_env, "run_cmd", return_value=True):
                with patch("os.chmod"):
                    switch_env.generate_netplan(SAMPLE_CONFIG, "dpdk")

        self.assert_yaml_structure(netplan_file.read_text())
