from __future__ import annotations

import argparse
import math
from pathlib import Path

import pythoncom
import win32com.client


DEFAULT_TEMPLATE_CANDIDATES = [
    r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot",
    r"C:\Users\Public\Documents\SOLIDWORKS\SOLIDWORKS 2024\samples\tutorial\advdrawings\part.prtdot",
]


def connect_solidworks():
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
        source = "active"
    except Exception:
        sw = win32com.client.Dispatch("SldWorks.Application")
        source = "dispatch"
    sw.Visible = True
    return sw, source


def find_template(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path)
        raise FileNotFoundError(f"SolidWorks template not found: {path}")

    for candidate in DEFAULT_TEMPLATE_CANDIDATES:
        if Path(candidate).exists():
            return candidate

    for root in [Path(r"C:\ProgramData\SOLIDWORKS"), Path(r"C:\Users\Public\Documents")]:
        if root.exists():
            match = next(root.rglob("*.prtdot"), None)
            if match:
                return str(match)

    raise FileNotFoundError("No .prtdot SolidWorks part template was found.")


def gear_points(
    center_x: float,
    center_y: float,
    teeth: int,
    root_radius: float,
    outer_radius: float,
    rotation: float,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    pitch = 2.0 * math.pi / teeth

    # Four points per tooth keeps the sketch robust while still looking gear-like.
    for index in range(teeth):
        tooth_center = rotation + index * pitch
        samples = [
            (tooth_center - 0.50 * pitch, root_radius),
            (tooth_center - 0.22 * pitch, outer_radius),
            (tooth_center + 0.22 * pitch, outer_radius),
            (tooth_center + 0.50 * pitch, root_radius),
        ]
        for angle, radius in samples:
            points.append(
                (
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                )
            )
    return points


def draw_closed_polyline(sketch_manager, points: list[tuple[float, float]]) -> None:
    for start, end in zip(points, points[1:] + points[:1]):
        sketch_manager.CreateLine(start[0], start[1], 0.0, end[0], end[1], 0.0)


def select_front_plane(model, null_dispatch) -> None:
    selected = model.Extension.SelectByID2(
        "Front Plane", "PLANE", 0.0, 0.0, 0.0, False, 0, null_dispatch, 0
    )
    if not selected:
        selected = model.Extension.SelectByID2(
            "前视基准面", "PLANE", 0.0, 0.0, 0.0, False, 0, null_dispatch, 0
        )
    if not selected:
        raise RuntimeError("Could not select the front plane.")


def extrude_current_sketch(model, thickness: float) -> None:
    feature = model.FeatureManager.FeatureExtrusion2(
        True,
        False,
        False,
        0,
        0,
        thickness,
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
        raise RuntimeError("Gear extrusion failed.")


def create_gear_pair(
    sw,
    template: str,
    output: Path,
    teeth: int,
    pitch_radius_mm: float,
    root_radius_mm: float,
    outer_radius_mm: float,
    thickness_mm: float,
) -> None:
    null_dispatch = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    model = sw.NewDocument(template, 0, 0, 0) or sw.ActiveDoc
    if model is None:
        raise RuntimeError(f"Could not create a part from template: {template}")

    pitch_radius = pitch_radius_mm / 1000.0
    root_radius = root_radius_mm / 1000.0
    outer_radius = outer_radius_mm / 1000.0
    thickness = thickness_mm / 1000.0
    center_distance = 2.0 * pitch_radius + 0.0008
    left_center = (-center_distance / 2.0, 0.0)
    right_center = (center_distance / 2.0, 0.0)
    pitch_angle = 2.0 * math.pi / teeth

    left = gear_points(
        left_center[0],
        left_center[1],
        teeth,
        root_radius,
        outer_radius,
        rotation=0.0,
    )
    right = gear_points(
        right_center[0],
        right_center[1],
        teeth,
        root_radius,
        outer_radius,
        rotation=math.pi - 0.5 * pitch_angle,
    )

    select_front_plane(model, null_dispatch)
    model.SketchManager.InsertSketch(True)
    draw_closed_polyline(model.SketchManager, left)
    model.SketchManager.InsertSketch(True)
    extrude_current_sketch(model, thickness)

    select_front_plane(model, null_dispatch)
    model.SketchManager.InsertSketch(True)
    draw_closed_polyline(model.SketchManager, right)
    model.SketchManager.InsertSketch(True)
    extrude_current_sketch(model, thickness)

    model.ForceRebuild3(False)
    result = model.SaveAs3(str(output.resolve()), 0, 2)
    print(f"SAVED_PART {output.resolve()}")
    print(f"SAVEAS3_RESULT {result}")


def export_png(sw, part: Path, png: Path) -> None:
    png = png.resolve()
    png.parent.mkdir(parents=True, exist_ok=True)
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model = sw.OpenDoc6(str(part.resolve()), 1, 1, "", errors, warnings) or sw.ActiveDoc
    if model is None:
        raise RuntimeError(f"Could not open generated part: {part}")

    model.ShowNamedView2("*Isometric", 7)
    model.ViewZoomtofit2()
    model.GraphicsRedraw2()

    bmp = png.with_suffix(".bmp")
    ok = model.SaveBMP(str(bmp.resolve()), 1400, 900)
    if not ok or not bmp.exists():
        raise RuntimeError(f"SaveBMP failed for {bmp}")

    from PIL import Image

    Image.open(bmp).save(png)
    bmp.unlink()
    print(f"SAVED_IMAGE {png.resolve()}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a meshing spur gear pair test part through SolidWorks COM."
    )
    parser.add_argument("--template")
    parser.add_argument("--output", default="solidworks_gear_pair_test.SLDPRT")
    parser.add_argument("--image-output")
    parser.add_argument("--teeth", type=int, default=24)
    parser.add_argument("--pitch-radius-mm", type=float, default=40.0)
    parser.add_argument("--root-radius-mm", type=float, default=35.8)
    parser.add_argument("--outer-radius-mm", type=float, default=44.0)
    parser.add_argument("--thickness-mm", type=float, default=12.0)
    args = parser.parse_args()

    pythoncom.CoInitialize()
    try:
        sw, source = connect_solidworks()
        print(f"CONNECTED source={source}")
        print(f"REVISION {sw.RevisionNumber}")
        template = find_template(args.template)
        create_gear_pair(
            sw,
            template,
            Path(args.output),
            args.teeth,
            args.pitch_radius_mm,
            args.root_radius_mm,
            args.outer_radius_mm,
            args.thickness_mm,
        )
        if args.image_output:
            export_png(sw, Path(args.output), Path(args.image_output))
    finally:
        pythoncom.CoUninitialize()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
