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

CAMERA_CONFIG_PATH = (
    CALIBRATION_DIR / "camera_config.json"
)

STEREO_CALIBRATION_PATH = (
    CALIBRATION_DIR / "stereo_calibration.npz"
)


# ============================================================
# IMPORTS
# ============================================================
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from camera import StereoCamera
from setup import camera_test
from setup import calibration
from depth import run_depth


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
        with CAMERA_CONFIG_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ) as error:
        print(
            f"[MAIN] Failed to load camera configuration: "
            f"{error}"
        )
        return None

    required_keys = {
        "index",
        "width",
        "height",
    }

    if not required_keys.issubset(config):
        print(
            "[MAIN] Camera configuration is incomplete."
        )
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
    required_keys = {
        "index",
        "width",
        "height",
    }

    if not required_keys.issubset(config):
        print(
            "[MAIN] Cannot save camera configuration. "
            "Required values are missing."
        )
        return False

    try:
        CALIBRATION_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        with CAMERA_CONFIG_PATH.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                config,
                file,
                indent=4,
            )

    except OSError as error:
        print(
            f"[MAIN] Failed to save camera configuration: "
            f"{error}"
        )
        return False

    print(
        "[MAIN] Camera configuration saved:\n"
        f"    {CAMERA_CONFIG_PATH}"
    )

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
    return (
        camera_config_exists()
        and calibration_exists()
    )


# ============================================================
# MAIN APPLICATION
# ============================================================
class ProjectileTrackingApp:
    """
    High-level application controller.

    main.py is responsible for application orchestration and
    owns the single Tk() root and mainloop().

    Current workflow:

        camera_test.py
            ↓
        camera.py
            ↓
        calibration.py
            ↓
        depth.py
            ↓
        tracking.py
            ↓
        trajectory.py

    Current depth stage:
        - static crushed paper-ball detection
        - stereo correspondence
        - disparity
        - depth estimation
        - 3D position

    Every application window is a Toplevel of self.root.
    This module is the only place tk.Tk() is created and the
    only place mainloop() is started.
    """

    def __init__(self):
        self.root = tk.Tk()

        self.root.title(
            "Projectile Tracking System"
        )

        self.root.geometry(
            "650x500"
        )

        self.root.resizable(
            False,
            False,
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.exit_application,
        )

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
        ).pack(
            pady=(35, 8)
        )

        tk.Label(
            self.root,
            text=(
                "Stereo camera setup and "
                "3D object localization"
            ),
            font=("Arial", 11),
        ).pack(
            pady=(0, 25)
        )

        self.camera_status = tk.Label(
            self.root,
            font=("Arial", 11),
        )

        self.camera_status.pack(
            pady=4
        )

        self.calibration_status = tk.Label(
            self.root,
            font=("Arial", 11),
        )

        self.calibration_status.pack(
            pady=4
        )

        self.button_frame = tk.Frame(
            self.root
        )

        self.button_frame.pack(
            pady=30
        )

    def clear_buttons(self):
        """
        Remove all buttons currently displayed.
        """
        for widget in (
            self.button_frame.winfo_children()
        ):
            widget.destroy()

    def add_button(
        self,
        text,
        command,
    ):
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
        ).pack(
            pady=6
        )

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
                "Initial setup is required before "
                "3D localization.\n\n"
                "The setup wizard will configure the "
                "camera and perform stereo calibration."
            ),
            font=("Arial", 11),
            justify="center",
        ).pack(
            pady=(0, 20)
        )

        self.add_button(
            "Start Setup",
            self.start_setup,
        )

        self.add_button(
            "Exit",
            self.exit_application,
        )

    def show_main_menu(self):
        """
        Display the normal application menu.
        """
        self.update_status()
        self.clear_buttons()

        self.add_button(
            "Start Tracking",
            self.start_tracking,
        )

        self.add_button(
            "Run Setup Again",
            self.start_setup,
        )

        self.add_button(
            "Exit",
            self.exit_application,
        )

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
        print(
            "\n[MAIN] Starting "
            "camera_test.run_camera_setup()"
        )

        config = camera_test.run_camera_setup(
            parent=self.root
        )

        if config is None:
            print(
                "[MAIN] Camera setup returned "
                "no configuration."
            )
            return None

        print(
            "[MAIN] Camera setup completed."
        )

        print(
            f"[MAIN] Camera index: "
            f"{config['index']}"
        )

        print(
            f"[MAIN] Resolution: "
            f"{config['width']} x "
            f"{config['height']}"
        )

        return config

    # ========================================================
    # CALIBRATION
    # ========================================================
    def run_stereo_calibration(
        self,
        stereo_camera,
    ):
        """
        Delegate stereo calibration to calibration.py.

        The application's single root is passed as `parent` so
        every calibration dialog is a Toplevel of self.root.

        Args:
            stereo_camera (StereoCamera):
                Configured stereo camera instance.

        Returns:
            bool:
                True if calibration succeeds.
        """
        print(
            "\n[MAIN] Starting "
            "calibration.run_calibration()"
        )

        result = calibration.run_calibration(
            stereo_camera,
            parent=self.root,
        )

        print(
            f"[MAIN] Calibration result: "
            f"{result}"
        )

        return result

    # ========================================================
    # SETUP WORKFLOW
    # ========================================================
    def start_setup(self):
        """
        Execute the complete camera and calibration setup
        workflow.
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
                parent=self.root,
            )

            selected_config = (
                self.run_camera_setup()
            )

            if selected_config is None:
                messagebox.showwarning(
                    "Setup Cancelled",
                    (
                        "Camera setup was cancelled "
                        "or failed.\n\n"
                        "Stereo calibration was not started."
                    ),
                    parent=self.root,
                )
                return

            # ------------------------------------------------
            # SAVE CAMERA CONFIGURATION
            # ------------------------------------------------
            if not save_camera_config(
                selected_config
            ):
                messagebox.showerror(
                    "Setup Error",
                    (
                        "The camera was selected successfully, "
                        "but its configuration could not be saved."
                    ),
                    parent=self.root,
                )
                return

            # ------------------------------------------------
            # CREATE STEREO CAMERA
            # ------------------------------------------------
            stereo_camera = StereoCamera(
                selected_config
            )

            print(
                "[MAIN] StereoCamera instance created."
            )

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
                parent=self.root,
            )

            calibration_success = (
                self.run_stereo_calibration(
                    stereo_camera
                )
            )

            if not calibration_success:
                messagebox.showwarning(
                    "Calibration Not Completed",
                    (
                        "Stereo calibration was not completed.\n\n"
                        "The camera configuration has been saved.\n"
                        "You can run setup again when ready."
                    ),
                    parent=self.root,
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
                parent=self.root,
            )

        except Exception as error:
            print(
                "\n[MAIN] SETUP ERROR"
            )

            print(
                repr(error)
            )

            messagebox.showerror(
                "Setup Error",
                (
                    "An unexpected error occurred "
                    "during setup:\n\n"
                    f"{error}"
                ),
                parent=self.root,
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
    # DEPTH / 3D LOCALIZATION
    # ========================================================
    def start_tracking(self):
        """
        Start the current static-object 3D localization stage.

        The current implementation does not perform temporal
        tracking yet.

        depth.py currently handles:
            - stereo camera acquisition
            - stereo rectification
            - crushed paper-ball detection
            - stereo correspondence
            - disparity calculation
            - depth estimation
            - 3D position calculation

        Future versions will add temporal tracking and
        trajectory processing.
        """
        if not setup_complete():
            messagebox.showwarning(
                "Setup Required",
                (
                    "Camera setup and stereo calibration "
                    "must be completed before starting "
                    "3D localization."
                ),
                parent=self.root,
            )

            self.update_status()

            if setup_complete():
                self.show_main_menu()
            else:
                self.show_first_run_menu()

            return

        camera_config = (
            load_camera_config()
        )

        if camera_config is None:
            messagebox.showerror(
                "Camera Configuration Error",
                (
                    "The saved camera configuration could "
                    "not be loaded.\n\n"
                    "Run setup again before continuing."
                ),
                parent=self.root,
            )

            self.show_main_menu()
            return

        stereo_camera = None

        try:
            print(
                "\n[MAIN] Starting 3D localization."
            )

            print(
                "[MAIN] Loading saved camera configuration."
            )

            stereo_camera = StereoCamera(
                camera_config
            )

            print(
                "[MAIN] StereoCamera instance created."
            )

            print(
                "[MAIN] Launching depth.py."
            )

            depth_ui = run_depth(
                stereo_camera=stereo_camera,
                parent=self.root,
            )

            if depth_ui is None:
                print(
                    "[MAIN] Depth localization "
                    "did not start."
                )

        except Exception as error:
            print(
                "\n[MAIN] DEPTH ERROR"
            )

            print(
                repr(error)
            )

            messagebox.showerror(
                "3D Localization Error",
                (
                    "An unexpected error occurred "
                    "while starting 3D localization:\n\n"
                    f"{error}"
                ),
                parent=self.root,
            )

            # If depth.py failed before taking ownership
            # of the camera, make sure it is not left open.
            if stereo_camera is not None:
                try:
                    stereo_camera.release()
                except Exception:
                    pass

        finally:
            self.update_status()

            if setup_complete():
                self.show_main_menu()
            else:
                self.show_first_run_menu()

    # ========================================================
    # EXIT
    # ========================================================
    def exit_application(self):
        """
        Close the application.
        """
        self.root.destroy()

    # ========================================================
    # APPLICATION LOOP
    # ========================================================
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