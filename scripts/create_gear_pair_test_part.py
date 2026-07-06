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


def tooth_profile(
    center_x: float,
    center_y: float,
    angle: float,
    pitch: float,
    root_radius: float,
    outer_radius: float,
) -> list[tuple[float, float]]:
    samples = [
        (angle - 0.24 * pitch, root_radius),
        (angle - 0.18 * pitch, outer_radius),
        (angle + 0.18 * pitch, outer_radius),
        (angle + 0.24 * pitch, root_radius),
    ]
    return [
        (
            center_x + radius * math.cos(sample_angle),
            center_y + radius * math.sin(sample_angle),
        )
        for sample_angle, radius in samples
    ]


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


def create_ring_base(
    model,
    null_dispatch,
    center: tuple[float, float],
    root_radius: float,
    hole_radius: float,
    thickness: float,
) -> None:
    select_front_plane(model, null_dispatch)
    model.SketchManager.InsertSketch(True)
    model.SketchManager.CreateCircleByRadius(center[0], center[1], 0.0, root_radius)
    model.SketchManager.CreateCircleByRadius(center[0], center[1], 0.0, hole_radius)
    model.SketchManager.InsertSketch(True)
    extrude_current_sketch(model, thickness)


def create_teeth(
    model,
    null_dispatch,
    center: tuple[float, float],
    teeth: int,
    root_radius: float,
    outer_radius: float,
    rotation: float,
    thickness: float,
) -> None:
    pitch = 2.0 * math.pi / teeth
    for index in range(teeth):
        select_front_plane(model, null_dispatch)
        model.SketchManager.InsertSketch(True)
        profile = tooth_profile(
            center[0],
            center[1],
            rotation + index * pitch,
            pitch,
            root_radius,
            outer_radius,
        )
        draw_closed_polyline(model.SketchManager, profile)
        model.SketchManager.InsertSketch(True)
        extrude_current_sketch(model, thickness)


def create_gear_pair(
    sw,
    template: str,
    output: Path,
    large_teeth: int,
    small_teeth: int,
    module_mm: float,
    thickness_mm: float,
    center_clearance_mm: float,
) -> None:
    null_dispatch = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    close_document_by_path(sw, output)
    model = sw.NewDocument(template, 0, 0, 0) or sw.ActiveDoc
    if model is None:
        raise RuntimeError(f"Could not create a part from template: {template}")

    module = module_mm / 1000.0
    thickness = thickness_mm / 1000.0
    large_pitch_radius = 0.5 * large_teeth * module
    small_pitch_radius = 0.5 * small_teeth * module
    large_root_radius = large_pitch_radius - 1.25 * module
    small_root_radius = small_pitch_radius - 1.25 * module
    large_outer_radius = large_pitch_radius + module
    small_outer_radius = small_pitch_radius + module
    center_distance = large_pitch_radius + small_pitch_radius + center_clearance_mm / 1000.0
    left_center = (-small_pitch_radius, 0.0)
    right_center = (large_pitch_radius + center_clearance_mm / 1000.0, 0.0)
    large_pitch_angle = 2.0 * math.pi / large_teeth

    create_ring_base(model, null_dispatch, left_center, large_root_radius, 0.012, thickness)
    create_teeth(
        model,
        null_dispatch,
        left_center,
        large_teeth,
        large_root_radius,
        large_outer_radius,
        rotation=0.5 * large_pitch_angle,
        thickness=thickness,
    )
    create_ring_base(model, null_dispatch, right_center, small_root_radius, 0.008, thickness)
    create_teeth(
        model,
        null_dispatch,
        right_center,
        small_teeth,
        small_root_radius,
        small_outer_radius,
        rotation=math.pi,
        thickness=thickness,
    )

    model.ForceRebuild3(False)
    result = model.SaveAs3(str(output.resolve()), 0, 2)
    print(f"SAVED_PART {output.resolve()}")
    print(f"SAVEAS3_RESULT {result}")


def close_document_by_path(sw, path: Path) -> None:
    target = str(path.resolve()).lower()
    try:
        documents = sw.GetDocuments()
    except Exception:
        return

    if documents is None:
        return

    for document in documents:
        try:
            document_path = (
                document.GetPathName
                if isinstance(document.GetPathName, str)
                else document.GetPathName()
            )
            document_path = str(document_path).lower()
            title = document.GetTitle if isinstance(document.GetTitle, str) else document.GetTitle()
        except Exception:
            continue
        if document_path == target:
            sw.CloseDoc(title)
            print(f"CLOSED_EXISTING {path.resolve()}")
            return


def close_document(sw, part: Path) -> None:
    try:
        model = sw.ActiveDoc
        if model is None:
            return
        path_name = model.GetPathName if isinstance(model.GetPathName, str) else model.GetPathName()
        path_name = str(path_name).lower()
        title = model.GetTitle if isinstance(model.GetTitle, str) else model.GetTitle()
        if path_name == str(part.resolve()).lower():
            sw.CloseDoc(title)
            print(f"CLOSED_DOC {part.resolve()}")
    except Exception as exc:
        print(f"WARN_CLOSE_DOC_FAILED {exc!r}")


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
    parser.add_argument("--large-teeth", type=int, default=32)
    parser.add_argument("--small-teeth", type=int, default=20)
    parser.add_argument("--module-mm", type=float, default=3.0)
    parser.add_argument("--thickness-mm", type=float, default=12.0)
    parser.add_argument("--center-clearance-mm", type=float, default=0.8)
    parser.add_argument("--keep-open", action="store_true")
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
            args.large_teeth,
            args.small_teeth,
            args.module_mm,
            args.thickness_mm,
            args.center_clearance_mm,
        )
        if args.image_output:
            export_png(sw, Path(args.output), Path(args.image_output))
        if not args.keep_open:
            close_document(sw, Path(args.output))
    finally:
        pythoncom.CoUninitialize()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
