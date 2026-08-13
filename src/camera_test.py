import cv2
import tkinter as tk
from tkinter import messagebox

# Configuration
MAX_CAMERA_INDEX = 10
# A very wide image is a strong hint that this may be a stereo camera outputting two views side-by-side.
STEREO_ASPECT_RATIO = 2.0
# Camera discovery

def scan_cameras():
    """
    Scan available camera indices and collect basic information.
    """
    cameras = []
    print("=" * 50)
    print("Projectile Tracking - Camera Discovery")
    print("=" * 50)
    print("\nScanning for cameras...\n")
    for index in range(MAX_CAMERA_INDEX):
        camera = cv2.VideoCapture(index)
        if not camera.isOpened():
            camera.release()
            continue
        success, frame = camera.read()
        if not success or frame is None:
            camera.release()
            continue
        height, width = frame.shape[:2]
        aspect_ratio = width / height
        likely_stereo = aspect_ratio >= STEREO_ASPECT_RATIO
        camera_info = {
            "index": index,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "likely_stereo": likely_stereo
        }
        cameras.append(camera_info)

        print(f"[{index}] Camera detected")
        print(f"    Resolution   : {width} x {height}")
        print(f"    Aspect ratio : {aspect_ratio:.2f}")

        if likely_stereo:
            print(" Likely stereo camera")
        print()

        camera.release()

    print("-" * 50)

    if not cameras:
        print(" No cameras detected.")
        print("-" * 50)

    else:
        print(f"Found {len(cameras)} camera(s).")
    print()
    return cameras


# Camera selection window
def select_camera(cameras):
    """
    Display detected cameras and let the user choose one.
    Returns the selected camera index.
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
    root.title("Projectile Tracking - Camera Selection")
    root.geometry("600x400")
    root.resizable(False, False)
    title = tk.Label(
        root,
        text="Select Camera",
        font=("Arial", 18, "bold")
    )
    title.pack(pady=15)

    subtitle = tk.Label(
        root,
        text=(
            "Choose the camera you want to use.\n"
            "A indicates a camera that looks like a stereo feed."
        ),
        font=("Arial", 10)
    )

    subtitle.pack(pady=5)

    listbox = tk.Listbox(
        root,
        width=70,
        height=10,
        font=("Consolas", 10)
    )

    listbox.pack(pady=15)

    # Add cameras to the list
    for camera in cameras:
        stereo_label = " Likely stereo" if camera["likely_stereo"] else ""
        text = (
            f"[{camera['index']}]  "
            f"{camera['width']} x {camera['height']}  "
            f"(aspect {camera['aspect_ratio']:.2f})"
            f"{stereo_label}"
        )
        listbox.insert(tk.END, text)

    # Automatically select the most likely stereo camera
    stereo_indices = [
        i for i, camera in enumerate(cameras)
        if camera["likely_stereo"]
    ]

    if stereo_indices:
        listbox.selection_set(stereo_indices[0])
        listbox.activate(stereo_indices[0])
    else:
        listbox.selection_set(0)
        listbox.activate(0)

    selected_camera = {"index": None}
    def confirm_selection():
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning(
                "No Camera Selected",
                "Please select a camera first."
            )
            return

        selected = cameras[selection[0]]
        selected_camera["index"] = selected["index"]
        root.destroy()
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



# Camera preview
def test_camera(camera_index):
    """
    Open the selected camera and display its live feed.
    """
    camera = cv2.VideoCapture(camera_index)

    if not camera.isOpened():
        print(f"\n Unable to open camera {camera_index}.")
        return
    success, frame = camera.read()
    if not success or frame is None:
        print(f"\n Unable to read frames from camera {camera_index}.")
        camera.release()
        return
    height, width = frame.shape[:2]
    aspect_ratio = width / height
    print("=" * 50)
    print("Selected Camera")
    print("=" * 50)
    print(f"Camera index : {camera_index}")
    print(f"Resolution   : {width} x {height}")
    print(f"Aspect ratio : {aspect_ratio:.2f}")

    if aspect_ratio >= STEREO_ASPECT_RATIO:
        print("Status       : Looks like a stereo feed")
    else:
        print("Status       : Standard camera aspect ratio")

    print("\nPress Q to exit the preview.")
    print("=" * 50)

    while True:
        success, frame = camera.read()
        if not success:
            print(" Failed to read frame.")
            break
        cv2.imshow(
            f"Camera {camera_index} - Projectile Tracking",
            frame
        )
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
    camera.release()
    cv2.destroyAllWindows()


# Main

def main():
    cameras = scan_cameras()
    if not cameras:
        return
    selected_camera = select_camera(cameras)
    if selected_camera is None:
        print("No camera selected.")
        return

    print(f"\nSelected camera index: {selected_camera}")
    test_camera(selected_camera)

if __name__ == "__main__":
    main()
