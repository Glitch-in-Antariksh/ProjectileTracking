import time
from pathlib import Path

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk


# ============================================================
# PROJECT PATHS
# ============================================================

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

CALIBRATION_DIR = PROJECT_ROOT / "data" / "calibration"

CALIBRATION_PATH = (
    CALIBRATION_DIR / "stereo_calibration.npz"
)


# ============================================================
# DETECTION SETTINGS
# ============================================================

# Number of rectified frames used to build the background
# model. A median over multiple frames is much more stable than
# a single reference image.
BACKGROUND_FRAME_COUNT = 9

# Euclidean distance threshold in BGR color space.
#
# Each pixel has three channels:
#     B, G, R
#
# A pixel is considered foreground when:
#
#     sqrt(dB^2 + dG^2 + dR^2)
#
# is greater than this value.
COLOR_DISTANCE_THRESHOLD = 45

# Minimum contour area accepted as a possible object.
MIN_CONTOUR_AREA = 500

# Maximum contour area accepted as a possible object.
MAX_CONTOUR_AREA = 250000

# Morphological kernel used to clean the foreground mask.
MORPHOLOGY_KERNEL_SIZE = 5

# Minimum disparity accepted for a valid stereo match.
MIN_DISPARITY_PX = 0.5

# Maximum vertical difference between corresponding points
# after stereo rectification.
MAX_VERTICAL_DIFFERENCE_PX = 35.0

# Maximum depth accepted as physically reasonable.
MAX_DEPTH_METERS = 20.0

# Display size of each camera view.
DISPLAY_SIZE = (560, 420)

# Tkinter update interval.
PREVIEW_INTERVAL_MS = 20


# ============================================================
# STEREO CALIBRATION
# ============================================================

class StereoCalibration:
    """
    Load the saved stereo calibration and provide stereo
    rectification maps.
    """

    REQUIRED_KEYS = (
        "left_camera_matrix",
        "left_distortion",
        "right_camera_matrix",
        "right_distortion",
        "R1",
        "R2",
        "P1",
        "P2",
        "Q",
        "image_width",
        "image_height",
    )

    def __init__(
        self,
        path=CALIBRATION_PATH,
    ):
        self.path = Path(path)

        if not self.path.is_file():
            raise FileNotFoundError(
                "Stereo calibration file was not found:\n"
                f"{self.path}"
            )

        data = np.load(
            self.path,
            allow_pickle=False,
        )

        missing = [
            key
            for key in self.REQUIRED_KEYS
            if key not in data
        ]

        if missing:
            data.close()

            raise ValueError(
                "Stereo calibration file is incomplete.\n"
                f"Missing: {', '.join(missing)}"
            )

        self.left_camera_matrix = data[
            "left_camera_matrix"
        ]

        self.left_distortion = data[
            "left_distortion"
        ]

        self.right_camera_matrix = data[
            "right_camera_matrix"
        ]

        self.right_distortion = data[
            "right_distortion"
        ]

        self.R1 = data["R1"]
        self.R2 = data["R2"]

        self.P1 = data["P1"]
        self.P2 = data["P2"]

        self.Q = data["Q"]

        self.image_width = int(
            data["image_width"]
        )

        self.image_height = int(
            data["image_height"]
        )

        self.baseline_mm = None

        if "baseline_mm" in data:
            self.baseline_mm = float(
                data["baseline_mm"]
            )

        data.close()

        self.left_map_x = None
        self.left_map_y = None
        self.right_map_x = None
        self.right_map_y = None

        self._build_rectification_maps()

    def _build_rectification_maps(self):
        """
        Build the rectification maps for both cameras.
        """
        image_size = (
            self.image_width,
            self.image_height,
        )

        (
            self.left_map_x,
            self.left_map_y,
        ) = cv2.initUndistortRectifyMap(
            self.left_camera_matrix,
            self.left_distortion,
            self.R1,
            self.P1,
            image_size,
            cv2.CV_32FC1,
        )

        (
            self.right_map_x,
            self.right_map_y,
        ) = cv2.initUndistortRectifyMap(
            self.right_camera_matrix,
            self.right_distortion,
            self.R2,
            self.P2,
            image_size,
            cv2.CV_32FC1,
        )

    def rectify(
        self,
        left_frame,
        right_frame,
    ):
        """
        Rectify one stereo frame pair.
        """
        if (
            left_frame is None
            or right_frame is None
        ):
            return None, None

        left_height, left_width = (
            left_frame.shape[:2]
        )

        right_height, right_width = (
            right_frame.shape[:2]
        )

        expected_size = (
            self.image_width,
            self.image_height,
        )

        if (
            left_width,
            left_height,
        ) != expected_size or (
            right_width,
            right_height,
        ) != expected_size:

            raise ValueError(
                "Camera frame size does not match "
                "the saved stereo calibration.\n\n"
                f"Calibration: "
                f"{self.image_width} x "
                f"{self.image_height}\n"
                f"Left frame: "
                f"{left_width} x "
                f"{left_height}\n"
                f"Right frame: "
                f"{right_width} x "
                f"{right_height}"
            )

        rectified_left = cv2.remap(
            left_frame,
            self.left_map_x,
            self.left_map_y,
            cv2.INTER_LINEAR,
        )

        rectified_right = cv2.remap(
            right_frame,
            self.right_map_x,
            self.right_map_y,
            cv2.INTER_LINEAR,
        )

        return (
            rectified_left,
            rectified_right,
        )


# ============================================================
# STATIC OBJECT DETECTOR
# ============================================================


class PaperBallDetector:
    """
    Color-aware classical detector for the current static
    crushed-paper-ball experiment.

    No grayscale conversion is used here.

    The detector stores a stable color background model from
    several rectified stereo frames. Each incoming pixel is
    compared against its corresponding background pixel in the
    full BGR color space. Pixels whose color differs enough are
    treated as foreground.

    This is deliberately a controlled-environment detector.
    It is intended to validate stereo localization before a
    learned detector such as YOLO is introduced.
    """

    def __init__(
        self,
        background_frames=9,
    ):
        self.background_frames_required = (
            max(1, int(background_frames))
        )

        self.left_background = None
        self.right_background = None

        self.left_samples = []
        self.right_samples = []

        self.capturing_background = False

    @property
    def background_ready(self):
        """
        Return True when the color background model is ready.
        """
        return (
            self.left_background is not None
            and self.right_background is not None
        )

    @property
    def background_progress(self):
        """
        Return the number of background samples currently
        collected and the required number.
        """
        return (
            len(self.left_samples),
            self.background_frames_required,
        )

    def start_background_capture(self):
        """
        Begin collecting a multi-frame stereo background.

        The frames supplied afterward must contain no paper
        ball or other intentionally moving object.
        """
        self.left_background = None
        self.right_background = None

        self.left_samples.clear()
        self.right_samples.clear()

        self.capturing_background = True

    def add_background_frame(
        self,
        left_frame,
        right_frame,
    ):
        """
        Add one rectified stereo frame to the background model.

        Once enough frames have been collected, a per-pixel
        median color is calculated. The median is more stable
        than using a single frame because small camera noise
        and transient changes are suppressed.
        """
        if not self.capturing_background:
            return False

        if (
            left_frame is None
            or right_frame is None
        ):
            return False

        if left_frame.shape != right_frame.shape:
            return False

        self.left_samples.append(
            left_frame.copy()
        )

        self.right_samples.append(
            right_frame.copy()
        )

        if (
            len(self.left_samples)
            < self.background_frames_required
        ):
            return False

        left_stack = np.stack(
            self.left_samples,
            axis=0,
        )

        right_stack = np.stack(
            self.right_samples,
            axis=0,
        )

        # Nine frames gives us an odd sample count, so the
        # middle value is a true median. NumPy partitions the
        # uint8 stack in place, avoiding a large float64 median
        # allocation.
        middle = (
            self.background_frames_required // 2
        )

        left_stack.partition(
            middle,
            axis=0,
        )

        right_stack.partition(
            middle,
            axis=0,
        )

        self.left_background = (
            left_stack[middle].copy()
        )

        self.right_background = (
            right_stack[middle].copy()
        )

        self.left_samples.clear()
        self.right_samples.clear()

        self.capturing_background = False

        return True

    def capture_background(
        self,
        left_frame,
        right_frame,
    ):
        """
        Convenience method for a one-frame background capture.

        Kept for compatibility with the earlier interface.
        The live UI uses multi-frame capture through
        start_background_capture() and add_background_frame().
        """
        if (
            left_frame is None
            or right_frame is None
        ):
            return False

        self.left_background = (
            left_frame.copy()
        )

        self.right_background = (
            right_frame.copy()
        )

        self.left_samples.clear()
        self.right_samples.clear()

        self.capturing_background = False

        return True

    def clear_background(self):
        """
        Remove the background model and any partial capture.
        """
        self.left_background = None
        self.right_background = None

        self.left_samples.clear()
        self.right_samples.clear()

        self.capturing_background = False

    def _create_foreground_mask(
        self,
        frame,
        background,
    ):
        """
        Compare the current frame and background directly in
        BGR color space.

        For every pixel:

            B = current B - background B
            G = current G - background G
            R = current R - background R

        The Euclidean color distance is then:

            sqrt(dB^2 + dG^2 + dR^2)

        A pixel is foreground when that color distance exceeds
        COLOR_DISTANCE_THRESHOLD.
        """
        if background is None:
            return None

        current = frame.astype(
            np.float32
        )

        reference = background.astype(
            np.float32
        )

        # Compensate for global illumination drift.
        #
        # Webcams continuously and automatically adjust exposure
        # and white balance. This shifts every pixel's color
        # slightly, even when nothing in the scene has moved,
        # which otherwise shows up as flickering false-positive
        # blobs scattered across the whole frame rather than a
        # single stable blob on the actual object.
        #
        # The paper ball only occupies a small fraction of the
        # frame, so the per-channel MEDIAN difference between the
        # current frame and the background is a good estimate of
        # this global shift (a mean would be pulled around by the
        # ball itself once it's large). Subtracting it removes the
        # illumination drift while leaving the ball's real,
        # localized color change intact.
        channel_shift = np.median(
            (current - reference).reshape(-1, 3),
            axis=0,
        )

        current = current - channel_shift

        difference = (
            current - reference
        )

        distance_squared = np.sum(
            difference * difference,
            axis=2,
            dtype=np.int32,
        )

        threshold_squared = (
            COLOR_DISTANCE_THRESHOLD
            * COLOR_DISTANCE_THRESHOLD
        )

        mask = np.where(
            distance_squared
            >= threshold_squared,
            255,
            0,
        ).astype(np.uint8)

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (
                MORPHOLOGY_KERNEL_SIZE,
                MORPHOLOGY_KERNEL_SIZE,
            ),
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel,
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel,
        )

        # Fill the accepted foreground contours so that small
        # holes inside the paper ball do not split it apart.
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        cleaned = np.zeros_like(mask)

        for contour in contours:
            area = cv2.contourArea(
                contour
            )

            if area >= MIN_CONTOUR_AREA:
                cv2.drawContours(
                    cleaned,
                    [contour],
                    -1,
                    255,
                    thickness=cv2.FILLED,
                )

        return cleaned

    def _find_candidates(
        self,
        mask,
    ):
        """
        Find plausible foreground blobs.

        Candidate information includes geometry that can later
        be used for stereo matching.
        """
        if mask is None:
            return []

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        candidates = []

        for contour in contours:
            area = cv2.contourArea(
                contour
            )

            if area < MIN_CONTOUR_AREA:
                continue

            if area > MAX_CONTOUR_AREA:
                continue

            perimeter = cv2.arcLength(
                contour,
                True,
            )

            if perimeter <= 0:
                continue

            x, y, width, height = (
                cv2.boundingRect(contour)
            )

            if width <= 0 or height <= 0:
                continue

            moments = cv2.moments(
                contour
            )

            if moments["m00"] == 0:
                continue

            center_x = (
                moments["m10"]
                / moments["m00"]
            )

            center_y = (
                moments["m01"]
                / moments["m00"]
            )

            contour_area = max(
                area,
                1.0,
            )

            bounding_area = (
                width * height
            )

            fill_ratio = (
                contour_area
                / bounding_area
            )

            circularity = (
                4.0
                * np.pi
                * contour_area
                / (perimeter * perimeter)
            )

            candidates.append(
                {
                    "bbox": (
                        x,
                        y,
                        x + width,
                        y + height,
                    ),
                    "center": (
                        float(center_x),
                        float(center_y),
                    ),
                    "area": float(area),
                    "width": width,
                    "height": height,
                    "fill_ratio": float(
                        fill_ratio
                    ),
                    "circularity": float(
                        circularity
                    ),
                }
            )

        candidates.sort(
            key=lambda candidate:
            candidate["area"],
            reverse=True,
        )

        return candidates

    def _match_candidate_pair(
        self,
        left_candidates,
        right_candidates,
    ):
        """
        Find the most plausible left/right observation pair.

        Because the images are rectified, the same physical
        object should have similar vertical coordinates.

        The best pair is selected using:
            - vertical alignment
            - positive disparity
            - similar apparent area
            - similar bounding-box size
        """
        if (
            not left_candidates
            or not right_candidates
        ):
            return None, None

        best_pair = None
        best_score = float("inf")

        for left in left_candidates:
            left_x, left_y = (
                left["center"]
            )

            for right in right_candidates:
                right_x, right_y = (
                    right["center"]
                )

                vertical_difference = abs(
                    left_y - right_y
                )

                if (
                    vertical_difference
                    > MAX_VERTICAL_DIFFERENCE_PX
                ):
                    continue

                disparity = (
                    left_x - right_x
                )

                if disparity <= MIN_DISPARITY_PX:
                    continue

                area_ratio = (
                    min(
                        left["area"],
                        right["area"],
                    )
                    / max(
                        left["area"],
                        right["area"],
                    )
                )

                width_ratio = (
                    min(
                        left["width"],
                        right["width"],
                    )
                    / max(
                        left["width"],
                        right["width"],
                    )
                )

                height_ratio = (
                    min(
                        left["height"],
                        right["height"],
                    )
                    / max(
                        left["height"],
                        right["height"],
                    )
                )

                # Lower is better.
                score = (
                    vertical_difference
                    + 15.0
                    * (1.0 - area_ratio)
                    + 10.0
                    * (1.0 - width_ratio)
                    + 10.0
                    * (1.0 - height_ratio)
                )

                if score < best_score:
                    best_score = score
                    best_pair = (
                        left,
                        right,
                    )

        if best_pair is None:
            return None, None

        return best_pair

    def detect_stereo(
        self,
        left_frame,
        right_frame,
    ):
        """
        Detect and match the object across the rectified stereo
        pair.
        """
        left_mask = self._create_foreground_mask(
            left_frame,
            self.left_background,
        )

        right_mask = self._create_foreground_mask(
            right_frame,
            self.right_background,
        )

        left_candidates = (
            self._find_candidates(
                left_mask
            )
        )

        right_candidates = (
            self._find_candidates(
                right_mask
            )
        )

        (
            left_detection,
            right_detection,
        ) = self._match_candidate_pair(
            left_candidates,
            right_candidates,
        )

        return (
            left_detection,
            right_detection,
            left_mask,
            right_mask,
        )


# ============================================================
# STEREO CORRESPONDENCE
# ============================================================

def match_stereo_detections(
    left_detection,
    right_detection,
):
    """
    Determine whether the left and right detections are
    plausible observations of the same object.

    Rectification means corresponding points should lie close
    to the same horizontal epipolar line.
    """
    if (
        left_detection is None
        or right_detection is None
    ):
        return None

    left_x, left_y = (
        left_detection["center"]
    )

    right_x, right_y = (
        right_detection["center"]
    )

    vertical_difference = abs(
        left_y - right_y
    )

    if (
        vertical_difference
        > MAX_VERTICAL_DIFFERENCE_PX
    ):
        return None

    disparity = (
        left_x - right_x
    )

    if disparity <= MIN_DISPARITY_PX:
        return None

    return {
        "left_x": float(left_x),
        "left_y": float(left_y),
        "right_x": float(right_x),
        "right_y": float(right_y),
        "disparity": float(disparity),
        "vertical_difference": float(
            vertical_difference
        ),
    }


# ============================================================
# 3D LOCALIZATION
# ============================================================

def calculate_3d_position(
    correspondence,
    calibration,
):
    """
    Calculate the 3D position using the calibrated Q matrix.

    Calibration was performed using millimetres, so the raw
    result is in millimetres and is additionally provided in
    metres.
    """
    if correspondence is None:
        return None

    disparity = (
        correspondence["disparity"]
    )

    if disparity <= MIN_DISPARITY_PX:
        return None

    point = np.array(
        [
            [
                [
                    correspondence["left_x"],
                    correspondence["left_y"],
                    disparity,
                ]
            ]
        ],
        dtype=np.float32,
    )

    position = cv2.perspectiveTransform(
        point,
        calibration.Q,
    )

    x_mm = float(
        position[0, 0, 0]
    )

    y_mm = float(
        position[0, 0, 1]
    )

    z_mm = float(
        position[0, 0, 2]
    )

    if not all(
        np.isfinite(value)
        for value in (
            x_mm,
            y_mm,
            z_mm,
        )
    ):
        return None

    x_m = x_mm / 1000.0
    y_m = y_mm / 1000.0
    z_m = z_mm / 1000.0

    if z_m <= 0:
        return None

    if z_m > MAX_DEPTH_METERS:
        return None

    return {
        "x_mm": x_mm,
        "y_mm": y_mm,
        "z_mm": z_mm,
        "x_m": x_m,
        "y_m": y_m,
        "z_m": z_m,
    }


# ============================================================
# DISPLAY HELPERS
# ============================================================

def draw_detection(
    frame,
    detection,
    label,
):
    """
    Draw the detected object and its center.
    """
    if detection is None:
        cv2.putText(
            frame,
            f"{label}: NOT DETECTED",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

        return

    x1, y1, x2, y2 = (
        detection["bbox"]
    )

    center_x, center_y = (
        detection["center"]
    )

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2,
    )

    cv2.circle(
        frame,
        (
            int(center_x),
            int(center_y),
        ),
        6,
        (0, 255, 255),
        -1,
    )

    cv2.putText(
        frame,
        f"{label}: OBJECT",
        (x1, max(y1 - 10, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        (
            f"Center: "
            f"({center_x:.0f}, "
            f"{center_y:.0f})"
        ),
        (
            x1,
            min(
                y2 + 22,
                frame.shape[0] - 10,
            ),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )


def draw_status(
    frame,
    text,
    good=False,
):
    """
    Draw processing status on the camera frame.
    """
    color = (
        (0, 255, 0)
        if good
        else (0, 0, 255)
    )

    cv2.putText(
        frame,
        text,
        (
            15,
            frame.shape[0] - 18,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def frame_to_photo(frame):
    """
    Convert an OpenCV frame to a Tkinter-compatible image.
    """
    display = cv2.resize(
        frame,
        DISPLAY_SIZE,
        interpolation=cv2.INTER_AREA,
    )

    rgb = cv2.cvtColor(
        display,
        cv2.COLOR_BGR2RGB,
    )

    image = Image.fromarray(
        rgb
    )

    return ImageTk.PhotoImage(
        image=image
    )


# ============================================================
# DEPTH UI
# ============================================================

class DepthLocalizationUI:
    """
    Live stereo depth and 3D localization interface.

    The window is a Toplevel owned by main.py.
    """

    def __init__(
        self,
        parent,
        stereo_camera,
        calibration,
        detector,
    ):
        self.parent = parent
        self.stereo_camera = stereo_camera
        self.calibration = calibration
        self.detector = detector

        self.window = tk.Toplevel(
            parent
        )

        self.window.title(
            "Projectile Tracking - 3D Localization"
        )

        self.window.geometry(
            "1180x900"
        )

        self.window.resizable(
            False,
            False,
        )

        self.window.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

        self.running = False
        self.update_job = None

        self.left_photo = None
        self.right_photo = None

        self.latest_left_frame = None
        self.latest_right_frame = None

        self.latest_rectified_left = None
        self.latest_rectified_right = None

        self.last_fps_time = (
            time.perf_counter()
        )

        self.frame_counter = 0
        self.fps = 0.0

        self._build_ui()

        self.window.transient(
            parent
        )

        self.window.grab_set()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def _build_ui(self):
        tk.Label(
            self.window,
            text="3D Object Localization",
            font=("Arial", 18, "bold"),
        ).pack(
            pady=(15, 4)
        )

        tk.Label(
            self.window,
            text=(
                "Static crushed paper-ball detection "
                "and stereo depth estimation"
            ),
            font=("Arial", 10),
        ).pack(
            pady=(0, 8)
        )

        instruction_frame = tk.Frame(
            self.window
        )

        instruction_frame.pack(
            pady=(0, 8)
        )

        self.instruction_status = tk.Label(
            instruction_frame,
            text=(
                "Step 1: Remove the paper ball "
                "from the camera view, then capture "
                "the background."
            ),
            font=("Arial", 10, "bold"),
            wraplength=900,
            justify="center",
        )

        self.instruction_status.pack()

        self.capture_button = tk.Button(
            instruction_frame,
            text="Capture Background",
            command=self.capture_background,
            font=("Arial", 10, "bold"),
            padx=20,
            pady=7,
        )

        self.capture_button.pack(
            pady=(7, 2)
        )

        self.reset_button = tk.Button(
            instruction_frame,
            text="Reset Background",
            command=self.reset_background,
            font=("Arial", 9),
            padx=15,
            pady=4,
            state=tk.DISABLED,
        )

        self.reset_button.pack(
            pady=2
        )

        video_frame = tk.Frame(
            self.window
        )

        video_frame.pack(
            padx=15,
            pady=5,
        )

        left_column = tk.Frame(
            video_frame
        )

        left_column.pack(
            side="left",
            padx=8,
        )

        tk.Label(
            left_column,
            text="LEFT CAMERA",
            font=("Arial", 10, "bold"),
        ).pack()

        self.left_video_label = tk.Label(
            left_column
        )

        self.left_video_label.pack()

        right_column = tk.Frame(
            video_frame
        )

        right_column.pack(
            side="left",
            padx=8,
        )

        tk.Label(
            right_column,
            text="RIGHT CAMERA",
            font=("Arial", 10, "bold"),
        ).pack()

        self.right_video_label = tk.Label(
            right_column
        )

        self.right_video_label.pack()

        status_frame = tk.Frame(
            self.window
        )

        status_frame.pack(
            pady=8
        )

        self.detection_status = tk.Label(
            status_frame,
            text="Detection: waiting...",
            font=("Arial", 10, "bold"),
        )

        self.detection_status.pack(
            pady=2
        )

        self.disparity_status = tk.Label(
            status_frame,
            text="Disparity: --",
            font=("Arial", 10),
        )

        self.disparity_status.pack(
            pady=2
        )

        self.depth_status = tk.Label(
            status_frame,
            text="Depth: --",
            font=("Arial", 11, "bold"),
        )

        self.depth_status.pack(
            pady=2
        )

        self.position_status = tk.Label(
            status_frame,
            text="3D Position: --",
            font=("Arial", 10),
        )

        self.position_status.pack(
            pady=2
        )

        self.fps_status = tk.Label(
            status_frame,
            text="Processing FPS: --",
            font=("Arial", 9),
        )

        self.fps_status.pack(
            pady=2
        )

        tk.Button(
            self.window,
            text="Stop",
            command=self.close,
            font=("Arial", 11, "bold"),
            padx=30,
            pady=8,
        ).pack(
            pady=8
        )

    # --------------------------------------------------------
    # BACKGROUND CONTROL
    # --------------------------------------------------------

    def capture_background(self):
        """
        Start collecting a multi-frame color background model.

        The camera is already running. The next
        BACKGROUND_FRAME_COUNT rectified stereo frames are
        collected by the live update loop.
        """
        if (
            self.latest_rectified_left is None
            or self.latest_rectified_right is None
        ):
            self.instruction_status.config(
                text=(
                    "Unable to capture background. "
                    "Waiting for camera frames..."
                )
            )

            return

        self.detector.start_background_capture()

        self.capture_button.config(
            state=tk.DISABLED
        )

        self.reset_button.config(
            state=tk.NORMAL
        )

        self.instruction_status.config(
            text=(
                "Capturing color background... "
                "Keep the scene still and keep the "
                "paper ball out of view."
            )
        )

        self.detection_status.config(
            text=(
                "Detection: building background model..."
            )
        )

    def reset_background(self):
        """
        Clear the stored background and return to setup mode.
        """
        self.detector.clear_background()

        self.capture_button.config(
            state=tk.NORMAL
        )

        self.reset_button.config(
            state=tk.DISABLED
        )

        self.detection_status.config(
            text="Detection: waiting..."
        )

        self.disparity_status.config(
            text="Disparity: --"
        )

        self.depth_status.config(
            text="Depth: --"
        )

        self.position_status.config(
            text="3D Position: --"
        )

        self.instruction_status.config(
            text=(
                "Step 1: Remove the paper ball "
                "from the camera view, then capture "
                "the background."
            )
        )

    # --------------------------------------------------------
    # PROCESSING
    # --------------------------------------------------------

    def update(self):
        """
        Acquire a stereo frame pair, rectify it, maintain the
        background model, detect the foreground object and
        calculate its 3D position.
        """
        if not self.running:
            return

        (
            left_frame,
            right_frame,
        ) = self.stereo_camera.read()

        if (
            left_frame is None
            or right_frame is None
        ):
            self.detection_status.config(
                text=(
                    "Detection: camera frame unavailable"
                )
            )

            self.schedule_next_update()
            return

        self.latest_left_frame = (
            left_frame.copy()
        )

        self.latest_right_frame = (
            right_frame.copy()
        )

        try:
            (
                rectified_left,
                rectified_right,
            ) = self.calibration.rectify(
                left_frame,
                right_frame,
            )

        except ValueError as error:
            self.detection_status.config(
                text="Calibration/frame mismatch"
            )

            self.position_status.config(
                text=str(error)
            )

            self.schedule_next_update()
            return

        # The background and live frame must use exactly the same
        # rectified coordinate system before pixel comparison.
        self.latest_rectified_left = (
            rectified_left.copy()
        )

        self.latest_rectified_right = (
            rectified_right.copy()
        )

        # ----------------------------------------------------
        # BACKGROUND MODEL
        # ----------------------------------------------------

        if self.detector.capturing_background:
            completed = (
                self.detector.add_background_frame(
                    rectified_left,
                    rectified_right,
                )
            )

            collected, required = (
                self.detector.background_progress
            )

            if completed:
                self.capture_button.config(
                    state=tk.DISABLED
                )

                self.reset_button.config(
                    state=tk.NORMAL
                )

                self.instruction_status.config(
                    text=(
                        "Background captured. "
                        "Now place the crushed paper ball "
                        "in the scene."
                    )
                )

                self.detection_status.config(
                    text=(
                        "Detection: background ready"
                    )
                )

            else:
                self.instruction_status.config(
                    text=(
                        "Capturing color background... "
                        f"{collected}/{required} frames. "
                        "Keep the scene still."
                    )
                )

                self.detection_status.config(
                    text=(
                        "Detection: background model "
                        f"{collected}/{required}"
                    )
                )

        # ----------------------------------------------------
        # DETECTION
        # ----------------------------------------------------

        if self.detector.background_ready:
            (
                left_detection,
                right_detection,
                left_mask,
                right_mask,
            ) = self.detector.detect_stereo(
                rectified_left,
                rectified_right,
            )

            correspondence = (
                match_stereo_detections(
                    left_detection,
                    right_detection,
                )
            )

            position = (
                calculate_3d_position(
                    correspondence,
                    self.calibration,
                )
            )

        else:
            left_detection = None
            right_detection = None
            correspondence = None
            position = None

        # ----------------------------------------------------
        # DRAW RESULTS
        # ----------------------------------------------------

        left_display = (
            rectified_left.copy()
        )

        right_display = (
            rectified_right.copy()
        )

        if self.detector.background_ready:
            draw_detection(
                left_display,
                left_detection,
                "LEFT",
            )

            draw_detection(
                right_display,
                right_detection,
                "RIGHT",
            )

        elif self.detector.capturing_background:
            collected, required = (
                self.detector.background_progress
            )

            draw_status(
                left_display,
                f"Building background {collected}/{required}",
                good=False,
            )

            draw_status(
                right_display,
                f"Building background {collected}/{required}",
                good=False,
            )

        else:
            draw_status(
                left_display,
                "Background not captured",
                good=False,
            )

            draw_status(
                right_display,
                "Background not captured",
                good=False,
            )

        # ----------------------------------------------------
        # DETECTION STATUS
        # ----------------------------------------------------

        if self.detector.capturing_background:
            self.disparity_status.config(
                text="Disparity: --"
            )

            self.depth_status.config(
                text="Depth: --"
            )

            self.position_status.config(
                text="3D Position: --"
            )

        elif not self.detector.background_ready:
            self.detection_status.config(
                text=(
                    "Detection: waiting for "
                    "background capture"
                )
            )

            self.disparity_status.config(
                text="Disparity: --"
            )

            self.depth_status.config(
                text="Depth: --"
            )

            self.position_status.config(
                text="3D Position: --"
            )

        elif (
            left_detection is not None
            and right_detection is not None
        ):
            self.detection_status.config(
                text=(
                    "Detection: "
                    "LEFT DETECTED  |  "
                    "RIGHT DETECTED"
                )
            )

        elif left_detection is not None:
            self.detection_status.config(
                text=(
                    "Detection: "
                    "LEFT DETECTED  |  "
                    "RIGHT NOT DETECTED"
                )
            )

        elif right_detection is not None:
            self.detection_status.config(
                text=(
                    "Detection: "
                    "LEFT NOT DETECTED  |  "
                    "RIGHT DETECTED"
                )
            )

        else:
            self.detection_status.config(
                text=(
                    "Detection: OBJECT NOT DETECTED"
                )
            )

        # ----------------------------------------------------
        # DEPTH STATUS
        # ----------------------------------------------------

        if (
            self.detector.background_ready
            and not self.detector.capturing_background
        ):
            if correspondence is None:

                if (
                    left_detection is not None
                    and right_detection is not None
                ):
                    self.disparity_status.config(
                        text=(
                            "Stereo match: INVALID"
                        )
                    )
                else:
                    self.disparity_status.config(
                        text="Disparity: --"
                    )

                self.depth_status.config(
                    text="Depth: --"
                )

                self.position_status.config(
                    text="3D Position: --"
                )

                draw_status(
                    left_display,
                    "Stereo correspondence unavailable",
                    good=False,
                )

                draw_status(
                    right_display,
                    "Stereo correspondence unavailable",
                    good=False,
                )

            elif position is None:

                self.disparity_status.config(
                    text=(
                        "Disparity: "
                        f"{correspondence['disparity']:.2f} px"
                    )
                )

                self.depth_status.config(
                    text="Depth: INVALID"
                )

                self.position_status.config(
                    text="3D Position: INVALID"
                )

                draw_status(
                    left_display,
                    "Invalid depth",
                    good=False,
                )

                draw_status(
                    right_display,
                    "Invalid depth",
                    good=False,
                )

            else:
                disparity = (
                    correspondence["disparity"]
                )

                depth_m = (
                    position["z_m"]
                )

                x_m = (
                    position["x_m"]
                )

                y_m = (
                    position["y_m"]
                )

                self.disparity_status.config(
                    text=(
                        f"Disparity: "
                        f"{disparity:.2f} px"
                    )
                )

                self.depth_status.config(
                    text=(
                        f"Depth: "
                        f"{depth_m:.3f} m"
                    )
                )

                self.position_status.config(
                    text=(
                        f"3D Position: "
                        f"X = {x_m:.3f} m    "
                        f"Y = {y_m:.3f} m    "
                        f"Z = {depth_m:.3f} m"
                    )
                )

                draw_status(
                    left_display,
                    f"Depth: {depth_m:.3f} m",
                    good=True,
                )

                draw_status(
                    right_display,
                    f"Depth: {depth_m:.3f} m",
                    good=True,
                )

        # ----------------------------------------------------
        # FPS
        # ----------------------------------------------------

        self.frame_counter += 1

        current_time = (
            time.perf_counter()
        )

        elapsed = (
            current_time
            - self.last_fps_time
        )

        if elapsed >= 1.0:
            self.fps = (
                self.frame_counter
                / elapsed
            )

            self.frame_counter = 0
            self.last_fps_time = (
                current_time
            )

            self.fps_status.config(
                text=(
                    f"Processing FPS: "
                    f"{self.fps:.1f}"
                )
            )

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        self.left_photo = (
            frame_to_photo(
                left_display
            )
        )

        self.right_photo = (
            frame_to_photo(
                right_display
            )
        )

        self.left_video_label.config(
            image=self.left_photo
        )

        self.right_video_label.config(
            image=self.right_photo
        )

        self.schedule_next_update()

    def schedule_next_update(self):
        """
        Schedule the next frame update.
        """
        if self.running:
            self.update_job = (
                self.window.after(
                    PREVIEW_INTERVAL_MS,
                    self.update,
                )
            )

    # --------------------------------------------------------
    # START / STOP
    # --------------------------------------------------------

    def run(self):
        """
        Start the live localization loop.
        """
        self.running = True

        if not self.stereo_camera.open():
            self.running = False

            self.detection_status.config(
                text=(
                    "Detection: unable to open camera"
                )
            )

            return False

        self.update()

        return True

    def close(self):
        """
        Stop the localization loop, release the camera and
        close the window.
        """
        self.running = False

        if self.update_job is not None:
            try:
                self.window.after_cancel(
                    self.update_job
                )
            except tk.TclError:
                pass

            self.update_job = None

        self.stereo_camera.release()

        try:
            self.window.grab_release()
            self.window.destroy()
        except tk.TclError:
            pass


# ============================================================
# MAIN DEPTH WORKFLOW
# ============================================================

def run_depth(
    stereo_camera,
    parent,
):
    """
    Start the static crushed-paper-ball 3D localization stage.

    The function is called by main.py and uses main.py's
    existing Tk root.
    """
    if stereo_camera is None:
        raise ValueError(
            "run_depth() requires a StereoCamera instance."
        )

    if parent is None:
        raise ValueError(
            "run_depth() requires the main application Tk root."
        )

    try:
        calibration = StereoCalibration()

    except (
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:

        message = tk.Toplevel(
            parent
        )

        message.title(
            "Depth Initialization Error"
        )

        message.geometry(
            "560x250"
        )

        message.resizable(
            False,
            False,
        )

        tk.Label(
            message,
            text="Unable to start 3D localization",
            font=("Arial", 15, "bold"),
        ).pack(
            pady=(25, 10)
        )

        tk.Label(
            message,
            text=str(error),
            font=("Arial", 10),
            wraplength=500,
            justify="center",
        ).pack(
            pady=10
        )

        tk.Button(
            message,
            text="Close",
            command=message.destroy,
            font=("Arial", 10),
            padx=25,
            pady=6,
        ).pack(
            pady=15
        )

        message.transient(
            parent
        )

        message.grab_set()

        return None

    detector = PaperBallDetector(
        background_frames=BACKGROUND_FRAME_COUNT,
    )

    ui = DepthLocalizationUI(
        parent=parent,
        stereo_camera=stereo_camera,
        calibration=calibration,
        detector=detector,
    )

    ui.run()

    return ui


# ============================================================
# STANDALONE TESTING
# ============================================================

def main():
    """
    depth.py is normally launched through main.py.
    """
    print(
        "depth.py is designed to be launched through main.py."
    )


if __name__ == "__main__":
    main()