import json
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# ============================================================
# PROJECT PATHS
# ============================================================
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CALIBRATION_DIR = PROJECT_ROOT / "data" / "calibration"
CAMERA_CONFIG_PATH = CALIBRATION_DIR / "camera_config.json"
STEREO_CALIBRATION_PATH = CALIBRATION_DIR / "stereo_calibration.npz"

# ============================================================
# IMPORTS
# ============================================================
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from camera import StereoCamera
from setup import camera_test
from setup import calibration


# ============================================================
# CAMERA CONFIGURATION STORAGE
# ============================================================
def load_camera_config():
    """
    Load the previously saved camera configuration.

    Returns:
        dict or None:
            Camera configuration if it exists and is valid.
    """
    if not CAMERA_CONFIG_PATH.is_file():
        return None

    try:
        with CAMERA_CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"[MAIN] Failed to load camera configuration: {error}")
        return None

    required_keys = {"index", "width", "height"}
    if not required_keys.issubset(config):
        print("[MAIN] Camera configuration is incomplete.")
        return None

    return config


def save_camera_config(config):
    """
    Save the camera configuration returned by camera_test.py.

    Args:
        config (dict): Tested camera configuration.

    Returns:
        bool:
            True if the configuration was saved successfully.
    """
    required_keys = {"index", "width", "height"}
    if not required_keys.issubset(config):
        print(
            "[MAIN] Cannot save camera configuration. "
            "Required values are missing."
        )
        return False

    try:
        CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
        with CAMERA_CONFIG_PATH.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)
    except OSError as error:
        print(f"[MAIN] Failed to save camera configuration: {error}")
        return False

    print(f"[MAIN] Camera configuration saved:\n    {CAMERA_CONFIG_PATH}")
    return True


# ============================================================
# SETUP STATE
# ============================================================
def camera_config_exists():
    """
    Return True if a valid camera configuration is saved.
    """
    return load_camera_config() is not None


def calibration_exists():
    """
    Return True if stereo calibration data is saved.
    """
    return STEREO_CALIBRATION_PATH.is_file()


def setup_complete():
    """
    Return True when both required setup artifacts exist.
    """
    return camera_config_exists() and calibration_exists()


# ============================================================
# MAIN APPLICATION
# ============================================================
class ProjectileTrackingApp:
    """
    High-level application controller.

    main.py is responsible only for orchestration, and owns the
    single Tk() root and mainloop() for the entire application.

    Camera discovery/testing:  camera_test.py
    Camera interface:          camera.py
    Stereo calibration:        calibration.py
    Future processing:         depth.py, tracking.py, trajectory.py

    Every dialog opened by camera_test.py or calibration.py is
    created as a Toplevel of self.root (passed in as `parent`),
    never as an independent tk.Tk(). This module is the only
    place tk.Tk() is called and the only place mainloop() runs.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Projectile Tracking System")
        self.root.geometry("650x500")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)

        self.build_ui()

    # ========================================================
    # UI
    # ========================================================
    def build_ui(self):
        """
        Build the main application window.
        """
        tk.Label(
            self.root,
            text="Projectile Tracking System",
            font=("Arial", 22, "bold"),
        ).pack(pady=(35, 8))

        tk.Label(
            self.root,
            text="Stereo camera setup and projectile tracking",
            font=("Arial", 11),
        ).pack(pady=(0, 25))

        self.camera_status = tk.Label(self.root, font=("Arial", 11))
        self.camera_status.pack(pady=4)

        self.calibration_status = tk.Label(self.root, font=("Arial", 11))
        self.calibration_status.pack(pady=4)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=30)

    def clear_buttons(self):
        """
        Remove all buttons currently displayed.
        """
        for widget in self.button_frame.winfo_children():
            widget.destroy()

    def add_button(self, text, command):
        """
        Add a standard application button.
        """
        tk.Button(
            self.button_frame,
            text=text,
            command=command,
            font=("Arial", 12),
            width=24,
            pady=8,
        ).pack(pady=6)

    def update_status(self):
        """
        Update the setup status shown in the main UI.
        """
        self.camera_status.config(
            text=(
                "Camera configuration: "
                f"{'READY' if camera_config_exists() else 'NOT SET UP'}"
            )
        )
        self.calibration_status.config(
            text=(
                "Stereo calibration: "
                f"{'READY' if calibration_exists() else 'NOT SET UP'}"
            )
        )

    # ========================================================
    # MAIN MENUS
    # ========================================================
    def show_first_run_menu(self):
        """
        Display the initial setup menu.
        """
        self.update_status()
        self.clear_buttons()

        tk.Label(
            self.button_frame,
            text=(
                "Initial setup is required before tracking.\n\n"
                "The setup wizard will configure the camera "
                "and perform stereo calibration."
            ),
            font=("Arial", 11),
            justify="center",
        ).pack(pady=(0, 20))

        self.add_button("Start Setup", self.start_setup)
        self.add_button("Exit", self.exit_application)

    def show_main_menu(self):
        """
        Display the normal application menu.
        """
        self.update_status()
        self.clear_buttons()

        self.add_button("Start Tracking", self.start_tracking)
        self.add_button("Run Setup Again", self.start_setup)
        self.add_button("Exit", self.exit_application)

    # ========================================================
    # CAMERA SETUP
    # ========================================================
    def run_camera_setup(self):
        """
        Delegate the complete camera workflow to camera_test.py.

        camera_test.py handles:
            - camera discovery
            - camera selection UI
            - camera testing
            - returning the tested configuration

        The application's single root is passed as `parent` so
        the selection dialog is a Toplevel, not a second Tk root.

        Returns:
            dict or None
        """
        print("\n[MAIN] Starting camera_test.run_camera_setup()")

        config = camera_test.run_camera_setup(parent=self.root)

        if config is None:
            print("[MAIN] Camera setup returned no configuration.")
            return None

        print("[MAIN] Camera setup completed.")
        print(f"[MAIN] Camera index: {config['index']}")
        print(f"[MAIN] Resolution: {config['width']} x {config['height']}")

        return config

    # ========================================================
    # CALIBRATION
    # ========================================================
    def run_stereo_calibration(self, stereo_camera):
        """
        Delegate stereo calibration to calibration.py.

        The application's single root is passed as `parent` so
        every calibration dialog (checkerboard config, guided
        capture, results) is a Toplevel of it.

        Args:
            stereo_camera (StereoCamera):
                Configured stereo camera instance.

        Returns:
            bool:
                True if calibration succeeds.
        """
        print("\n[MAIN] Starting calibration.run_calibration()")

        result = calibration.run_calibration(stereo_camera, parent=self.root)

        print(f"[MAIN] Calibration result: {result}")

        return result

    # ========================================================
    # SETUP WORKFLOW
    # ========================================================
    def start_setup(self):
        """
        Execute the complete setup workflow.

        Every explicit request for setup runs camera selection
        again. Normal application launches never enter this
        function when setup is already complete.

        Note: the main window is deliberately left visible (not
        withdrawn) during setup. Every setup dialog is a Toplevel
        that is transient to self.root and uses grab_set(), which
        already makes them modal. Withdrawing self.root here would
        also silently withdraw every Toplevel transient to it --
        that's Tk's documented behavior for transient windows, and
        it's what was causing the setup dialogs not to appear.
        """
        stereo_camera = None

        try:
            # ------------------------------------------------
            # CAMERA SETUP
            # ------------------------------------------------
            messagebox.showinfo(
                "Camera Setup",
                (
                    "Camera setup will now begin.\n\n"
                    "The camera setup window will let you "
                    "select and test your stereo camera."
                ),
            )

            selected_config = self.run_camera_setup()

            if selected_config is None:
                messagebox.showwarning(
                    "Setup Cancelled",
                    (
                        "Camera setup was cancelled or failed.\n\n"
                        "Stereo calibration was not started."
                    ),
                )
                return

            # ------------------------------------------------
            # SAVE CAMERA CONFIGURATION
            # ------------------------------------------------
            if not save_camera_config(selected_config):
                messagebox.showerror(
                    "Setup Error",
                    (
                        "The camera was selected successfully, "
                        "but its configuration could not be saved."
                    ),
                )
                return

            # ------------------------------------------------
            # CREATE STEREO CAMERA
            # ------------------------------------------------
            stereo_camera = StereoCamera(selected_config)
            print("[MAIN] StereoCamera instance created.")

            # ------------------------------------------------
            # CALIBRATION
            # ------------------------------------------------
            messagebox.showinfo(
                "Stereo Calibration",
                (
                    "Camera setup is complete.\n\n"
                    "Stereo calibration will now begin.\n\n"
                    "Use the project's supplied checkerboard "
                    "and follow the instructions shown by "
                    "the calibration window."
                ),
            )

            calibration_success = self.run_stereo_calibration(stereo_camera)

            if not calibration_success:
                messagebox.showwarning(
                    "Calibration Not Completed",
                    (
                        "Stereo calibration was not completed.\n\n"
                        "The camera configuration has been saved.\n"
                        "You can run setup again when ready."
                    ),
                )
                return

            # ------------------------------------------------
            # COMPLETE
            # ------------------------------------------------
            messagebox.showinfo(
                "Setup Complete",
                (
                    "Setup completed successfully.\n\n"
                    "Camera configuration: READY\n"
                    "Stereo calibration: READY"
                ),
            )

        except Exception as error:
            print("\n[MAIN] SETUP ERROR")
            print(repr(error))
            messagebox.showerror(
                "Setup Error",
                f"An unexpected error occurred during setup:\n\n{error}",
            )

        finally:
            if stereo_camera is not None:
                stereo_camera.release()

            self.update_status()

            if setup_complete():
                self.show_main_menu()
            else:
                self.show_first_run_menu()

    # ========================================================
    # TRACKING PLACEHOLDER
    # ========================================================
    def start_tracking(self):
        """
        Placeholder for the future tracking pipeline.
        """
        messagebox.showinfo(
            "Tracking",
            (
                "Tracking is not implemented yet.\n\n"
                "Camera setup and stereo calibration are "
                "the current development stage."
            ),
        )

    # ========================================================
    # EXIT
    # ========================================================
    def exit_application(self):
        """
        Close the application.
        """
        self.root.destroy()

    def run(self):
        """
        Start the Tkinter event loop.
        """
        if setup_complete():
            self.show_main_menu()
        else:
            self.show_first_run_menu()

        self.root.mainloop()


# ============================================================
# ENTRY POINT
# ============================================================
def main():
    """
    Application entry point.
    """
    application = ProjectileTrackingApp()
    application.run()


if __name__ == "__main__":
    main()