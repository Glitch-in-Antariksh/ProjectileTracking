import cv2
import json
from pathlib import Path


class StereoCamera:
    """
    Reusable interface for the selected stereo camera.

    The camera configuration is provided by camera_test.py and
    can be saved to / loaded from the project's calibration data.
    """

    DEFAULT_CONFIG_PATH = Path(
        "data/calibration/camera_config.json"
    )

    def __init__(self, config):
        """
        Initialize the stereo camera using the configuration
        selected during camera testing.

        Args:
            config (dict): Camera configuration dictionary.

        Raises:
            ValueError: If required configuration fields are missing.
        """
        required_keys = (
            "index",
            "width",
            "height"
        )

        missing_keys = [
            key
            for key in required_keys
            if key not in config
        ]

        if missing_keys:
            raise ValueError(
                "Invalid camera configuration. "
                f"Missing: {', '.join(missing_keys)}"
            )

        self.config = config
        self.camera_index = config["index"]
        self.width = config["width"]
        self.height = config["height"]

        self.camera = None
        self.actual_width = None
        self.actual_height = None

    # CONFIGURATION STORAGE

    def save_config(self, path=None):
        """
        Save the current camera configuration to disk.

        Args:
            path (str | Path, optional):
                Destination JSON file.
                Uses DEFAULT_CONFIG_PATH if omitted.

        Returns:
            bool: True if saved successfully, otherwise False.
        """
        config_path = Path(
            path or self.DEFAULT_CONFIG_PATH
        )

        try:
            config_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            with config_path.open(
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    self.config,
                    file,
                    indent=4
                )

            print(
                f"Camera configuration saved to: "
                f"{config_path}"
            )

            return True

        except (OSError, TypeError) as error:
            print(
                f"Unable to save camera configuration: "
                f"{error}"
            )
            return False

    @classmethod
    def load_config(cls, path=None):
        """
        Load a previously saved camera configuration.

        Args:
            path (str | Path, optional):
                Source JSON file.
                Uses DEFAULT_CONFIG_PATH if omitted.

        Returns:
            dict or None:
                Camera configuration dictionary if valid,
                otherwise None.
        """
        config_path = Path(
            path or cls.DEFAULT_CONFIG_PATH
        )

        if not config_path.exists():
            print(
                "No saved camera configuration found."
            )
            return None

        try:
            with config_path.open(
                "r",
                encoding="utf-8"
            ) as file:
                config = json.load(file)

            required_keys = (
                "index",
                "width",
                "height"
            )

            missing_keys = [
                key
                for key in required_keys
                if key not in config
            ]

            if missing_keys:
                print(
                    "Saved camera configuration is invalid. "
                    f"Missing: {', '.join(missing_keys)}"
                )
                return None

            return config

        except (
            OSError,
            json.JSONDecodeError
        ) as error:
            print(
                f"Unable to load camera configuration: "
                f"{error}"
            )
            return None

    # CAMERA INITIALIZATION

    def open(self):
        """
        Open the selected camera and request the tested
        resolution.

        Returns:
            bool: True if the camera opens successfully,
            otherwise False.
        """
        if self.camera is not None:
            return True

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        if not self.camera.isOpened():
            print(
                f"Unable to open camera "
                f"{self.camera_index}."
            )
            self.camera.release()
            self.camera = None
            return False

        # Request the resolution identified during testing.
        self.camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.width
        )
        self.camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.height
        )

        # Check the resolution actually provided
        # by the camera/driver.
        self.actual_width = int(
            self.camera.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )
        self.actual_height = int(
            self.camera.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        print(
            f"Camera {self.camera_index} opened."
        )
        print(
            f"Requested resolution: "
            f"{self.width} x {self.height}"
        )
        print(
            f"Actual resolution: "
            f"{self.actual_width} x "
            f"{self.actual_height}"
        )

        return True

    # FRAME ACQUISITION

    def read(self):
        """
        Capture one stereo frame and split it into
        left and right images.

        The current ELP configuration provides the stereo
        views as a side-by-side frame.

        Returns:
            tuple:
                left_frame, right_frame

            Returns (None, None) if the frame cannot
            be captured or split.
        """
        if self.camera is None:
            print("Camera is not open.")
            return None, None

        success, frame = self.camera.read()

        if not success or frame is None:
            print("Failed to read frame from camera.")
            return None, None

        frame_height, frame_width = frame.shape[:2]

        if frame_width < 2 or frame_width % 2 != 0:
            print(
                "Invalid stereo frame width. "
                "Expected an even frame width."
            )
            return None, None

        midpoint = frame_width // 2

        left_frame = frame[:, :midpoint]
        right_frame = frame[:, midpoint:]
        return left_frame, right_frame

    # CAMERA INFORMATION

    def get_resolution(self):
        """
        Return the actual resolution provided by the camera.

        Returns:
            tuple: (width, height)
        """
        return (
            self.actual_width,
            self.actual_height
        )

    def get_config(self):
        """
        Return the stored camera configuration.

        Returns:
            dict: Camera configuration dictionary.
        """
        return self.config.copy()

    # CAMERA RELEASE

    def release(self):
        """
        Release the camera and clean up the capture object.
        """
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            print("Camera released.")