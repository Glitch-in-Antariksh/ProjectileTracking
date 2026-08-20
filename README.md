# Projectile Tracking

An embedded AI and computer vision project focused on real-time projectile detection, 3D localization, trajectory estimation, and trajectory prediction using stereo vision.

## Overview

The objective of this project is to develop a computer vision system capable of detecting a moving projectile, estimating its position in three-dimensional space, tracking its motion, and predicting its future trajectory.

Development is currently focused on a laptop-based stereo vision system. The first phase covers:

- Stereo camera acquisition
- Camera configuration and validation
- Stereo camera calibration
- Projectile identification
- 3D localization
- Motion tracking
- Trajectory estimation
- Trajectory prediction

A physical actuation and interception system is planned as a future extension once the vision and prediction pipeline has been validated.

---

# Phase 1 — Vision and Trajectory Prediction

Phase 1 is developed and tested using:

- ELP stereo camera
- Laptop
- Python
- OpenCV
- YOLO
- PyCharm

No Raspberry Pi or external actuation hardware is required during this phase.

The current development priority is to complete the vision pipeline from stereo camera input to a tracked and predicted three-dimensional projectile trajectory.

---

## 1. Camera Testing

`camera_test.py` is used to discover and validate the connected camera before it is used by the rest of the system.

The testing layer:

- Discovers available camera indices
- Allows the user to select a camera
- Inspects frame resolution, shape, channels, and aspect ratio
- Identifies feeds that are likely to contain stereo imagery
- Measures approximate camera FPS
- Provides a live preview
- Displays the left and right stereo views separately
- Tests available camera resolutions
- Allows the user to select a suitable resolution

The camera is currently capable of providing a **2560 × 960 stereo frame**, giving approximately **1280 × 960 pixels per camera view** at around 50 FPS.

Camera indices are intentionally not hardcoded because they can vary between systems.

The stereo-camera identification is heuristic and is based on the captured frame characteristics. It is intended to assist with hardware identification rather than serve as definitive camera identification.

---

## 2. Stereo Camera Interface

`camera.py` provides the reusable interface between the physical stereo camera and the rest of the project.

It is responsible for:

- Loading the selected camera configuration
- Opening the selected camera
- Requesting the configured resolution
- Verifying the actual resolution supplied by the camera
- Capturing stereo frames
- Splitting the side-by-side camera feed into left and right images
- Releasing the camera safely

The rest of the system can obtain a stereo image pair through:

```python
left_frame, right_frame = camera.read()
```

This keeps hardware-specific camera handling separate from the computer vision modules.

---

## 3. Stereo Camera Calibration

`calibration.py` is used to calibrate the stereo camera using a physical checkerboard.

The current checkerboard contains **8 × 10 squares**, corresponding to **7 × 9 internal corners**. The calibration system uses the internal-corner count when detecting the pattern.

The calibration process estimates:

- Camera intrinsic parameters
- Lens distortion
- Relative orientation of the two cameras
- Relative translation between the cameras
- Stereo calibration parameters

Calibration data is stored in:

```text
data/calibration/
```

### Calibration Interface

Calibration is designed as a guided user interaction rather than requiring the user to manually decide when to capture each image.

During calibration, the interface displays the live stereo camera views and provides a **target box** showing approximately where the checkerboard should be positioned for the current capture.

The target box is a visual guide. It helps the user move the checkerboard into useful positions and orientations while the system searches for the pattern in the surrounding image area.

The system automatically detects the checkerboard and captures a pose when the board is successfully detected and sufficiently stable.

Multiple guided checkerboard poses are collected so that the calibration contains varied positions, orientations, and perspectives.

At the end of calibration, the interface reports the left-camera reprojection error, right-camera reprojection error, stereo RMS error, and an overall calibration-quality result.

A successful calibration is then available to the rest of the vision pipeline.

---

## 4. Stereo Rectification

After calibration, the stereo images can be rectified so that corresponding points in the left and right images can be compared more reliably.

Rectification is the intermediate stage between calibration and depth estimation.

The rectified images will provide the basis for subsequent stereo correspondence and 3D localization.

---

## 5. Depth Estimation

Once the stereo camera has been calibrated and rectified, the system will estimate depth from the relationship between corresponding points in the two camera views.

Initial experiments will use objects placed at known distances from the camera.

For example:

```text
Actual Distance    Estimated Distance
      0.5 m                ?
      1.0 m                ?
      1.5 m                ?
      2.0 m                ?
```

These experiments will be used to evaluate the accuracy and stability of the stereo-depth system before introducing a moving projectile.

---

## 6. Projectile Identification

After the stereo-depth foundation is functional, object detection will be introduced.

The initial target will be a small, lightweight **paper projectile** or another soft test projectile whose appearance can be reliably detected by the vision system.

YOLO is planned for projectile identification.

The initial objective is straightforward:

> Detect the projectile reliably.

At this stage, the focus is on identifying the projectile in the camera frames rather than predicting its trajectory.

---

## 7. 3D Projectile Localization

Projectile detection and stereo depth will then be combined.

The object detector will provide the projectile's image location, while the calibrated stereo system will provide the information required to estimate its depth.

Together, these measurements will produce an estimated projectile position in three-dimensional space.

The objective is to move from detecting a projectile in an image to determining **where it is in physical space**.

---

## 8. Moving Projectile Tracking

Once static 3D localization is reliable, the system will be tested with a moving projectile.

A controlled **pendulum-mounted paper projectile** will initially be used.

The pendulum provides repeatable motion so that the tracking system can be evaluated before introducing a freely launched projectile.

The system will collect a sequence of 3D measurements over time, allowing it to estimate:

- Position
- Velocity
- Direction of motion
- Acceleration
- Motion history

---

## 9. Trajectory Estimation

The sequence of observed 3D positions will be used to estimate the projectile's trajectory.

The project will investigate suitable mathematical and computational approaches for fitting the observed motion.

Controlled motion will be used for the initial experiments before moving toward more complex projectile trajectories.

The goal is to obtain a reliable representation of the projectile's current motion.

---

## 10. Trajectory Prediction

Once trajectory estimation is reliable, the system will use the observed motion to predict the projectile's future position.

The eventual objective is for the system to determine:

> Where is the projectile now?

> Where is the projectile going?

> Where will it be after a given amount of time?

This prediction capability forms the final objective of Phase 1.

---

# User Interface

The project is designed to provide a simple guided interface for setup and operation.

When the application starts, the main interface shows the status of the camera configuration and stereo calibration.

Once both are ready, the user can select:

- **Start Tracking** — begins the tracking stage
- **Run Setup Again** — repeats the camera/calibration setup
- **Exit** — closes the application

During camera setup, the user is guided through camera selection and resolution selection.

During stereo calibration, the user sees the live stereo camera views and a target box that indicates where to position the checkerboard for each capture. The system handles detection and automatic capture once the board is correctly positioned and stable.

The tracking interface will be implemented as the next major development stage.

---

# System Architecture

The project is divided into independent modules so that camera handling, calibration, depth estimation, tracking, and trajectory processing can be developed and tested separately.

### Current modules

- `main.py` — application interface and overall workflow
- `camera_test.py` — camera discovery, inspection, resolution testing, and preview
- `camera.py` — reusable stereo camera interface
- `calibration.py` — stereo checkerboard calibration
- `depth.py` — depth and 3D localization
- `tracking.py` — projectile detection and tracking
- `trajectory.py` — trajectory estimation and prediction
- `utils.py` — shared utilities

The tracking, depth, and trajectory modules are currently being developed after completion of the camera setup and stereo calibration stages.

---

# Project Structure

```text
ProjectileTracking/
├── src/
│   ├── main.py
│   ├── camera.py
│   ├── camera_test.py
│   ├── calibration.py
│   ├── depth.py
│   ├── tracking.py
│   ├── trajectory.py
│   └── utils.py
│
├── data/
│   ├── calibration/
│   └── captures/
│
├── docs/
├── tests/
├── requirements.txt
└── README.md
```

Generated calibration captures are local working data and should not be committed to the repository.

---

# Future Work — Phase 2

After the vision and trajectory-prediction pipeline is validated, the project may be extended into a physical interception system.

This stage may introduce embedded hardware such as a Raspberry Pi, sensors, servos, actuators, and a suitable interception mechanism.

The predicted trajectory from Phase 1 would be used to determine a suitable interception point, after which the physical system could position or activate an actuator to interact with the predicted trajectory.

The exact hardware architecture will be determined after Phase 1 has been successfully completed.

The Raspberry Pi is therefore intentionally **not part of the current vision-development workflow**.

---

# Development Roadmap

The project is being developed incrementally. Each major stage is validated before the next stage is introduced.

- [x] Project planning and repository setup
- [x] Git and GitHub integration
- [x] Initial project structure
- [x] Laptop development environment
- [x] ELP stereo camera acquisition
- [x] Camera discovery and testing
- [x] Camera selection
- [x] Stereo-feed inspection
- [x] Camera preview
- [x] Approximate FPS measurement
- [x] Camera resolution testing and selection
- [x] Reusable stereo camera interface
- [x] Stereo image acquisition
- [x] Stereo checkerboard calibration
- [x] Guided calibration interface
- [x] Automatic checkerboard capture
- [x] Calibration quality validation
- [ ] Stereo rectification
- [ ] Depth estimation
- [ ] Known-distance depth validation
- [ ] Projectile identification using YOLO
- [ ] 3D projectile localization
- [ ] Moving projectile tracking
- [ ] Trajectory estimation
- [ ] Trajectory prediction
- [ ] Phase 1 system validation
- [ ] Physical interception system design
- [ ] Raspberry Pi integration
- [ ] Actuator and sensor integration
- [ ] Phase 2 system testing

---

# Current Status

The camera setup and stereo calibration stages are complete.

The ELP stereo camera has been successfully connected to the laptop and validated. The system can discover the camera, test available resolutions, select a suitable stereo resolution, acquire synchronized left and right views, and provide them through the reusable camera interface.

Stereo calibration is also functional. The checkerboard calibration interface guides the user through multiple poses using an on-screen target box and automatically captures valid, stable views.

The current calibration setup uses a **2560 × 960 stereo frame**, providing approximately **1280 × 960 pixels per camera view**. A recent calibration produced:

- Left-camera reprojection error: **0.371 px**
- Right-camera reprojection error: **0.379 px**
- Stereo RMS error: **0.746 px**
- Calibration quality: **GOOD**

The project is now moving into the **tracking stage**.

`tracking.py`, `depth.py`, and `trajectory.py` are currently placeholders. The next milestone is to implement reliable projectile detection and tracking, followed by stereo depth, 3D localization, and trajectory estimation.
