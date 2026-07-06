---
name: solidworks-ai-bridge
description: Bridge a local AI coding agent to SolidWorks through the Windows COM Automation API for automated CAD modeling, parametric part and assembly creation, macro-like API calls, template discovery, dependency setup, and neutral CAD export for CAE/CFD workflows such as Ansys Fluent. Use when the user asks to connect an agent with SolidWorks, drive an open SolidWorks session, troubleshoot SldWorks.Application COM access, create SolidWorks models automatically, or export geometry for simulation.
---

# SolidWorks AI Bridge

Use the Windows COM Automation entrypoint `SldWorks.Application` to control SolidWorks from the local machine. Prefer Python with `pywin32` for agent-driven automation because it is scriptable, easy to inspect, and can be extended into downstream workflows such as STEP export, meshing, Fluent journals, or PyFluent.

## Operating Assumptions

- This skill only works on Windows with SolidWorks installed, licensed, and COM-registered.
- The agent must be able to run local shell commands and Python in the same user session as SolidWorks.
- Opening SolidWorks first is recommended but not required.
- If SolidWorks is already open, attach with `GetActiveObject("SldWorks.Application")`.
- If SolidWorks is closed, try `Dispatch("SldWorks.Application")`; this can launch SolidWorks only when installation and licensing are valid.
- Do not silently install SolidWorks. SolidWorks is commercial software; instruct the user to install it through their licensed Dassault/SOLIDWORKS installer, company software center, or administrator-managed package.
- It is acceptable to install Python dependencies such as `pywin32` when the user permits dependency setup.

## Quick Probe

From this skill directory, run:

```powershell
python .\scripts\sw_probe.py
```

If `pywin32` is missing and installing dependencies is appropriate:

```powershell
python .\scripts\sw_probe.py --install-deps
```

Create a test part:

```powershell
python .\scripts\sw_probe.py --create-test-part --output .\solidworks_com_test.SLDPRT
```

If the agent cannot rely on the current working directory, resolve the skill directory first and call the script by absolute path.

## Standard Workflow

1. Check Python and `pywin32`:

```powershell
python --version
python -m pip show pywin32
```

2. Probe SolidWorks with `scripts/sw_probe.py`.

3. If the probe connects, write task-specific automation using the same connection pattern:

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

4. For model creation, discover or provide a `.prtdot`, `.asmdot`, or `.drwdot` template. Common locations include:

```text
C:\ProgramData\SOLIDWORKS\SOLIDWORKS <year>\templates
C:\Users\Public\Documents\SOLIDWORKS\SOLIDWORKS <year>
```

5. Save generated files under the user's workspace unless another output path is requested.

## Modeling Rules

- Use SI units in SolidWorks API calls: meters, radians, kilograms.
- Convert user-facing millimeters to meters explicitly.
- Use `win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)` for nullable COM dispatch arguments such as `SelectByID2` callouts.
- Support localized default plane names where practical, including `Front Plane` and `前视基准面`.
- Prefer parameterized functions for geometry creation so the same model can be regenerated for design sweeps.
- For CFD/CAE handoff, export neutral geometry such as STEP (`.step/.stp`) or Parasolid (`.x_t`) after model creation.

## Troubleshooting

- `ModuleNotFoundError: No module named 'win32com'`: install `pywin32`.
- `Invalid class string`: SolidWorks is not installed or the COM ProgID is not registered.
- `GetActiveObject` fails but `Dispatch` works: SolidWorks was not open; continue with the new instance.
- COM calls fail in PowerShell with type-library errors: use Python + `pywin32`.
- New document fails: locate a valid SolidWorks template and pass it to `NewDocument`.
- Plane or feature selection fails: check localized names and use an explicit COM null dispatch argument.
