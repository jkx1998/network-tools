# 测试说明书（小白版）

## 第一步：安装 Python

你的电脑上需要安装 Python。打开终端（命令行），输入以下命令检查是否已安装：

```bash
python3 --version
```

如果显示 `Python 3.x.x`，说明已安装，跳到下一步。

如果没装，去 [python.org](https://www.python.org/downloads/) 下载安装，安装时**勾选 "Add Python to PATH"**。

## 第二步：安装测试工具

打开终端，输入一行命令就够了：

```bash
pip install pytest
```

> 提示：如果提示 `pip: command not found`，试试换成 `pip3 install pytest`

## 第三步：进入项目目录

在终端中切换到项目文件夹：

```bash
cd /你放项目的路径/network-tools
```

> 比如你把项目下载到了 `/home/me/network-tools`，就输入 `cd /home/me/network-tools`

## 第四步：运行测试

输入以下命令，一键运行所有测试：

```bash
python3 -m pytest tests/ -v
```

你会看到类似这样的输出：

```
tests/test_switch_env.py::TestLoadConfig::test_load_valid_config PASSED
tests/test_switch_env.py::TestLoadConfig::test_config_missing_file PASSED
...
tests/test_ezwan.py::TestValidateParams::test_negative_delay PASSED
...
=================== 34 passed in 0.5s ===================
```

- 绿色 `PASSED` = 测试通过，没问题
- 红色 `FAILED` = 测试失败，有 bug
- 黄色 `SKIPPED` = 跳过了

## 测试内容说明

共 34 个测试用例，分在两个文件中。

### test_ezwan.py — 22 个用例

**参数验证（8个）**

| 测试 | 验证什么 |
|------|----------|
| `test_all_valid_defaults` | 全部为 0 的默认参数能过 |
| `test_normal_params` | 正常的延迟+抖动+丢包能过 |
| `test_max_loss` | 丢包率 100% 是合法的上限 |
| `test_negative_delay` | 延迟为负数 → 拒绝 |
| `test_negative_jitter` | 抖动为负数 → 拒绝 |
| `test_loss_above_100` | 丢包率超过 100% → 拒绝 |
| `test_negative_loss` | 丢包率为负数 → 拒绝 |
| `test_multiple_invalid_params` | 多个参数全非法 → 拒绝 |

**命令执行（4个）**

| 测试 | 验证什么 |
|------|----------|
| `test_run_cmd_success` | 成功时返回 True + 命令输出 |
| `test_run_cmd_failure` | 失败时返回 False + 错误信息 |
| `test_run_cmd_string_input` | 字符串参数自动拆成列表 |
| `test_run_cmd_tc_not_found` | tc 没安装时给出友好提示 |

**权限检查（2个）**

| 测试 | 验证什么 |
|------|----------|
| `test_root_user_passes` | root 用户（uid=0）不拦截 |
| `test_non_root_user_exits` | 普通用户直接退出 |

**规则重置（2个）**

| 测试 | 验证什么 |
|------|----------|
| `test_reset_calls_tc_delete` | 执行了 `tc qdisc del` 命令 |
| `test_reset_handles_no_existing_rule` | 本来就没规则也不崩溃 |

**网络模拟（7个）**

| 测试 | 验证什么 |
|------|----------|
| `test_delay_only` | 只设延迟 → 命令不含 loss 参数 |
| `test_delay_with_jitter` | 延迟+抖动 → 含 25% 相关性参数 |
| `test_loss_only` | 只设丢包 → 命令不含 delay 参数 |
| `test_combined_delay_loss` | 三个参数组合 → 命令包含全部 |
| `test_no_params_resets_only` | 无参数时只重置、不执行 tc |
| `test_command_dev_order` | 参数拼写顺序正确 |
| `test_invalid_params_rejected` | 非法参数在重置网卡之前就被拦住 |

**状态查看（2个）**

| 测试 | 验证什么 |
|------|----------|
| `test_show_with_netem_rules` | 有规则时输出延迟数值 |
| `test_show_direct_mode` | 无规则时输出"无限制（直通状态）" |

**入口函数（4个）**

| 测试 | 验证什么 |
|------|----------|
| `test_status_flag_calls_show` | `--status` 参数会调用显示状态 |
| `test_reset_flag_calls_reset` | `--reset` 参数会调用重置规则 |
| `test_apply_mode_with_params` | 默认模式调网络模拟 |
| `test_missing_interface_exits` | 缺少 -i 参数直接退出 |

---

### test_switch_env.py — 12 个用例

**配置加载（4个）**

| 测试 | 验证什么 |
|------|----------|
| `test_load_valid_config` | 合法 JSON → 正常加载 |
| `test_config_missing_file` | 文件不存在 → 退出并提示 |
| `test_config_missing_required_fields` | 缺必要字段 → 退出并点名缺失项 |
| `test_config_empty_groups` | groups 为空也是合法的 |

**命令执行（3个）**

| 测试 | 验证什么 |
|------|----------|
| `test_run_cmd_success` | 成功返回 True |
| `test_run_cmd_failure` | 失败返回 False |
| `test_run_cmd_string_input` | 字符串自动拆成列表 |

**网卡名获取（3个）**

| 测试 | 验证什么 |
|------|----------|
| `test_interface_found` | PCI 路径有网卡 → 返回 eth0 |
| `test_interface_not_found` | PCI 路径不存在 → 返回 None |
| `test_interface_empty_dir` | net 目录为空 → 返回 None |

**Netplan 生成（2个）**

| 测试 | 验证什么 |
|------|----------|
| `test_linux_mode_generates_bridges` | Linux 模式生成 br0/br1 网桥 |
| `test_dpdk_mode_minimal_content` | DPDK 模式只生成基本头部 |

## 常用命令速查

```bash
# 运行所有测试，显示详细信息
python3 -m pytest tests/ -v

# 只运行 ezwan 的测试
python3 -m pytest tests/test_ezwan.py -v

# 只运行"参数验证"相关的测试
python3 -m pytest tests/ -v -k "validate"

# 显示每个测试的执行时间
python3 -m pytest tests/ -v --duration=0

# 遇到第一个失败就停
python3 -m pytest tests/ -v -x
```

## 如果测试失败了怎么办？

1. 看报错信息，了解哪个测试失败了
2. 报错会告诉你：预期是什么，实际是什么
3. 把报错信息复制下来，发给我看看

示例报错：

```
FAILED tests/test_ezwan.py::TestValidateParams::test_negative_delay - SystemExit: 1
```

意思是"延迟不能为负数"这个测试失败了，说明代码把这个错误情况漏掉了。

## 注意事项

- 测试不需要 root 权限，普通用户就能跑
- 测试不会真的操作网卡，不会影响你的网络
- 测试用到了 mock（模拟），就像"假装"执行命令来验证逻辑是否正确
- 环境要求：Python 3.6 以上
