# SolidWorks AI Bridge

> 让本地 AI Agent 通过 SolidWorks COM 接口连接、驱动并自动生成 CAD 模型。

## 语言 / Language

- [中文](README.md)
- [English](README_en.md)

## 这个项目是什么？

`solidworks-ai-bridge` 是一个面向本地 AI 编程 Agent 的轻量级 Skill，用于把 Codex、Claude Code 等工具连接到本机 SolidWorks。

它的核心不是重新发明 CAD 内核，而是走 SolidWorks 官方开放的 Windows COM Automation 接口：

```text
SldWorks.Application
```

这样 AI Agent 就可以在你的电脑上完成这些事情：

- 连接已经打开的 SolidWorks
- 在 SolidWorks 未打开时尝试启动它
- 检查并安装 Python 依赖 `pywin32`
- 自动创建测试零件，验证连接链路
- 后续扩展参数化建模、STEP/Parasolid 导出、Fluent 前处理等流程

## 示例：真实 SolidWorks 导出的测试零件

下面图片来自脚本创建的 SolidWorks 测试零件，并通过 SolidWorks COM 自动导出。相比普通长方体，齿轮对更适合用来验证 sketch 轮廓、相位关系、多特征拉伸、中心孔和视图导出是否正常。

![SolidWorks exported gear pair](docs/images/solidworks-exports/gear_pair_test.png)

GitHub 仓库只保留这一个复杂示例图，避免 README 被多个重复的长方体测试件占满。

## 适合谁使用？

这个项目适合正在尝试把 AI Agent 接入工程软件流程的人，尤其是：

- 想让 AI 自动驱动 SolidWorks 建模
- 想做参数化 CAD 自动生成
- 想把 SolidWorks 建模接到 Ansys Fluent / CFD 流程
- 想让 Codex、Claude Code 等本地 Agent 执行真实工程软件操作
- 想先打通“AI -> SolidWorks -> 几何导出”的第一步

## 环境要求

- Windows
- 已安装并授权的 SolidWorks
- SolidWorks COM 接口已正常注册
- Python 已加入 `PATH`
- AI Agent 具备本地命令行执行权限

> 注意：SolidWorks 是商业软件，本项目不会、也不能自动安装 SolidWorks。请通过 Dassault/SOLIDWORKS 官方安装器、学校/公司软件中心或管理员提供的软件包安装。

## 安装到 Codex

把这个仓库复制到：

```text
%USERPROFILE%\.codex\skills\solidworks-ai-bridge
```

然后在 Codex 中可以这样说：

```text
使用 solidworks-ai-bridge，连接 SolidWorks，并创建一个测试零件。
```

## 安装到 Claude Code

把这个仓库复制到：

```text
%USERPROFILE%\.claude\skills\solidworks-ai-bridge
```

然后在 Claude Code 中可以这样说：

```text
Use the solidworks-ai-bridge skill to connect to SolidWorks and create a test part.
```

## 快速测试

在 skill 文件夹下运行：

```powershell
python .\scripts\sw_probe.py --install-deps
```

创建测试零件：

```powershell
python .\scripts\sw_probe.py --create-test-part --output .\solidworks_com_test.SLDPRT
```

创建两个啮合齿轮测试件：

```powershell
python .\scripts\create_gear_pair_test_part.py --output .\solidworks_gear_pair_test.SLDPRT --image-output .\docs\images\solidworks-exports\gear_pair_test.png
```

齿轮脚本默认会在保存和导出图片后关闭生成的 SolidWorks 文档，避免 SolidWorks 里堆积很多 `零件1`、`零件2` 这类窗口。如果需要保留窗口用于检查，可以追加：

```powershell
--keep-open
```

正常情况下会看到类似输出：

```text
CONNECTED source=active
VISIBLE True
REVISION <SolidWorks version>
```

说明：

- `source=active`：连接到了已经打开的 SolidWorks
- `source=dispatch`：通过 COM dispatch 启动或连接了 SolidWorks

## 工作原理

项目使用 Python + `pywin32` 调用 SolidWorks COM：

```python
import pythoncom
import win32com.client

pythoncom.CoInitialize()
try:
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
    except Exception:
        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = True
finally:
    pythoncom.CoUninitialize()
```

这个连接方式适合继续扩展成完整自动化流程：

```text
AI Agent
  -> SolidWorks COM
  -> 参数化建模
  -> STEP / Parasolid 导出
  -> Fluent Meshing / Fluent
  -> 后处理与结果分析
```

## 仓库结构

```text
solidworks-ai-bridge/
├── SKILL.md
├── README.md
├── README_en.md
├── requirements.txt
├── scripts/
│   ├── create_gear_pair_test_part.py
│   └── sw_probe.py
└── docs/
    └── images/
        └── solidworks-exports/
```

## 常见问题

### 使用前必须先打开 SolidWorks 吗？

不强制，但推荐先打开。

如果 SolidWorks 已经打开，脚本会优先连接当前会话：

```python
GetActiveObject("SldWorks.Application")
```

如果没有打开，脚本会尝试：

```python
Dispatch("SldWorks.Application")
```

但这要求 SolidWorks 已经正确安装、授权并注册 COM 接口。

### 网页版 AI 能直接用吗？

通常不能。这个项目需要本地命令行、Python 和 Windows COM 权限。

Codex、Claude Code 这类运行在本机的 Agent 更适合使用它。

### 后续能接 Fluent 吗？

可以。这也是这个项目的主要方向之一。建议路线是：

```text
SolidWorks 自动建模 -> 导出 STEP/Parasolid -> Fluent Meshing -> Fluent 求解
```

## License

MIT
