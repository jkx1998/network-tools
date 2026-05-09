"""ezwan 单元测试"""

import subprocess
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call, ANY

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestValidateParams:
    """测试参数验证逻辑"""

    def test_all_valid_defaults(self):
        """默认参数(全为0)应通过验证"""
        import ezwan
        try:
            ezwan.validate_params(0, 0, 0)
        except SystemExit:
            assert False, "不应该退出"

    def test_normal_params(self):
        """正常参数范围应通过"""
        import ezwan
        try:
            ezwan.validate_params(100, 10, 5.0)
        except SystemExit:
            assert False, "不应该退出"

    def test_max_loss(self):
        """丢包率100%应在合法范围内"""
        import ezwan
        try:
            ezwan.validate_params(0, 0, 100)
        except SystemExit:
            assert False, "不应该退出"

    def test_negative_delay(self):
        """延迟不能为负数"""
        import ezwan
        try:
            ezwan.validate_params(-1, 0, 0)
            assert False, "应该抛出 SystemExit"
        except SystemExit:
            pass

    def test_negative_jitter(self):
        """抖动不能为负数"""
        import ezwan
        try:
            ezwan.validate_params(0, -5, 0)
            assert False, "应该抛出 SystemExit"
        except SystemExit:
            pass

    def test_loss_above_100(self):
        """丢包率不能超过100%"""
        import ezwan
        try:
            ezwan.validate_params(0, 0, 150)
            assert False, "应该抛出 SystemExit"
        except SystemExit:
            pass

    def test_negative_loss(self):
        """丢包率不能为负数"""
        import ezwan
        try:
            ezwan.validate_params(0, 0, -10)
            assert False, "应该抛出 SystemExit"
        except SystemExit:
            pass

    def test_multiple_invalid_params(self):
        """多个无效参数应被捕获"""
        import ezwan
        try:
            ezwan.validate_params(-10, -5, -50)
            assert False, "应该抛出 SystemExit"
        except SystemExit:
            pass


class TestRunCmd:
    """测试命令执行"""

    def test_run_cmd_success(self):
        """子进程成功执行时返回 (True, stdout)"""
        import ezwan
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok\n", stderr="")
            ok, stdout = ezwan.run_cmd(["echo", "hello"])
            assert ok is True
            assert stdout == "ok\n"

    def test_run_cmd_failure(self):
        """子进程失败时返回 (False, stderr)"""
        import ezwan
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "cmd", stderr="command failed"
            )
            ok, stderr = ezwan.run_cmd(["bad_cmd"])
            assert ok is False
            assert "command failed" in stderr

    def test_run_cmd_string_input(self):
        """字符串输入自动拆分为列表"""
        import ezwan
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="")
            ezwan.run_cmd("tc qdisc show dev eth0")
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            assert isinstance(args[0], list)
            assert args[0][0] == "tc"

    def test_run_cmd_tc_not_found(self):
        """tc 命令不存在时返回友好提示"""
        import ezwan
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("tc")
            ok, stderr = ezwan.run_cmd(["tc", "qdisc"])
            assert ok is False
            assert "iproute2" in stderr


class TestCheckRoot:
    """测试 root 权限检查"""

    def test_root_user_passes(self):
        """uid=0(root) 时不退出"""
        import ezwan
        with patch("os.geteuid", return_value=0):
            try:
                ezwan.check_root()
            except SystemExit:
                assert False, "root 用户不应被拒绝"

    def test_non_root_user_exits(self):
        """非 root 用户应触发退出"""
        import ezwan
        with patch("os.geteuid", return_value=1000):
            try:
                ezwan.check_root()
                assert False, "应该抛出 SystemExit"
            except SystemExit:
                pass


class TestResetInterface:
    """测试规则重置"""

    def test_reset_calls_tc_delete(self):
        """重置接口应调用 tc qdisc del"""
        import ezwan
        with patch.object(ezwan, "run_cmd", return_value=(True, "")) as mock_run:
            ezwan.reset_interface("eth0")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "del" in args
            assert "eth0" in args

    def test_reset_handles_no_existing_rule(self):
        """无现有规则时不应报错"""
        import ezwan
        with patch.object(ezwan, "run_cmd", return_value=(False, "No such file or directory")):
            try:
                ezwan.reset_interface("eth0")
            except Exception:
                assert False, "没有规则时不应抛出异常"


class TestApplyNetem:
    """测试网络模拟规则应用"""

    def test_delay_only(self):
        """仅设置延迟"""
        import ezwan
        with patch.object(ezwan, "reset_interface") as mock_reset:
            with patch.object(ezwan, "run_cmd", return_value=(True, "")) as mock_run:
                ezwan.apply_netem("eth0", 100, 0, 0)
                mock_reset.assert_called_once()
                cmd = mock_run.call_args[0][0]
                assert "delay" in cmd
                assert "100ms" in cmd
                assert "loss" not in cmd

    def test_delay_with_jitter(self):
        """延迟 + 抖动"""
        import ezwan
        with patch.object(ezwan, "reset_interface"):
            with patch.object(ezwan, "run_cmd", return_value=(True, "")) as mock_run:
                ezwan.apply_netem("eth1", 50, 10, 0)
                cmd = mock_run.call_args[0][0]
                assert "delay" in cmd
                assert "50ms" in cmd
                assert "10ms" in cmd
                assert "25%" in cmd

    def test_loss_only(self):
        """仅设置丢包"""
        import ezwan
        with patch.object(ezwan, "reset_interface"):
            with patch.object(ezwan, "run_cmd", return_value=(True, "")) as mock_run:
                ezwan.apply_netem("eth0", 0, 0, 10)
                cmd = mock_run.call_args[0][0]
                assert "loss" in cmd
                assert "10%" in cmd
                assert "delay" not in cmd

    def test_combined_delay_loss(self):
        """延迟 + 丢包组合"""
        import ezwan
        with patch.object(ezwan, "reset_interface"):
            with patch.object(ezwan, "run_cmd", return_value=(True, "")) as mock_run:
                ezwan.apply_netem("eth2", 200, 30, 5)
                cmd = mock_run.call_args[0][0]
                assert "delay" in cmd
                assert "200ms" in cmd
                assert "30ms" in cmd
                assert "25%" in cmd
                assert "loss" in cmd
                assert "5%" in cmd

    def test_no_params_resets_only(self):
        """没有参数时只重置网络，不执行 tc"""
        import ezwan
        with patch.object(ezwan, "reset_interface") as mock_reset:
            with patch.object(ezwan, "run_cmd") as mock_run:
                ezwan.apply_netem("eth0", 0, 0, 0)
                mock_reset.assert_called_once()
                mock_run.assert_not_called()

    def test_command_dev_order(self):
        """验证命令参数顺序"""
        import ezwan
        with patch.object(ezwan, "reset_interface"):
            with patch.object(ezwan, "run_cmd", return_value=(True, "")) as mock_run:
                ezwan.apply_netem("eth0", 100, 0, 0)
                cmd = mock_run.call_args[0][0]
                # tc qdisc add dev <iface> root netem ...
                assert cmd[0] == "tc"
                assert cmd[1] == "qdisc"
                assert cmd[2] == "add"
                assert cmd[3] == "dev"
                assert cmd[4] == "eth0"
                assert cmd[5] == "root"
                assert cmd[6] == "netem"

    def test_invalid_params_rejected(self):
        """无效参数在调用 reset 之前就被拦截"""
        import ezwan
        with patch.object(ezwan, "reset_interface") as mock_reset:
            try:
                ezwan.apply_netem("eth0", -10, 0, 0)
            except SystemExit:
                pass
            mock_reset.assert_not_called()


class TestShowStatus:
    """测试状态查看"""

    def test_show_with_netem_rules(self, capsys):
        """有 netem 规则时的输出"""
        import ezwan
        sample = "qdisc netem 8001: root refcnt 2 limit 1000 delay 100.0ms"

        with patch.object(ezwan, "run_cmd", return_value=(True, sample)):
            ezwan.show_status("eth0")
        captured = capsys.readouterr()
        assert "100.0ms" in captured.out

    def test_show_direct_mode(self, capsys):
        """无限制时的输出"""
        import ezwan
        with patch.object(ezwan, "run_cmd", return_value=(True, "qdisc noqueue 0: root")):
            ezwan.show_status("eth0")
        captured = capsys.readouterr()
        assert "无限制" in captured.out


class TestMain:
    """测试 main 入口函数"""

    def test_status_flag_calls_show(self):
        """--status 参数触发状态查询"""
        import ezwan
        with patch("sys.argv", ["ezwan", "-i", "eth0", "--status"]):
            with patch.object(ezwan, "check_root"):
                with patch.object(ezwan, "show_status") as mock_show:
                    ezwan.main()
                    mock_show.assert_called_once_with("eth0")

    def test_reset_flag_calls_reset(self):
        """--reset 参数触发规则重置"""
        import ezwan
        with patch("sys.argv", ["ezwan", "-i", "eth1", "--reset"]):
            with patch.object(ezwan, "check_root"):
                with patch.object(ezwan, "reset_interface") as mock_reset:
                    ezwan.main()
                    mock_reset.assert_called_once_with("eth1")

    def test_apply_mode_with_params(self):
        """默认模式执行网络模拟"""
        import ezwan
        with patch("sys.argv", ["ezwan", "-i", "eth2", "--delay", "100", "--loss", "5"]):
            with patch.object(ezwan, "check_root"):
                with patch.object(ezwan, "apply_netem") as mock_apply:
                    ezwan.main()
                    mock_apply.assert_called_once_with("eth2", 100, 0, 5.0)

    def test_missing_interface_exits(self):
        """缺少 -i 参数应退出"""
        import ezwan
        with patch("sys.argv", ["ezwan"]):
            try:
                ezwan.main()
                assert False, "应该退出"
            except SystemExit:
                pass
