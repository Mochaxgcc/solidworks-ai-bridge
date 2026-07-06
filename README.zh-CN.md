# SolidWorks AI Bridge

[English](README.md) | [中文](README.zh-CN.md)

一个可移植的 AI Agent Skill，用于通过 Windows COM Automation API 连接和驱动 SolidWorks。

它可以帮助本地 AI 编程 Agent 使用 `SldWorks.Application` 连接已经打开的 SolidWorks，或者在条件允许时启动 SolidWorks；同时检查 Python 依赖、创建测试零件，并为参数化 CAD 建模和 CAD-to-CAE 流程提供基础。

## 示例输出

内置探针脚本可以创建一个 100 mm x 50 mm x 30 mm 的测试零件，用来验证从 AI Agent 到 SolidWorks 的自动化链路是否打通。

![SolidWorks AI Bridge 测试零件](docs/images/solidworks-ai-bridge-test-part.png)

## 环境要求

- Windows
- 已安装、已授权并已注册 COM 接口的 SolidWorks
- Python 已加入 `PATH`
- 本地命令行执行权限

SolidWorks 是商业软件，本 skill 不会安装 SolidWorks 本体。请通过 Dassault/SOLIDWORKS 官方安装器、学校/公司软件中心或管理员提供的软件包安装。

## 安装

### Codex

复制本文件夹到：

```text
%USERPROFILE%\.codex\skills\solidworks-ai-bridge
```

### Claude Code

复制本文件夹到：

```text
%USERPROFILE%\.claude\skills\solidworks-ai-bridge
```

其他本地 Agent 如果支持 `SKILL.md` 风格的 skill，或者能读取说明并运行内置脚本，也可以使用这个项目。

## 测试

在 skill 文件夹下运行：

```powershell
python .\scripts\sw_probe.py --install-deps
```

创建测试零件：

```powershell
python .\scripts\sw_probe.py --create-test-part --output .\solidworks_com_test.SLDPRT
```

正常输出会包含：

```text
CONNECTED source=active
VISIBLE True
REVISION <SolidWorks version>
```

`source=active` 表示连接到了已经打开的 SolidWorks 会话。`source=dispatch` 表示通过 COM dispatch 启动或连接了新的 SolidWorks 会话。

## 使用示例

你可以这样要求本地 AI 编程 Agent：

```text
Use the solidworks-ai-bridge skill to connect to SolidWorks, create a parameterized pipe model, and export STEP geometry for Fluent.
```

也可以用中文表达：

```text
使用 solidworks-ai-bridge skill 连接 SolidWorks，创建一个参数化管道模型，并导出 STEP 几何给 Fluent 使用。
```

## 仓库内容

```text
solidworks-ai-bridge/
├── SKILL.md
├── README.md
├── README.zh-CN.md
├── docs/
│   └── images/
│       └── solidworks-ai-bridge-test-part.png
└── scripts/
    └── sw_probe.py
```

## 许可证

MIT
