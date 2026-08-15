import cv2
class StereoCamera:
    """
    Reusable interface for the selected stereo camera.

    The camera configuration is provided by camera_test.py.
    """
    def __init__(self, config):
        """
        Initialize the stereo camera using the configuration
        selected during camera testing.

        Args:
            config (dict): Camera configuration dictionary.
        """
        self.config = config
        self.camera_index = config["index"]
        self.width = config["width"]
        self.height = config["height"]
        self.camera = None
        self.actual_width = None
        self.actual_height = None

    # CAMERA INITIALIZATION
    def open(self):
        """
        Open the selected camera and request the tested
        resolution.

        Returns:
            bool: True if the camera opens successfully,
                  otherwise False.
        """
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
                left_frame
                right_frame

            Returns (None, None) if the frame cannot
            be captured.
        """
        if self.camera is None:
            print(
                "Camera is not open."
            )
            return None, None

        success, frame = self.camera.read()
        if not success or frame is None:
            print(
                "Failed to read frame from camera.")
            return None, None

        frame_height, frame_width = frame.shape[:2]
        midpoint = frame_width // 2
        left_frame = frame[
            :,
            :midpoint
        ]
        right_frame = frame[
            :,
            midpoint:
        ]
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

    # CAMERA RELEASE
    def release(self):
        """
        Release the camera and clean up the capture object.
        """
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            print("Camera released.")