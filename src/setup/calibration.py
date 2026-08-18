import cv2
import json
import time
import numpy as np
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_DIR = PROJECT_ROOT / "data" / "calibration"
CAPTURE_DIR = PROJECT_ROOT / "data" / "captures"

CAMERA_CONFIG_PATH = CALIBRATION_DIR / "camera_config.json"
CALIBRATION_PATH = CALIBRATION_DIR / "stereo_calibration.npz"

# ============================================================
# DEFAULT CALIBRATION SETTINGS
# ============================================================
# The supplied project checkerboard contains 8 x 10 squares.
# Therefore it has 7 x 9 INTERNAL corners.
#
# The supplied checkerboard uses 20 x 20 mm squares.
DEFAULT_CORNERS_HORIZONTAL = 7
DEFAULT_CORNERS_VERTICAL = 9
DEFAULT_SQUARE_SIZE_MM = 20.0

# Number of accepted stereo image pairs targeted by the
# guided calibration workflow.
TARGET_CAPTURES = 12

# Maximum number of capture attempts allowed before the
# session is aborted (protects against an endless session).
# Raised from the original 30 because auto-capture (see below)
# will harmlessly re-attempt a few times whenever the board sits
# still after a successful capture, before the user moves it.
MAX_CAPTURE_ATTEMPTS = 45

# Number of consecutive stable detections required before a pose
# is captured. Kept relatively low because detection now runs at
# close to full camera frame rate (see DETECTION_DOWNSCALE below),
# so this corresponds to well under a second of "hold still" time
# rather than several seconds.
STABILITY_DURATION = 0.25

# Maximum mean corner movement in pixels for a stable board.
STABILITY_THRESHOLD = 4.0

# Reprojection-error guidance thresholds in pixels.
GOOD_ERROR = 1.0
ACCEPTABLE_ERROR = 1.5

# Live preview update interval, in milliseconds.
PREVIEW_INTERVAL_MS = 30

# Size (pixels) each half of the live preview is scaled to.
PREVIEW_DISPLAY_SIZE = (420, 315)

# Checkerboard detection scale. Search runs on a downscaled
# copy of the FULL frame (both cameras -- see _update_preview);
# corner search cost scales roughly with pixel count, so this is
# the main lever for detection speed. 0.5 balances speed against
# still being able to resolve the board at typical distances; if
# detection struggles for a far-away board, raise this toward
# 0.7-0.8 at the cost of some speed.
DETECTION_DOWNSCALE = 0.7

# Keep the fast SB detector for live preview. Accuracy mode adds
# extra processing and is unnecessary once the pattern is correct.
USE_SB_ACCURACY = False


# How long (seconds) the "CAPTURED" confirmation stays on screen
# after an automatic or manual capture.
CAPTURE_FLASH_SECONDS = 0.6

# ============================================================
# CALIBRATION POSES
# ============================================================
CALIBRATION_POSES = [
    {
        "name": "CENTER",
        "instruction": "Place the checkerboard inside the center box.",
        "center": (0.50, 0.50),
        "size": (0.52, 0.64),
    },
    {
        "name": "LEFT",
        "instruction": "Move the checkerboard into the LEFT box.",
        "center": (0.25, 0.50),
        "size": (0.46, 0.60),
    },
    {
        "name": "RIGHT",
        "instruction": "Move the checkerboard into the RIGHT box.",
        "center": (0.75, 0.50),
        "size": (0.46, 0.60),
    },
    {
        "name": "TOP",
        "instruction": "Move the checkerboard into the TOP box.",
        "center": (0.50, 0.25),
        "size": (0.46, 0.58),
    },
    {
        "name": "BOTTOM",
        "instruction": "Move the checkerboard into the BOTTOM box.",
        "center": (0.50, 0.75),
        "size": (0.46, 0.58),
    },
    {
        "name": "UPPER-LEFT",
        "instruction": "Move the checkerboard into the UPPER-LEFT box.",
        "center": (0.25, 0.25),
        "size": (0.44, 0.56),
    },
    {
        "name": "UPPER-RIGHT",
        "instruction": "Move the checkerboard into the UPPER-RIGHT box.",
        "center": (0.75, 0.25),
        "size": (0.44, 0.56),
    },
    {
        "name": "LOWER-LEFT",
        "instruction": "Move the checkerboard into the LOWER-LEFT box.",
        "center": (0.25, 0.75),
        "size": (0.44, 0.56),
    },
    {
        "name": "LOWER-RIGHT",
        "instruction": "Move the checkerboard into the LOWER-RIGHT box.",
        "center": (0.75, 0.75),
        "size": (0.44, 0.56),
    },
    {
        "name": "CLOSE",
        "instruction": "Move the checkerboard closer until it fits inside the box.",
        "center": (0.50, 0.50),
        "size": (0.68, 0.78),
    },
    {
        "name": "FAR",
        "instruction": "Move the checkerboard farther away until it fits inside the box.",
        "center": (0.50, 0.50),
        "size": (0.34, 0.44),
    },
    {
        "name": "PERSPECTIVE",
        "instruction": "Tilt the checkerboard for a different perspective.",
        "center": (0.50, 0.50),
        "size": (0.52, 0.64),
    },
]


# ============================================================
# CHECKERBOARD CONFIGURATION
# ============================================================
def request_checkerboard_config(parent):
    """
    Display a UI that allows the user to enter their own
    checkerboard dimensions and square size.

    Defaults correspond to the project's supplied checkerboard:
    7 x 9 squares -> 6 x 8 internal corners, 20 mm square size.

    Args:
        parent (tk.Tk | tk.Toplevel): Owning window.

    Returns:
        dict or None:
            Valid checkerboard configuration, or None if
            the user cancels the setup.
    """
    result = None

    window = tk.Toplevel(parent)
    window.title("Projectile Tracking - Checkerboard Setup")
    window.geometry("560x430")
    window.resizable(False, False)

    tk.Label(
        window,
        text="Checkerboard Configuration",
        font=("Arial", 18, "bold"),
    ).pack(pady=(20, 8))

    tk.Label(
        window,
        text=(
            "Enter the checkerboard's INTERNAL corner count.\n"
            "Do not enter the number of black/white squares.\n\n"
            "For the supplied 7 x 9 checkerboard:\n"
            "6 horizontal x 8 vertical internal corners,\n"
            "with 20 mm square size."
        ),
        font=("Arial", 10),
        justify="center",
    ).pack(pady=8)

    frame = tk.Frame(window)
    frame.pack(pady=15)

    tk.Label(frame, text="Horizontal internal corners:", font=("Arial", 10)).grid(
        row=0, column=0, padx=10, pady=8, sticky="e"
    )
    horizontal_entry = tk.Entry(frame, width=12, font=("Arial", 10))
    horizontal_entry.insert(0, str(DEFAULT_CORNERS_HORIZONTAL))
    horizontal_entry.grid(row=0, column=1, padx=10, pady=8)

    tk.Label(frame, text="Vertical internal corners:", font=("Arial", 10)).grid(
        row=1, column=0, padx=10, pady=8, sticky="e"
    )
    vertical_entry = tk.Entry(frame, width=12, font=("Arial", 10))
    vertical_entry.insert(0, str(DEFAULT_CORNERS_VERTICAL))
    vertical_entry.grid(row=1, column=1, padx=10, pady=8)

    tk.Label(frame, text="Square size (mm):", font=("Arial", 10)).grid(
        row=2, column=0, padx=10, pady=8, sticky="e"
    )
    square_entry = tk.Entry(frame, width=12, font=("Arial", 10))
    square_entry.insert(0, str(DEFAULT_SQUARE_SIZE_MM))
    square_entry.grid(row=2, column=1, padx=10, pady=8)

    def confirm():
        nonlocal result
        try:
            horizontal = int(horizontal_entry.get().strip())
            vertical = int(vertical_entry.get().strip())
            square_size = float(square_entry.get().strip())

            if horizontal < 3 or vertical < 3:
                raise ValueError("Each corner count must be at least 3.")
            if square_size <= 0:
                raise ValueError("Square size must be greater than zero.")

            result = {
                "corners_horizontal": horizontal,
                "corners_vertical": vertical,
                "square_size": square_size,
                "square_size_unit": "mm",
            }
            window.destroy()
        except ValueError as error:
            messagebox.showerror(
                "Invalid Checkerboard Configuration",
                str(error),
                parent=window,
            )

    def cancel():
        window.destroy()

    button_frame = tk.Frame(window)
    button_frame.pack(pady=15)

    tk.Button(
        button_frame,
        text="Continue",
        command=confirm,
        font=("Arial", 11, "bold"),
        padx=25,
        pady=8,
    ).pack(side="left", padx=10)

    tk.Button(
        button_frame,
        text="Cancel",
        command=cancel,
        font=("Arial", 11),
        padx=25,
        pady=8,
    ).pack(side="left", padx=10)

    window.protocol("WM_DELETE_WINDOW", cancel)

    # Single application event loop: this window only waits on
    # itself, it never starts a second mainloop().
    window.transient(parent)
    window.grab_set()
    window.wait_window()

    return result


# ============================================================
# CHECKERBOARD DETECTION
# ============================================================
def clamp_roi(x, y, width, height, frame_shape):
    """
    Clamp an ROI to valid frame coordinates.

    Returns:
        tuple: (x, y, width, height)
    """
    frame_height, frame_width = frame_shape[:2]

    x = max(0, min(int(x), frame_width - 1))
    y = max(0, min(int(y), frame_height - 1))
    width = max(1, min(int(width), frame_width - x))
    height = max(1, min(int(height), frame_height - y))

    return x, y, width, height


def normalized_target_to_roi(frame, target, scale=1.0):
    """
    Convert a normalized target box into a pixel ROI.

    The target is expressed as:
        center = (x, y)
        size   = (width, height)

    All values are normalized to [0, 1]. `scale` expands the box
    around its own center (e.g. 1.45 searches an area 45% larger
    than the visible guide box, giving the detector some slack).
    """
    frame_height, frame_width = frame.shape[:2]

    center_x, center_y = target["center"]
    target_width, target_height = target["size"]
    target_width *= scale
    target_height *= scale

    x = (center_x - target_width / 2.0) * frame_width
    y = (center_y - target_height / 2.0) * frame_height
    width = target_width * frame_width
    height = target_height * frame_height

    return clamp_roi(x, y, width, height, frame.shape)


def detect_checkerboard(frame, pattern_size, roi=None):
    """
    Detect checkerboard corners using OpenCV's sector-based
    checkerboard detector.

    If an ROI is supplied, detection is performed only inside
    that region. This dramatically reduces the search area and
    makes the detector more reliable because the user is guided
    to place the board in a known location.

    Returned corner coordinates are always expressed in the
    original full-frame coordinate system.

    Sub-pixel refinement is performed separately during capture.
    """
    if roi is None:
        roi = (0, 0, frame.shape[1], frame.shape[0])

    x, y, width, height = clamp_roi(*roi, frame.shape)
    roi_frame = frame[y:y + height, x:x + width]

    gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)

    if DETECTION_DOWNSCALE != 1.0:
        search_gray = cv2.resize(
            gray,
            None,
            fx=DETECTION_DOWNSCALE,
            fy=DETECTION_DOWNSCALE,
            interpolation=cv2.INTER_AREA,
        )
    else:
        search_gray = gray

    found, corners = cv2.findChessboardCornersSB(
        search_gray,
        pattern_size,
        flags=cv2.CALIB_CB_NORMALIZE_IMAGE,
    )

    if not found or corners is None:
        return None

    # OpenCV versions may return SB corners as either (N, 1, 2)
    # or (N, 2). Normalize the shape so the rest of the pipeline
    # always receives the standard OpenCV (N, 1, 2) format.
    corners = np.asarray(corners, dtype=np.float32).reshape(-1, 1, 2)

    if DETECTION_DOWNSCALE != 1.0:
        corners /= DETECTION_DOWNSCALE

    # Convert ROI-relative coordinates back to full-frame
    # coordinates.
    corners[:, 0, 0] += x
    corners[:, 0, 1] += y

    return corners


def refine_checkerboard_corners(frame, corners):
    """
    Refine already-detected checkerboard corners to sub-pixel
    accuracy using the full-resolution image.

    This expensive operation is only performed for a frame that
    is actually being captured for calibration.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.001,
    )

    corners = np.asarray(corners, dtype=np.float32).reshape(-1, 1, 2)

    refined_corners = cv2.cornerSubPix(
        gray,
        corners,
        (11, 11),
        (-1, -1),
        criteria,
    )

    return refined_corners.astype("float32")


# ============================================================
# OBJECT POINT GENERATION
# ============================================================
def create_object_points(corners_horizontal, corners_vertical, square_size_mm):
    """
    Create the known 3D checkerboard coordinates.

    The checkerboard is assumed to lie on the Z = 0 plane.
    """
    object_points = np.zeros(
        (corners_horizontal * corners_vertical, 3), dtype=np.float32
    )
    grid = np.mgrid[0:corners_horizontal, 0:corners_vertical].T.reshape(-1, 2)
    object_points[:, :2] = grid * square_size_mm
    return object_points


# ============================================================
# CAPTURE QUALITY
# ============================================================
def calculate_corner_motion(previous, current):
    """
    Calculate the mean corner displacement between two
    consecutive detections.
    """
    if previous is None or current is None:
        return float("inf")
    if previous.shape != current.shape:
        return float("inf")
    return float(cv2.norm(previous, current, cv2.NORM_L2) / previous.shape[0])


def calculate_image_sharpness(frame):
    """
    Estimate image sharpness using the variance of the
    Laplacian.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def calculate_board_geometry(corners, frame_shape):
    """
    Calculate normalized checkerboard geometry.

    Returns:
        dict containing center and bounding-box size as fractions
        of the full frame.
    """
    points = corners.reshape(-1, 2)
    min_x, min_y = points.min(axis=0)
    max_x, max_y = points.max(axis=0)

    frame_height, frame_width = frame_shape[:2]

    width = max_x - min_x
    height = max_y - min_y
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    return {
        "center": (
            float(center_x / frame_width),
            float(center_y / frame_height),
        ),
        "size": (
            float(width / frame_width),
            float(height / frame_height),
        ),
    }


def board_matches_target(corners, frame_shape, target):
    """
    Determine whether the detected checkerboard is positioned
    appropriately inside the guided target box.

    The target box is intentionally larger than the expected
    checkerboard so the user has some positioning tolerance.
    """
    geometry = calculate_board_geometry(corners, frame_shape)

    board_center_x, board_center_y = geometry["center"]
    board_width, board_height = geometry["size"]

    target_center_x, target_center_y = target["center"]
    target_width, target_height = target["size"]

    center_tolerance_x = target_width * 0.38
    center_tolerance_y = target_height * 0.38

    center_ok = (
        abs(board_center_x - target_center_x) <= center_tolerance_x
        and abs(board_center_y - target_center_y) <= center_tolerance_y
    )

    # The board must be large enough to be useful, but it must
    # also fit inside the target box with a little safety margin.
    min_width = target_width * 0.20
    min_height = target_height * 0.20
    max_width = target_width * 1.25
    max_height = target_height * 1.25

    size_ok = (
        min_width <= board_width <= max_width
        and min_height <= board_height <= max_height
    )

    return center_ok and size_ok


def board_in_frame(corners, frame_shape, margin=0.02):
    """
    Determine whether a detected checkerboard is fully inside
    the frame with a small safety margin, with NO requirement
    about *where* in the frame it sits.

    This is used for the RIGHT camera instead of
    board_matches_target(). Because of stereo disparity, the
    same physical checkerboard position can land anywhere in the
    right image relative to the left image -- there is no shared
    "correct" position to check against. All that actually
    matters for calibration is that the full board is visible
    and not clipped at an edge (which would make its corners
    inaccurate).
    """
    points = corners.reshape(-1, 2)
    frame_height, frame_width = frame_shape[:2]

    margin_x = margin * frame_width
    margin_y = margin * frame_height

    min_x, min_y = points.min(axis=0)
    max_x, max_y = points.max(axis=0)

    return (
        min_x >= margin_x
        and min_y >= margin_y
        and max_x <= frame_width - margin_x
        and max_y <= frame_height - margin_y
    )


def draw_target_box(frame, target, detected=False):
    """
    Draw the current calibration target box onto a frame.
    """
    x, y, width, height = normalized_target_to_roi(frame, target)

    color = (0, 200, 0) if detected else (255, 200, 0)

    cv2.rectangle(
        frame,
        (x, y),
        (x + width, y + height),
        color,
        2,
    )

    label = "READY" if detected else "TARGET"
    cv2.putText(
        frame,
        label,
        (x + 8, max(y - 8, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def draw_in_frame_indicator(frame, detected=False):
    """
    Draw a simple status label onto the right camera view, which
    (unlike the left camera) has no target box to guide against
    -- stereo disparity means there's no single "correct" position
    for the board to sit at in the right view (see board_in_frame).
    """
    color = (0, 200, 0) if detected else (255, 200, 0)
    label = "BOARD IN VIEW" if detected else "BOARD NOT FULLY IN VIEW"

    cv2.putText(
        frame,
        label,
        (10, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )



# ============================================================
# GUIDED CAPTURE (EMBEDDED TKINTER PREVIEW)
# ============================================================
class _CalibrationCaptureUI:
    """
    Guided stereo checkerboard capture window.

    Each calibration pose provides a target box. The user places
    the checkerboard inside that box, and the detector searches
    only inside the corresponding ROI instead of the full camera
    image.

    This reduces the search area, improves far-distance detection,
    and gives the user explicit visual guidance for every pose.
    """

    def __init__(self, parent, stereo_camera, checkerboard_config):
        self.parent = parent
        self.stereo_camera = stereo_camera
        self.checkerboard_config = checkerboard_config

        self.pattern_size = (
            checkerboard_config["corners_horizontal"],
            checkerboard_config["corners_vertical"],
        )
        self.base_object_points = create_object_points(
            checkerboard_config["corners_horizontal"],
            checkerboard_config["corners_vertical"],
            checkerboard_config["square_size"],
        )

        self.object_points = []
        self.left_image_points = []
        self.right_image_points = []

        self.previous_left = None
        self.previous_right = None
        self.stable_count = 0
        self.stable_since = None
        self.pose_index = 0
        self.attempts = 0
        self.image_size = None

        self.current_left_frame = None
        self.current_right_frame = None
        self.current_left_corners = None
        self.current_right_corners = None
        self.current_stable = False
        self.current_target_ok = False

        self.success = False
        self.cancelled = False
        self._update_job = None

        self.auto_capture_armed = True

        self.flash_text = None
        self.flash_until = 0.0

        self.left_photo = None
        self.right_photo = None

        self._build_ui()

    def _build_ui(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Projectile Tracking - Stereo Calibration")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)

        tk.Label(
            self.window,
            text="Stereo Calibration",
            font=("Arial", 16, "bold"),
        ).pack(pady=(15, 0))

        tk.Label(
            self.window,
            text=(
                "Fit the checkerboard into the box on the LEFT camera "
                "view. It only needs to be fully visible (anywhere) on "
                "the RIGHT -- its position there will look different "
                "because the two cameras are physically apart. "
                "Capture happens automatically once both are steady."
            ),
            font=("Arial", 9),
            wraplength=850,
            justify="center",
        ).pack(pady=(0, 4))

        self.counter_label = tk.Label(
            self.window,
            font=("Arial", 11, "bold"),
        )
        self.counter_label.pack(pady=2)

        self.instruction_label = tk.Label(
            self.window,
            font=("Arial", 11),
            wraplength=850,
            justify="center",
        )
        self.instruction_label.pack(pady=(2, 8))

        video_frame = tk.Frame(self.window)
        video_frame.pack(padx=15)

        left_column = tk.Frame(video_frame)
        left_column.pack(side="left", padx=8)
        tk.Label(
            left_column,
            text="LEFT CAMERA",
            font=("Arial", 10, "bold"),
        ).pack()
        self.left_video_label = tk.Label(left_column)
        self.left_video_label.pack()

        right_column = tk.Frame(video_frame)
        right_column.pack(side="left", padx=8)
        tk.Label(
            right_column,
            text="RIGHT CAMERA",
            font=("Arial", 10, "bold"),
        ).pack()
        self.right_video_label = tk.Label(right_column)
        self.right_video_label.pack()

        status_frame = tk.Frame(self.window)
        status_frame.pack(pady=10)

        self.detection_label = tk.Label(
            status_frame,
            font=("Arial", 10),
        )
        self.detection_label.pack()

        self.status_label = tk.Label(
            status_frame,
            font=("Arial", 10, "bold"),
        )
        self.status_label.pack(pady=(4, 0))

        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=15)

        self.capture_button = tk.Button(
            button_frame,
            text="Capture Now (Space)",
            command=self._on_capture,
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
        )
        self.capture_button.pack(side="left", padx=10)

        tk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            font=("Arial", 11),
            padx=20,
            pady=8,
        ).pack(side="left", padx=10)

        self.window.bind(
            "<space>",
            lambda event: self._on_capture(),
        )
        self.window.bind(
            "<Escape>",
            lambda event: self._on_cancel(),
        )

        self.window.transient(self.parent)
        self.window.grab_set()

    def _frame_to_photo(self, frame):
        display = cv2.resize(
            frame,
            PREVIEW_DISPLAY_SIZE,
            interpolation=cv2.INTER_AREA,
        )
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        return ImageTk.PhotoImage(image=image)

    def _get_current_target(self):
        return CALIBRATION_POSES[
            min(self.pose_index, len(CALIBRATION_POSES) - 1)
        ]

    def _update_preview(self):
        left_frame, right_frame = self.stereo_camera.read()

        if left_frame is None or right_frame is None:
            self.status_label.config(
                text="Status: Unable to read camera frames"
            )
            self._update_job = self.window.after(
                PREVIEW_INTERVAL_MS,
                self._update_preview,
            )
            return

        if self.image_size is None:
            self.image_size = (
                left_frame.shape[1],
                left_frame.shape[0],
            )

        target = self._get_current_target()

        # Both cameras search their FULL frame, uncropped.
        #
        # An earlier version cropped the left camera's search to
        # the guide box (expanded by SEARCH_ROI_SCALE). That crop
        # caused genuine missed detections: findChessboardCornersSB
        # needs every internal corner to be inside the search
        # image or it fails outright, so if the physical board was
        # even slightly larger than the crop, or your hand didn't
        # match the guide pose exactly, the board would be cut off
        # at the crop boundary and detection would fail completely
        # for that frame -- not partially, totally. Searching the
        # full frame removes that failure mode entirely. The left
        # camera's guide box is now purely visual guidance plus a
        # scoring check (board_matches_target), not a search crop.
        left_corners = detect_checkerboard(
            left_frame,
            self.pattern_size,
            roi=None,
        )
        right_corners = detect_checkerboard(
            right_frame,
            self.pattern_size,
            roi=None,
        )

        left_target_ok = (
            left_corners is not None
            and board_matches_target(
                left_corners,
                left_frame.shape,
                target,
            )
        )

        right_ok = (
            right_corners is not None
            and board_in_frame(
                right_corners,
                right_frame.shape,
            )
        )

        both_target_ok = left_target_ok and right_ok

        if both_target_ok:
            left_motion = calculate_corner_motion(
                self.previous_left,
                left_corners,
            )
            right_motion = calculate_corner_motion(
                self.previous_right,
                right_corners,
            )

            if (
                left_motion <= STABILITY_THRESHOLD
                and right_motion <= STABILITY_THRESHOLD
            ):
                if self.stable_since is None:
                    self.stable_since = time.perf_counter()

                self.stable_count += 1
            else:
                self.stable_since = None
                self.stable_count = 0

            self.previous_left = left_corners
            self.previous_right = right_corners

            stable_duration = (
                time.perf_counter() - self.stable_since
                if self.stable_since is not None
                else 0.0
            )

            if stable_duration >= STABILITY_DURATION:
                stable = True
                status = "READY - capturing automatically"
            else:
                stable = False
                status = "Board aligned - hold still"

            detection_text = (
                "Left: DETECTED    Right: DETECTED    "
                "Target: ALIGNED"
            )
        else:
            self.stable_count = 0
            self.stable_since = None
            self.previous_left = None
            self.previous_right = None
            stable = False

            if left_corners is None and right_corners is None:
                detection_text = (
                    "Left: NOT DETECTED    Right: NOT DETECTED"
                )
            elif left_corners is None:
                detection_text = (
                    "Left: NOT DETECTED    Right: DETECTED"
                )
            elif right_corners is None:
                detection_text = (
                    "Left: DETECTED    Right: NOT DETECTED"
                )
            elif not left_target_ok:
                detection_text = (
                    "Left: DETECTED    Right: DETECTED    "
                    "Target: MOVE INTO LEFT BOX"
                )
            else:
                detection_text = (
                    "Left: DETECTED    Right: DETECTED    "
                    "Right camera: board too close to its frame edge"
                )

            if left_corners is None:
                status = "Move the checkerboard into view of the LEFT camera"
            elif right_corners is None:
                status = "Board not visible to the RIGHT camera -- try holding it farther back"
            elif not left_target_ok:
                status = "Move the checkerboard into the highlighted box (left view)"
            else:
                status = "Move the checkerboard slightly -- right camera view is clipped"

        self.current_left_frame = left_frame
        self.current_right_frame = right_frame
        self.current_left_corners = left_corners
        self.current_right_corners = right_corners
        self.current_stable = stable
        self.current_target_ok = both_target_ok

        if stable and self.auto_capture_armed:
            self.auto_capture_armed = False
            self._on_capture()
        elif not stable:
            self.auto_capture_armed = True

        left_display = left_frame.copy()
        right_display = right_frame.copy()

        draw_target_box(
            left_display,
            target,
            detected=left_target_ok,
        )
        # The right camera has no target box to draw (stereo
        # disparity means there's no shared "correct" position --
        # see board_in_frame). A plain label indicates whether the
        # board is fully in view instead.
        draw_in_frame_indicator(
            right_display,
            detected=right_ok,
        )

        if left_corners is not None:
            cv2.drawChessboardCorners(
                left_display,
                self.pattern_size,
                left_corners,
                True,
            )

        if right_corners is not None:
            cv2.drawChessboardCorners(
                right_display,
                self.pattern_size,
                right_corners,
                True,
            )

        self.left_photo = self._frame_to_photo(left_display)
        self.right_photo = self._frame_to_photo(right_display)

        self.left_video_label.config(image=self.left_photo)
        self.right_video_label.config(image=self.right_photo)

        self.counter_label.config(
            text=(
                f"Capture {min(self.pose_index + 1, TARGET_CAPTURES)} "
                f"/ {TARGET_CAPTURES}"
            )
        )
        self.instruction_label.config(
            text=(
                f"{target['name']}: {target['instruction']}"
            )
        )
        self.detection_label.config(text=detection_text)

        if (
            self.flash_text is not None
            and time.time() < self.flash_until
        ):
            self.status_label.config(text=self.flash_text)
        else:
            self.flash_text = None
            self.status_label.config(
                text=f"Status: {status}"
            )

        self._update_job = self.window.after(
            PREVIEW_INTERVAL_MS,
            self._update_preview,
        )

    def _set_flash(self, text, seconds=CAPTURE_FLASH_SECONDS):
        self.flash_text = text
        self.flash_until = time.time() + seconds

    def _on_capture(self):
        if self.pose_index >= TARGET_CAPTURES:
            return

        self.attempts += 1

        if self.attempts >= MAX_CAPTURE_ATTEMPTS:
            self._set_flash(
                "Status: Too many attempts, cancelling",
                seconds=2.0,
            )
            self.success = False
            self._finish()
            return

        if not self.current_stable:
            return

        if not self.current_target_ok:
            self._set_flash(
                "Status: Position the board in the left box, "
                "keep it fully visible on the right"
            )
            return

        if (
            self.current_left_corners is None
            or self.current_right_corners is None
        ):
            return

        left_sharpness = calculate_image_sharpness(
            self.current_left_frame
        )
        right_sharpness = calculate_image_sharpness(
            self.current_right_frame
        )

        if left_sharpness < 30.0 or right_sharpness < 30.0:
            self._set_flash(
                "Status: Image too blurry, hold still"
            )
            self.auto_capture_armed = True
            return

        # Refine corners only for the frame that is actually
        # being accepted for calibration.
        refined_left_corners = refine_checkerboard_corners(
            self.current_left_frame,
            self.current_left_corners,
        )
        refined_right_corners = refine_checkerboard_corners(
            self.current_right_frame,
            self.current_right_corners,
        )

        self.object_points.append(
            self.base_object_points.copy()
        )
        self.left_image_points.append(
            refined_left_corners
        )
        self.right_image_points.append(
            refined_right_corners
        )

        capture_index = self.pose_index + 1

        CAPTURE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        cv2.imwrite(
            str(
                CAPTURE_DIR
                / f"left_{capture_index:03d}.png"
            ),
            self.current_left_frame,
        )
        cv2.imwrite(
            str(
                CAPTURE_DIR
                / f"right_{capture_index:03d}.png"
            ),
            self.current_right_frame,
        )

        self.pose_index += 1
        self.stable_count = 0
        self.stable_since = None
        self.previous_left = None
        self.previous_right = None
        self.auto_capture_armed = True

        self._set_flash(
            f"Status: CAPTURED "
            f"({self.pose_index}/{TARGET_CAPTURES})"
        )

        if self.pose_index >= TARGET_CAPTURES:
            self.success = True
            self._finish()

    def _on_cancel(self):
        self.success = False
        self.cancelled = True
        self._finish()

    def _finish(self):
        if self._update_job is not None:
            self.window.after_cancel(
                self._update_job
            )
            self._update_job = None

        self.window.grab_release()
        self.window.destroy()

    def run(self):
        self._update_job = self.window.after(
            PREVIEW_INTERVAL_MS,
            self._update_preview,
        )
        self.window.wait_window()
        return self.success


def capture_calibration_pairs(stereo_camera, checkerboard_config, parent):
    """
    Guide the user through stereo checkerboard capture using an
    embedded Tkinter preview (see `_CalibrationCaptureUI`).

    Args:
        stereo_camera (StereoCamera): Opened stereo camera.
        checkerboard_config (dict): Checkerboard configuration.
        parent (tk.Tk | tk.Toplevel): Owning window.

    Returns:
        tuple:
            object_points, left_image_points, right_image_points,
            image_size, success (bool)
    """
    ui = _CalibrationCaptureUI(parent, stereo_camera, checkerboard_config)
    success = ui.run()

    if not success or ui.cancelled:
        return None, None, None, None, False

    return (
        ui.object_points,
        ui.left_image_points,
        ui.right_image_points,
        ui.image_size,
        True,
    )


# ============================================================
# CALIBRATION MATHEMATICS
# ============================================================
def calculate_calibration(
    object_points, left_image_points, right_image_points, image_size
):
    """
    Calculate monocular and stereo calibration parameters.

    Returns:
        dict containing all calibration matrices, distortion
        coefficients, stereo geometry, rectification data,
        and reprojection errors.
    """
    (
        left_rms,
        left_camera_matrix,
        left_distortion,
        left_rvecs,
        left_tvecs,
    ) = cv2.calibrateCamera(object_points, left_image_points, image_size, None, None)

    (
        right_rms,
        right_camera_matrix,
        right_distortion,
        right_rvecs,
        right_tvecs,
    ) = cv2.calibrateCamera(
        object_points, right_image_points, image_size, None, None
    )

    # Intrinsics are calibrated independently first, then held fixed
    # during stereo calibration. This is the standard two-stage
    # approach for a fixed stereo camera pair.
    stereo_flags = cv2.CALIB_FIX_INTRINSIC

    stereo_criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER,
        100,
        1e-6,
    )

    stereo_rms, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
        object_points,
        left_image_points,
        right_image_points,
        left_camera_matrix,
        left_distortion,
        right_camera_matrix,
        right_distortion,
        image_size,
        criteria=stereo_criteria,
        flags=stereo_flags,
    )

    (R1, R2, P1, P2, Q, roi_left, roi_right) = cv2.stereoRectify(
        left_camera_matrix,
        left_distortion,
        right_camera_matrix,
        right_distortion,
        image_size,
        R,
        T,
        alpha=0,
    )

    left_error = calculate_reprojection_error(
        object_points,
        left_image_points,
        left_camera_matrix,
        left_distortion,
        left_rvecs,
        left_tvecs,
    )
    right_error = calculate_reprojection_error(
        object_points,
        right_image_points,
        right_camera_matrix,
        right_distortion,
        right_rvecs,
        right_tvecs,
    )

    return {
        "left_camera_matrix": left_camera_matrix,
        "left_distortion": left_distortion,
        "right_camera_matrix": right_camera_matrix,
        "right_distortion": right_distortion,
        "R": R,
        "T": T,
        "E": E,
        "F": F,
        "R1": R1,
        "R2": R2,
        "P1": P1,
        "P2": P2,
        "Q": Q,
        "roi_left": roi_left,
        "roi_right": roi_right,
        "image_width": image_size[0],
        "image_height": image_size[1],
        "left_rms": float(left_rms),
        "right_rms": float(right_rms),
        "stereo_rms": float(stereo_rms),
        "left_reprojection_error": float(left_error),
        "right_reprojection_error": float(right_error),
    }


def calculate_reprojection_error(
    object_points, image_points, camera_matrix, distortion, rvecs, tvecs
):
    """
    Calculate mean reprojection error in pixels.
    """
    total_error = 0.0
    total_points = 0

    for object_set, image_set, rvec, tvec in zip(
        object_points, image_points, rvecs, tvecs
    ):
        projected, _ = cv2.projectPoints(
            object_set, rvec, tvec, camera_matrix, distortion
        )
        error = cv2.norm(image_set, projected, cv2.NORM_L2)
        total_error += error * error
        total_points += len(object_set)

    if total_points == 0:
        return float("inf")

    return float((total_error / total_points) ** 0.5)


# ============================================================
# SAVE CALIBRATION
# ============================================================
def save_calibration(calibration, checkerboard_config, stereo_camera):
    """
    Save calculated stereo calibration parameters and update
    the persistent camera configuration with checkerboard data.
    """
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)

    # Save calculated stereo parameters.
    np.savez(
        CALIBRATION_PATH,
        left_camera_matrix=calibration["left_camera_matrix"],
        left_distortion=calibration["left_distortion"],
        right_camera_matrix=calibration["right_camera_matrix"],
        right_distortion=calibration["right_distortion"],
        R=calibration["R"],
        T=calibration["T"],
        E=calibration["E"],
        F=calibration["F"],
        R1=calibration["R1"],
        R2=calibration["R2"],
        P1=calibration["P1"],
        P2=calibration["P2"],
        Q=calibration["Q"],
        roi_left=calibration["roi_left"],
        roi_right=calibration["roi_right"],
        image_width=calibration["image_width"],
        image_height=calibration["image_height"],
        left_rms=calibration["left_rms"],
        right_rms=calibration["right_rms"],
        stereo_rms=calibration["stereo_rms"],
        left_reprojection_error=calibration["left_reprojection_error"],
        right_reprojection_error=calibration["right_reprojection_error"],
        checkerboard_corners_horizontal=checkerboard_config["corners_horizontal"],
        checkerboard_corners_vertical=checkerboard_config["corners_vertical"],
        checkerboard_square_size_mm=checkerboard_config["square_size"],
        baseline_mm=float(np.linalg.norm(calibration["T"])),
    )

    # Merge checkerboard information into the existing
    # camera configuration rather than replacing it.
    config = stereo_camera.get_config()
    config["checkerboard"] = checkerboard_config

    with CAMERA_CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

    print(f"Stereo calibration saved to: {CALIBRATION_PATH}")
    print(f"Camera/checkerboard configuration saved to: {CAMERA_CONFIG_PATH}")


# ============================================================
# RESULT UI
# ============================================================
def show_calibration_result(calibration, parent):
    """
    Display calibration quality and allow the user to either
    accept the result or retry.

    Args:
        calibration (dict): Output of calculate_calibration().
        parent (tk.Tk | tk.Toplevel): Owning window.

    Returns:
        bool: True if the user accepted the calibration.
    """
    stereo_error = calibration["stereo_rms"]

    if stereo_error <= GOOD_ERROR:
        quality = "GOOD"
    elif stereo_error <= ACCEPTABLE_ERROR:
        quality = "ACCEPTABLE"
    else:
        quality = "HIGH ERROR"

    window = tk.Toplevel(parent)
    window.title("Projectile Tracking - Calibration Result")
    window.geometry("600x430")
    window.resizable(False, False)

    tk.Label(
        window,
        text="Calibration Results",
        font=("Arial", 18, "bold"),
    ).pack(pady=(20, 10))

    result_text = (
        f"Left camera reprojection error: "
        f"{calibration['left_reprojection_error']:.3f} px\n\n"
        f"Right camera reprojection error: "
        f"{calibration['right_reprojection_error']:.3f} px\n\n"
        f"Stereo RMS error: {stereo_error:.3f} px\n\n"
        f"Calibration quality: {quality}"
    )
    tk.Label(
        window,
        text=result_text,
        font=("Arial", 11),
        justify="center",
    ).pack(pady=20)

    tk.Label(
        window,
        text=(
            "Lower reprojection error generally indicates a "
            "better calibration.\n"
            "If the error is high, recapturing with more varied "
            "checkerboard views is recommended."
        ),
        font=("Arial", 9),
        justify="center",
    ).pack(pady=10)

    decision = {"accepted": False}

    def accept():
        decision["accepted"] = True
        window.destroy()

    def retry():
        decision["accepted"] = False
        window.destroy()

    button_frame = tk.Frame(window)
    button_frame.pack(pady=20)

    tk.Button(
        button_frame,
        text="Use Calibration",
        command=accept,
        font=("Arial", 11, "bold"),
        padx=20,
        pady=8,
    ).pack(side="left", padx=10)

    tk.Button(
        button_frame,
        text="Retry Calibration",
        command=retry,
        font=("Arial", 11),
        padx=20,
        pady=8,
    ).pack(side="left", padx=10)

    window.protocol("WM_DELETE_WINDOW", retry)

    window.transient(parent)
    window.grab_set()
    window.wait_window()

    return decision["accepted"]


# ============================================================
# MAIN CALIBRATION ENTRY POINT
# ============================================================
def run_calibration(stereo_camera, parent=None):
    """
    Run the complete guided stereo calibration workflow.

    Exactly one Tk root exists for the whole application. If
    `parent` is not supplied (e.g. running this module directly
    for testing) a single hidden root is created locally here
    and destroyed before returning -- it is never left running
    alongside another root.

    Args:
        stereo_camera:
            Configured StereoCamera instance supplied by main.py.
        parent (tk.Tk | tk.Toplevel | None):
            Owning window. main.py should pass its own root.

    Returns:
        bool:
            True if calibration completed and was accepted,
            otherwise False.
    """
    owns_root = False
    if parent is None:
        parent = tk.Tk()
        parent.withdraw()
        owns_root = True

    try:
        if stereo_camera is None:
            print("Calibration cannot start: no StereoCamera was provided.")
            return False

        if not stereo_camera.open():
            return False

        checkerboard_config = request_checkerboard_config(parent)
        if checkerboard_config is None:
            return False

        print(
            "[CALIBRATION] Checkerboard: "
            f"{checkerboard_config['corners_horizontal']} x "
            f"{checkerboard_config['corners_vertical']} internal corners, "
            f"{checkerboard_config['square_size']} mm squares"
        )

        ready = messagebox.askokcancel(
            "Stereo Calibration",
            (
                "Before calibration begins:\n\n"
                "1. Keep both cameras firmly fixed.\n"
                "2. Do not change camera position or resolution.\n"
                "3. Use the checkerboard at its printed scale.\n"
                "4. Move the checkerboard, not the cameras.\n"
                "6. Watch the LEFT camera view and fit the board into "
                "its highlighted box for each pose. The board's "
                "position in the RIGHT camera view will look "
                "different (the two cameras are physically apart) -- "
                "it only needs to be fully visible there, not aligned "
                "to any box.\n\n"
                "The program will guide you through 12 target poses.\n"
                "Place the checkerboard inside the highlighted box "
                "for each pose."
            ),
            parent=parent,
        )

        if not ready:
            return False

        while True:
            (
                object_points,
                left_image_points,
                right_image_points,
                image_size,
                success,
            ) = capture_calibration_pairs(stereo_camera, checkerboard_config, parent)

            if not success:
                return False

            if len(object_points) < 8:
                messagebox.showerror(
                    "Calibration Failed",
                    "Not enough valid stereo image pairs were captured.",
                    parent=parent,
                )
                return False

            calibration = calculate_calibration(
                object_points, left_image_points, right_image_points, image_size
            )

            accepted = show_calibration_result(calibration, parent)

            if not accepted:
                continue

            save_calibration(calibration, checkerboard_config, stereo_camera)
            return True

    finally:
        if owns_root:
            parent.destroy()


# ============================================================
# MODULE ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print(
        "calibration.py is designed to be called by main.py "
        "with a configured StereoCamera instance."
    )