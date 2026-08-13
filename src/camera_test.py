import cv2
import tkinter as tk
from tkinter import messagebox
import time

# CONFIGURATION
MAX_CAMERA_INDEX = 10
# A wide aspect ratio is a useful hint that a camera may be outputting two views side-by-side.
STEREO_ASPECT_RATIO = 2.0
# Number of seconds used for the FPS measurement.
FPS_TEST_DURATION = 3

# CAMERA UTILITIES
def open_camera(index):
    """
    Open a camera using the Windows DirectShow backend.
    Returns:
        cv2.VideoCapture object
    """

    camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return camera


def get_frame_info(frame):
    """
    Extract basic information from a frame.

    Returns:
        Dictionary containing frame dimensions and properties.
    """

    height, width = frame.shape[:2]
    if len(frame.shape) == 3:
        channels = frame.shape[2]
    else:
        channels = 1
    aspect_ratio = width / height
    return {
        "width": width,
        "height": height,
        "channels": channels,
        "aspect_ratio": aspect_ratio,
        "shape": frame.shape
    }


def is_likely_stereo(aspect_ratio):
    """
    Determine whether a frame has an aspect ratio that
    resembles a side-by-side stereo image.

    This is only a heuristic. It does NOT prove that the
    camera is stereo.
    """

    return aspect_ratio >= STEREO_ASPECT_RATIO


# CAMERA DISCOVERY
def scan_cameras():
    """
    Scan available camera indices and collect basic information.
    """

    cameras = []
    print("=" * 55)
    print("       Projectile Tracking - Camera Discovery")
    print("=" * 55)
    print("\nScanning for cameras...\n")
    for index in range(MAX_CAMERA_INDEX):
        camera = open_camera(index)

        if not camera.isOpened():
            camera.release()
            continue
        success, frame = camera.read()

        if not success or frame is None:
            camera.release()
            continue
        info = get_frame_info(frame)

        likely_stereo = is_likely_stereo(
            info["aspect_ratio"]
        )

        camera_info = {
            "index": index,
            "width": info["width"],
            "height": info["height"],
            "channels": info["channels"],
            "aspect_ratio": info["aspect_ratio"],
            "shape": info["shape"],
            "likely_stereo": likely_stereo
        }
        cameras.append(camera_info)
        print(f"[{index}] Camera detected")
        print(f"    Resolution   : "
              f"{info['width']} x {info['height']}")
        print(f"    Frame shape  : {info['shape']}")
        print(f"    Channels     : {info['channels']}")
        print(f"    Aspect ratio : "
              f"{info['aspect_ratio']:.2f}")

        if likely_stereo:
            print("  Likely stereo feed")
        print()

        camera.release()

    print("-" * 55)
    if not cameras:
        print(" No cameras detected.")
    else:
        print(f"Found {len(cameras)} camera(s).")
    print()
    return cameras


# CAMERA SELECTION

def select_camera(cameras):
    """
    Display detected cameras and allow the user to choose one.

    Returns:
        Selected camera index, or None.
    """
    if not cameras:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "No Cameras Found",
            "No cameras could be detected.\n\n"
            "Make sure your camera is connected and try again."
        )
        root.destroy()
        return None
    root = tk.Tk()
    root.title(
        "Projectile Tracking - Camera Selection"
    )
    root.geometry("650x430")
    root.resizable(False, False)

    # Title
    title = tk.Label(
        root,
        text="Select Camera",
        font=("Arial", 18, "bold")
    )
    title.pack(pady=(20, 5))

    # Description
    subtitle = tk.Label(
        root,
        text=(
            "Choose the camera you want to test.\n"
            "⭐ indicates a camera that looks like a "
            "possible stereo feed."
        ),
        font=("Arial", 10)
    )
    subtitle.pack(pady=5)

    # Camera list
    listbox = tk.Listbox(
        root,
        width=75,
        height=12,
        font=("Consolas", 10)
    )
    listbox.pack(pady=15)
    for camera in cameras:
        stereo_label = ""
        if camera["likely_stereo"]:
            stereo_label = " Likely stereo"
        text = (
            f"[{camera['index']}]  "
            f"{camera['width']} x "
            f"{camera['height']}  | "
            f"Aspect: {camera['aspect_ratio']:.2f}"
            f"{stereo_label}"
        )
        listbox.insert(
            tk.END,
            text
        )

    # Automatically highlight likely stereo camera
    stereo_indices = [
        i
        for i, camera in enumerate(cameras)
        if camera["likely_stereo"]
    ]
    if stereo_indices:
        listbox.selection_set(
            stereo_indices[0]
        )
        listbox.activate(
            stereo_indices[0]
        )
    else:
        listbox.selection_set(0)
        listbox.activate(0)
    selected_camera = {
        "index": None
    }

    # Selection callback
    def confirm_selection():
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "No Camera Selected",
                "Please select a camera first."
            )
            return
        selected = cameras[
            selection[0]
        ]
        selected_camera["index"] = (
            selected["index"]
        )
        root.destroy()

    # Button
    button = tk.Button(
        root,
        text="Use Selected Camera",
        command=confirm_selection,
        font=("Arial", 11, "bold"),
        padx=20,
        pady=8
    )
    button.pack(pady=10)
    root.mainloop()
    return selected_camera["index"]


# FPS MEASUREMENT

def measure_fps(camera):
    """
    Measure the approximate real-world FPS of a camera.

    Returns:
        Measured FPS.
    """
    print("\nMeasuring camera FPS...")
    print(f"Test duration: {FPS_TEST_DURATION} seconds")
    frame_count = 0
    start_time = time.perf_counter()

    while True:
        success, frame = camera.read()
        if not success:
            break

        frame_count += 1
        elapsed = (
            time.perf_counter() - start_time
        )

        if elapsed >= FPS_TEST_DURATION:
            break

    if elapsed <= 0:
        return 0.0

    fps = frame_count / elapsed
    return fps

# STEREO PREVIEW
def show_stereo_preview(frame):
    """
    Split a side-by-side frame into left and right views
    and display them separately.

    This function assumes a side-by-side layout.
    """

    height, width = frame.shape[:2]
    midpoint = width // 2
    left_frame = frame[:, :midpoint]
    right_frame = frame[:, midpoint:]
    cv2.imshow(
        "Left Camera",
        left_frame
    )
    cv2.imshow(
        "Right Camera",
        right_frame
    )
    return left_frame, right_frame

# CAMERA TESTING

def test_camera(camera_index):
    """
    Open the selected camera, inspect its output,
    measure FPS, and provide a live preview.
    """
    camera = open_camera(camera_index)
    if not camera.isOpened():
        print(
            f"\n Unable to open camera "
            f"{camera_index}."
        )

        return

    # First frame
    success, frame = camera.read()
    if not success or frame is None:
        print(
            f"\n Unable to read frames "
            f"from camera {camera_index}."
        )
        camera.release()
        return

    info = get_frame_info(frame)
    likely_stereo = is_likely_stereo(
        info["aspect_ratio"]
    )

    # Camera properties
    print("\n")
    print("=" * 55)
    print("              Selected Camera")
    print("=" * 55)
    print(
        f"Camera index : {camera_index}"
    )
    print(
        f"Resolution   : "
        f"{info['width']} x {info['height']}"
    )
    print(
        f"Frame shape  : "
        f"{info['shape']}"
    )
    print(
        f"Channels     : "
        f"{info['channels']}"
    )
    print(
        f"Aspect ratio : "
        f"{info['aspect_ratio']:.2f}"
    )

    if likely_stereo:
        print(
            "Stereo status: Likely stereo feed"
        )
    else:
        print(
            "Stereo status: Standard camera aspect ratio"
        )

    # FPS
    fps = measure_fps(camera)
    print(
        f"Measured FPS : {fps:.2f}"
    )
    print("=" * 55)

    # Preview
    print("\nStarting live preview.")
    print("Press Q to exit.")
    print()
    while True:
        success, frame = camera.read()
        if not success:
            print(
                "Failed to read frame."
            )
            break

        cv2.imshow(
            f"Camera {camera_index} - Raw Feed",
            frame
        )
        # If the feed looks stereo, also show
        # the two halves independently.
        if likely_stereo:
            show_stereo_preview(frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    # Cleanup
    camera.release()
    cv2.destroyAllWindows()

    # Final summary
    print("\n")
    print("=" * 55)
    print("             Camera Test Summary")
    print("=" * 55)
    print(
        f"Camera index    : {camera_index}"
    )
    print(
        f"Resolution      : "
        f"{info['width']} x {info['height']}"
    )
    print(
        f"Frame shape     : "
        f"{info['shape']}"
    )
    print(
        f"Aspect ratio    : "
        f"{info['aspect_ratio']:.2f}"
    )
    print(
        f"Measured FPS    : "
        f"{fps:.2f}"
    )
    print(
        f"Likely stereo   : "
        f"{'YES' if likely_stereo else 'NO'}"
    )
    if likely_stereo:
        half_width = info["width"] // 2
        print(
            f"Possible L/R size: "
            f"{half_width} x {info['height']} each"
        )
    print("=" * 55)
    print(
        "\nCamera test completed successfully."
    )

# MAIN
def main():
    cameras = scan_cameras()
    if not cameras:
        return
    selected_camera = select_camera(cameras)

    if selected_camera is None:
        print("No camera selected.")
        return

    print(
        f"\nSelected camera index: "
        f"{selected_camera}"
    )
    test_camera(
        selected_camera
    )


if __name__ == "__main__":
    main()