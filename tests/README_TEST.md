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

测试文件一共 3 个：

| 文件 | 测试什么 | 用例数 |
|------|----------|--------|
| `test_ezwan.py` | 弱网模拟工具（参数验证、命令执行） | 22 个 |
| `test_switch_env.py` | 网卡模式切换工具（配置加载、Netplan 生成） | 12 个 |
| `conftest.py` | 共享的测试数据，不用管 | - |

### 测试了什么？

- 配置文件能不能正常加载？
- 缺少配置时会报错吗？
- 延迟参数能不能是负数？（当然不能）
- 丢包率能超过 100% 吗？（也不能）
- tc 命令能正确拼出来吗？

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
