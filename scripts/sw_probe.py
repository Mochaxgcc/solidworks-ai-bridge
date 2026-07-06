from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


def ensure_pywin32(install: bool) -> None:
    if importlib.util.find_spec("win32com") and importlib.util.find_spec("pythoncom"):
        return
    if not install:
        raise RuntimeError("pywin32 is not installed. Run: python -m pip install pywin32")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])


def solidworks_template_roots() -> list[Path]:
    roots = [
        Path(r"C:\ProgramData\SOLIDWORKS"),
        Path(r"C:\Users\Public\Documents\SOLIDWORKS"),
    ]
    existing = [root for root in roots if root.exists()]
    return existing


def find_template(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path)
        raise FileNotFoundError(f"SolidWorks template not found: {path}")

    preferred_names = {"gb_part.prtdot", "part.prtdot"}
    all_templates: list[Path] = []
    for root in solidworks_template_roots():
        all_templates.extend(root.rglob("*.prtdot"))

    for template in all_templates:
        if template.name.lower() in preferred_names:
            return str(template)

    if all_templates:
        return str(all_templates[0])

    raise FileNotFoundError(
        "No .prtdot SolidWorks part template was found. "
        "Pass one explicitly with --template."
    )


def connect_solidworks():
    import win32com.client

    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
        source = "active"
    except Exception:
        sw = win32com.client.Dispatch("SldWorks.Application")
        source = "dispatch"
    sw.Visible = True
    return sw, source


def create_test_part(sw, template: str, output: Path) -> int:
    import pythoncom
    import win32com.client

    null_dispatch = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    model = sw.NewDocument(template, 0, 0, 0) or sw.ActiveDoc
    if model is None:
        raise RuntimeError(f"Could not create a part from template: {template}")

    selected = model.Extension.SelectByID2(
        "Front Plane", "PLANE", 0.0, 0.0, 0.0, False, 0, null_dispatch, 0
    )
    if not selected:
        selected = model.Extension.SelectByID2(
            "前视基准面", "PLANE", 0.0, 0.0, 0.0, False, 0, null_dispatch, 0
        )
    if not selected:
        raise RuntimeError("Could not select the front plane.")

    model.SketchManager.InsertSketch(True)
    model.SketchManager.CreateCenterRectangle(0.0, 0.0, 0.0, 0.05, 0.025, 0.0)
    model.SketchManager.InsertSketch(True)

    feature = model.FeatureManager.FeatureExtrusion2(
        True,
        False,
        False,
        0,
        0,
        0.03,
        0.0,
        False,
        False,
        False,
        False,
        0.0,
        0.0,
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        0,
        0,
        False,
    )
    if feature is None:
        raise RuntimeError("Extrude feature creation failed.")

    model.ForceRebuild3(False)
    return model.SaveAs3(str(output.resolve()), 0, 2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe SolidWorks COM connectivity and optionally create a test part."
    )
    parser.add_argument("--install-deps", action="store_true")
    parser.add_argument("--create-test-part", action="store_true")
    parser.add_argument("--template")
    parser.add_argument("--output", default="solidworks_com_test.SLDPRT")
    args = parser.parse_args()

    ensure_pywin32(args.install_deps)

    import pythoncom

    pythoncom.CoInitialize()
    try:
        sw, source = connect_solidworks()
        print(f"CONNECTED source={source}")
        print(f"VISIBLE {sw.Visible}")
        print(f"REVISION {sw.RevisionNumber}")

        if args.create_test_part:
            template = find_template(args.template)
            print(f"TEMPLATE {template}")
            result = create_test_part(sw, template, Path(args.output))
            print(f"SAVED {Path(args.output).resolve()}")
            print(f"SAVEAS3_RESULT {result}")
    finally:
        pythoncom.CoUninitialize()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
