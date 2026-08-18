import cv2
import tkinter as tk
from tkinter import messagebox
import time


# ============================================================
# CONFIGURATION
# ============================================================
MAX_CAMERA_INDEX = 10

# A wide aspect ratio is a useful hint that a camera may
# output two views side-by-side.
STEREO_ASPECT_RATIO = 2.0

# Candidate side-by-side resolutions to test.
#
# These are requests, not guarantees. The camera/driver may
# reject a mode or silently substitute another resolution.
#
# The list goes from low to high so the UI can show exactly
# which modes the camera accepts.
CANDIDATE_RESOLUTIONS = (
    (640, 240),
    (1280, 480),
    (1920, 720),
    (2560, 960),
    (3840, 1080),
)

# Frames to discard after changing resolution. Camera drivers
# often need a few frames to settle.
RESOLUTION_WARMUP_FRAMES = 8

# Number of seconds used for FPS measurement after a mode
# has been selected.
FPS_TEST_DURATION = 2.0

# A mode below this FPS is considered unsuitable for the
# live calibration workflow.
MINIMUM_USABLE_FPS = 15.0


# ============================================================
# CAMERA UTILITIES
# ============================================================
def open_camera(index):
    """
    Open a camera using the Windows DirectShow backend.
    """
    return cv2.VideoCapture(index, cv2.CAP_DSHOW)


def get_frame_info(frame):
    """
    Extract basic information from a camera frame.
    """
    height, width = frame.shape[:2]
    channels = frame.shape[2] if len(frame.shape) == 3 else 1
    aspect_ratio = width / height

    return {
        "width": width,
        "height": height,
        "channels": channels,
        "aspect_ratio": aspect_ratio,
        "shape": frame.shape,
    }


def is_likely_stereo(aspect_ratio):
    """
    Determine whether a frame resembles a side-by-side
    stereo image based on its aspect ratio.
    """
    return aspect_ratio >= STEREO_ASPECT_RATIO


# ============================================================
# RESOLUTION TESTING
# ============================================================
def set_resolution(camera, width, height):
    """
    Request a resolution and verify the actual frame size.

    Returns:
        tuple[int, int] | None:
            Actual (width, height), or None if no frame can
            be obtained.
    """
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Give the driver a chance to switch modes.
    frame = None
    for _ in range(RESOLUTION_WARMUP_FRAMES):
        success, candidate = camera.read()
        if success and candidate is not None:
            frame = candidate

    if frame is None:
        return None

    # Use the actual frame dimensions rather than trusting
    # CAP_PROP_FRAME_WIDTH/HEIGHT, because some drivers report
    # stale property values.
    frame_height, frame_width = frame.shape[:2]

    if frame_width != actual_width or frame_height != actual_height:
        actual_width = frame_width
        actual_height = frame_height

    return actual_width, actual_height


def measure_fps(camera, duration=FPS_TEST_DURATION):
    """
    Measure approximate real-world FPS for the current mode.
    """
    frame_count = 0
    start_time = time.perf_counter()

    while True:
        success, frame = camera.read()

        if not success or frame is None:
            break

        frame_count += 1
        elapsed = time.perf_counter() - start_time

        if elapsed >= duration:
            break

    if elapsed <= 0:
        return 0.0

    return frame_count / elapsed


def probe_resolutions(camera_index):
    """
    Test candidate resolutions for a camera.

    Returns:
        list[dict]:
            Successfully opened modes. Each result contains
            requested and actual dimensions, per-camera
            dimensions, aspect ratio, stereo status and FPS.
    """
    camera = open_camera(camera_index)

    if not camera.isOpened():
        return []

    results = []
    seen_actual_modes = set()

    try:
        print("\n" + "=" * 65)
        print(" Resolution Probe")
        print("=" * 65)
        print(f"Camera index: {camera_index}")
        print()

        for requested_width, requested_height in CANDIDATE_RESOLUTIONS:
            actual = set_resolution(
                camera,
                requested_width,
                requested_height,
            )

            if actual is None:
                print(
                    f"{requested_width:4d} x {requested_height:<4d}"
                    " -> no usable frame"
                )
                continue

            actual_width, actual_height = actual
            actual_mode = (actual_width, actual_height)

            # If several requests collapse to the same driver
            # mode, don't measure and display that mode repeatedly.
            if actual_mode in seen_actual_modes:
                print(
                    f"{requested_width:4d} x {requested_height:<4d}"
                    f" -> {actual_width} x {actual_height}"
                    " (duplicate driver mode)"
                )
                continue

            seen_actual_modes.add(actual_mode)

            aspect_ratio = actual_width / actual_height
            stereo = is_likely_stereo(aspect_ratio)

            fps = measure_fps(camera)

            result = {
                "requested_width": requested_width,
                "requested_height": requested_height,
                "width": actual_width,
                "height": actual_height,
                "channels": 3,
                "aspect_ratio": aspect_ratio,
                "likely_stereo": stereo,
                "measured_fps": fps,
            }

            results.append(result)

            stereo_text = "stereo-like" if stereo else "not stereo-like"

            print(
                f"{requested_width:4d} x {requested_height:<4d}"
                f" -> {actual_width:4d} x {actual_height:<4d}"
                f" | {fps:5.1f} FPS"
                f" | {stereo_text}"
            )

        print("-" * 65)

        if results:
            usable = [
                result
                for result in results
                if result["likely_stereo"]
                and result["measured_fps"] >= MINIMUM_USABLE_FPS
            ]

            if usable:
                best = max(
                    usable,
                    key=lambda result: result["width"] * result["height"],
                )
                print(
                    "Recommended mode: "
                    f"{best['width']} x {best['height']} "
                    f"@ {best['measured_fps']:.1f} FPS"
                )
            else:
                print("No stereo mode met the minimum FPS requirement.")

        else:
            print("No usable resolution modes found.")

        print("=" * 65)

        return results

    finally:
        camera.release()


# ============================================================
# CAMERA DISCOVERY
# ============================================================
def scan_cameras():
    """
    Scan available camera indices and collect basic information.
    """
    cameras = []

    print("=" * 65)
    print(" Projectile Tracking - Camera Discovery")
    print("=" * 65)
    print("\nScanning for cameras...\n")

    for index in range(MAX_CAMERA_INDEX):
        camera = open_camera(index)

        if not camera.isOpened():
            camera.release()
            continue

        try:
            success, frame = camera.read()

            if not success or frame is None:
                continue

            info = get_frame_info(frame)

            camera_info = {
                "index": index,
                "width": info["width"],
                "height": info["height"],
                "channels": info["channels"],
                "aspect_ratio": info["aspect_ratio"],
                "shape": info["shape"],
                "likely_stereo": is_likely_stereo(
                    info["aspect_ratio"]
                ),
            }

            cameras.append(camera_info)

            print(f"[{index}] Camera detected")
            print(
                f"    Current resolution : "
                f"{info['width']} x {info['height']}"
            )
            print(f"    Frame shape        : {info['shape']}")
            print(f"    Channels           : {info['channels']}")
            print(
                f"    Aspect ratio       : "
                f"{info['aspect_ratio']:.2f}"
            )

            if camera_info["likely_stereo"]:
                print("    Likely stereo feed")

            print()

        finally:
            camera.release()

    print("-" * 65)

    if cameras:
        print(f"Found {len(cameras)} camera(s).")
    else:
        print("No cameras detected.")

    print()

    return cameras


# ============================================================
# CAMERA SELECTION UI
# ============================================================
def select_camera(cameras, parent=None):
    """
    Display detected cameras and allow the user to choose one.
    """
    owns_root = False

    if parent is None:
        parent = tk.Tk()
        parent.withdraw()
        owns_root = True

    try:
        if not cameras:
            messagebox.showerror(
                "No Cameras Found",
                (
                    "No cameras could be detected.\n\n"
                    "Make sure your camera is connected "
                    "and try again."
                ),
                parent=parent,
            )
            return None

        selected_camera = None

        window = tk.Toplevel(parent)
        window.title("Projectile Tracking - Camera Selection")
        window.geometry("650x430")
        window.resizable(False, False)

        tk.Label(
            window,
            text="Select Camera",
            font=("Arial", 18, "bold"),
        ).pack(pady=(20, 5))

        tk.Label(
            window,
            text=(
                "Choose the camera you want to use.\n"
                "The next step will test its supported "
                "stereo resolutions."
            ),
            font=("Arial", 10),
        ).pack(pady=5)

        listbox = tk.Listbox(
            window,
            width=75,
            height=12,
            font=("Consolas", 10),
        )
        listbox.pack(pady=15)

        for camera in cameras:
            stereo_label = (
                " Likely stereo"
                if camera["likely_stereo"]
                else ""
            )

            text = (
                f"[{camera['index']}] "
                f"{camera['width']} x {camera['height']} | "
                f"Aspect: {camera['aspect_ratio']:.2f}"
                f"{stereo_label}"
            )

            listbox.insert(tk.END, text)

        stereo_indices = [
            position
            for position, camera in enumerate(cameras)
            if camera["likely_stereo"]
        ]

        default_index = (
            stereo_indices[0]
            if stereo_indices
            else 0
        )

        listbox.selection_set(default_index)
        listbox.activate(default_index)

        def confirm_selection():
            nonlocal selected_camera

            selection = listbox.curselection()

            if not selection:
                messagebox.showwarning(
                    "No Camera Selected",
                    "Please select a camera first.",
                    parent=window,
                )
                return

            selected_camera = cameras[selection[0]]
            window.destroy()

        def cancel_selection():
            window.destroy()

        button_frame = tk.Frame(window)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Use Selected Camera",
            command=confirm_selection,
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
        ).pack(side="left", padx=8)

        tk.Button(
            button_frame,
            text="Cancel",
            command=cancel_selection,
            font=("Arial", 11),
            padx=20,
            pady=8,
        ).pack(side="left", padx=8)

        window.protocol(
            "WM_DELETE_WINDOW",
            cancel_selection,
        )

        window.transient(parent)
        window.grab_set()
        window.wait_window()

        return selected_camera

    finally:
        if owns_root:
            parent.destroy()


# ============================================================
# RESOLUTION SELECTION UI
# ============================================================
def select_resolution(resolutions, parent=None):
    """
    Display tested resolution modes and allow the user to
    choose one.

    The highest-resolution stereo mode meeting the minimum
    FPS requirement is highlighted automatically.
    """
    owns_root = False

    if parent is None:
        parent = tk.Tk()
        parent.withdraw()
        owns_root = True

    try:
        if not resolutions:
            messagebox.showerror(
                "No Resolution Modes",
                (
                    "The camera did not provide any usable "
                    "resolution modes."
                ),
                parent=parent,
            )
            return None

        selected_resolution = None

        window = tk.Toplevel(parent)
        window.title("Projectile Tracking - Resolution Selection")
        window.geometry("760x500")
        window.resizable(False, False)

        tk.Label(
            window,
            text="Select Camera Resolution",
            font=("Arial", 18, "bold"),
        ).pack(pady=(20, 5))

        tk.Label(
            window,
            text=(
                "Higher resolution gives the stereo calibration "
                "more image detail.\n"
                f"Modes below {MINIMUM_USABLE_FPS:.0f} FPS are "
                "marked as low FPS."
            ),
            font=("Arial", 10),
        ).pack(pady=5)

        listbox = tk.Listbox(
            window,
            width=88,
            height=14,
            font=("Consolas", 10),
        )
        listbox.pack(pady=15)

        for result in resolutions:
            per_eye_width = result["width"] // 2
            per_eye_height = result["height"]

            stereo_text = (
                "Stereo"
                if result["likely_stereo"]
                else "Not stereo-like"
            )

            fps_text = (
                f"{result['measured_fps']:.1f} FPS"
            )

            if result["measured_fps"] < MINIMUM_USABLE_FPS:
                fps_text += "  LOW FPS"

            text = (
                f"{result['width']:4d} x {result['height']:<4d}"
                f" | Per eye: {per_eye_width:4d} x "
                f"{per_eye_height:<4d}"
                f" | {fps_text:<15}"
                f" | {stereo_text}"
            )

            listbox.insert(tk.END, text)

        usable_stereo = [
            (position, result)
            for position, result in enumerate(resolutions)
            if result["likely_stereo"]
            and result["measured_fps"] >= MINIMUM_USABLE_FPS
        ]

        if usable_stereo:
            default_index = max(
                usable_stereo,
                key=lambda item: (
                    item[1]["width"] * item[1]["height"]
                ),
            )[0]
        else:
            stereo_only = [
                (position, result)
                for position, result in enumerate(resolutions)
                if result["likely_stereo"]
            ]

            default_index = (
                max(
                    stereo_only,
                    key=lambda item: (
                        item[1]["width"] * item[1]["height"]
                    ),
                )[0]
                if stereo_only
                else 0
            )

        listbox.selection_set(default_index)
        listbox.activate(default_index)
        listbox.see(default_index)

        def confirm_selection():
            nonlocal selected_resolution

            selection = listbox.curselection()

            if not selection:
                messagebox.showwarning(
                    "No Resolution Selected",
                    "Please select a resolution first.",
                    parent=window,
                )
                return

            selected_resolution = resolutions[selection[0]]
            window.destroy()

        def cancel_selection():
            window.destroy()

        button_frame = tk.Frame(window)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Use Selected Resolution",
            command=confirm_selection,
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
        ).pack(side="left", padx=8)

        tk.Button(
            button_frame,
            text="Cancel",
            command=cancel_selection,
            font=("Arial", 11),
            padx=20,
            pady=8,
        ).pack(side="left", padx=8)

        window.protocol(
            "WM_DELETE_WINDOW",
            cancel_selection,
        )

        window.transient(parent)
        window.grab_set()
        window.wait_window()

        return selected_resolution

    finally:
        if owns_root:
            parent.destroy()


# ============================================================
# STEREO PREVIEW
# ============================================================
def show_stereo_preview(frame):
    """
    Split a side-by-side frame into left and right views
    and display them separately.
    """
    height, width = frame.shape[:2]

    if width < 2 or width % 2 != 0:
        return None, None

    midpoint = width // 2

    left_frame = frame[:, :midpoint]
    right_frame = frame[:, midpoint:]

    cv2.imshow("Left Camera", left_frame)
    cv2.imshow("Right Camera", right_frame)

    return left_frame, right_frame


# ============================================================
# CAMERA TESTING
# ============================================================
def test_camera(
    camera_index,
    width,
    height,
    parent=None,
):
    """
    Open the selected camera at the chosen tested resolution,
    measure FPS, and provide a live preview.
    """
    camera = open_camera(camera_index)

    if not camera.isOpened():
        print(
            f"\nUnable to open camera {camera_index}."
        )
        return None

    info = None
    fps = 0.0

    try:
        actual = set_resolution(
            camera,
            width,
            height,
        )

        if actual is None:
            print(
                "\nUnable to obtain a frame at the "
                "selected resolution."
            )
            return None

        actual_width, actual_height = actual

        success, frame = camera.read()

        if not success or frame is None:
            print(
                "\nUnable to read frames from camera."
            )
            return None

        info = get_frame_info(frame)
        likely_stereo = is_likely_stereo(
            info["aspect_ratio"]
        )

        print("\n")
        print("=" * 65)
        print(" Selected Camera")
        print("=" * 65)
        print(f"Camera index      : {camera_index}")
        print(
            f"Requested resolution: "
            f"{width} x {height}"
        )
        print(
            f"Actual resolution : "
            f"{actual_width} x {actual_height}"
        )
        print(
            f"Per-eye resolution: "
            f"{actual_width // 2} x {actual_height}"
            if likely_stereo
            else "Per-eye resolution: N/A"
        )
        print(f"Frame shape       : {info['shape']}")
        print(f"Aspect ratio      : {info['aspect_ratio']:.2f}")

        fps = measure_fps(camera)
        print(f"Measured FPS      : {fps:.2f}")
        print("=" * 65)

        print("\nStarting live preview.")
        print("Press Q to exit.\n")

        while True:
            success, frame = camera.read()

            if not success:
                print("Failed to read frame.")
                break

            cv2.imshow(
                f"Camera {camera_index} - Raw Feed",
                frame,
            )

            if likely_stereo:
                show_stereo_preview(frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

        return {
            "index": camera_index,
            "width": actual_width,
            "height": actual_height,
            "channels": info["channels"],
            "aspect_ratio": info["aspect_ratio"],
            "shape": info["shape"],
            "likely_stereo": likely_stereo,
            "measured_fps": fps,
        }

    finally:
        camera.release()
        cv2.destroyAllWindows()

        if info is not None:
            print("\n")
            print("=" * 65)
            print(" Camera Test Summary")
            print("=" * 65)
            print(f"Camera index      : {camera_index}")
            print(
                f"Actual resolution : "
                f"{info['width']} x {info['height']}"
            )

            if likely_stereo:
                print(
                    f"Per-eye resolution: "
                    f"{info['width'] // 2} x "
                    f"{info['height']}"
                )

            print(f"Aspect ratio      : {info['aspect_ratio']:.2f}")
            print(f"Measured FPS      : {fps:.2f}")
            print(
                "Likely stereo     : "
                f"{'YES' if likely_stereo else 'NO'}"
            )
            print("=" * 65)
            print("\nCamera test completed successfully.")


# ============================================================
# COMPLETE CAMERA SETUP WORKFLOW
# ============================================================
def run_camera_setup(parent=None):
    """
    Run camera discovery, selection, resolution probing,
    resolution selection, and final testing.
    """
    cameras = scan_cameras()

    if not cameras:
        return None

    selected_camera = select_camera(
        cameras,
        parent=parent,
    )

    if selected_camera is None:
        print("Camera selection cancelled.")
        return None

    camera_index = selected_camera["index"]

    print(
        f"\nSelected camera index: {camera_index}"
    )

    resolutions = probe_resolutions(
        camera_index
    )

    if not resolutions:
        return None

    selected_resolution = select_resolution(
        resolutions,
        parent=parent,
    )

    if selected_resolution is None:
        print("Resolution selection cancelled.")
        return None

    width = selected_resolution["width"]
    height = selected_resolution["height"]

    print(
        f"\nSelected resolution: "
        f"{width} x {height}"
    )

    tested_camera = test_camera(
        camera_index,
        width,
        height,
        parent=parent,
    )

    if tested_camera is None:
        return None

    return tested_camera


# ============================================================
# MAIN
# ============================================================
def main():
    """
    Run camera discovery and testing as a standalone program.
    """
    run_camera_setup()


if __name__ == "__main__":
    main()