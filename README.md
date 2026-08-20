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

# Phase 1 — Stereo Vision and 3D Localization

Phase 1 focuses on establishing a reliable stereo-vision foundation using a **static crushed paper ball** as the initial target.

The system is developed and tested using:

- ELP stereo camera
- Laptop
- Python
- OpenCV
- YOLO
- PyCharm

No Raspberry Pi or external actuation hardware is required during this phase.

The main objectives are:

- Reliable stereo image acquisition
- Camera configuration and validation
- Stereo camera calibration
- Object detection
- Depth estimation
- 3D position estimation

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

The current camera setup can provide a **2560 × 960 stereo frame**, giving approximately **1280 × 960 pixels per camera view** at around 50 FPS.

## 2. Stereo Camera Interface

`camera.py` provides the reusable interface between the physical stereo camera and the rest of the project.

It handles:

- Loading the selected camera configuration
- Opening the camera
- Requesting and verifying the configured resolution
- Capturing stereo frames
- Splitting the side-by-side feed into left and right images
- Releasing the camera safely

The rest of the system can obtain a stereo image pair through:

```python
left_frame, right_frame = camera.read()
```

## 3. Stereo Camera Calibration

`calibration.py` calibrates the stereo camera using a physical checkerboard.

The current checkerboard contains **8 × 10 squares**, corresponding to **7 × 9 internal corners**.

The calibration process estimates:

- Camera intrinsic parameters
- Lens distortion
- Relative orientation of the cameras
- Relative translation between the cameras
- Stereo calibration parameters

Calibration data is stored in:

```text
data/calibration/
```

### Calibration Interface

The calibration screen shows the live left and right camera views and a **target box** for the current checkerboard pose.

The target box is a visual guide. It helps the user position the checkerboard in useful locations and orientations while the system searches the surrounding image area for the pattern.

Once the checkerboard is detected and sufficiently stable, the system automatically captures the pose.

Multiple guided poses are collected so that the calibration contains varied positions, orientations, and perspectives.

At the end of calibration, the interface reports the left-camera reprojection error, right-camera reprojection error, stereo RMS error, and overall calibration quality.

## 4. Stereo Rectification

After calibration, the stereo images can be rectified so that corresponding points in the left and right images can be compared more reliably.

Rectification provides the basis for stereo correspondence and 3D localization.

## 5. Static Paper-Ball Detection and Depth Estimation

The first actual vision experiment uses a **crushed paper ball placed at known positions**.

The objective is to establish that the system can:

1. Detect the paper ball in the left image.
2. Detect the same paper ball in the right image.
3. Match the two observations.
4. Estimate its depth from the stereo pair.
5. Produce a three-dimensional position.

Known-distance tests will be used to evaluate the depth system:

```text
Actual Distance    Estimated Distance
      0.5 m                ?
      1.0 m                ?
      1.5 m                ?
      2.0 m                ?
```

The purpose of this stage is to validate stereo geometry and 3D localization before introducing motion.

---

# Phase 2 — Controlled Motion Tracking

Once the static paper ball can be detected and localized reliably in 3D, the same object will be introduced as a controlled moving target.

## 6. Pendulum Motion

The crushed paper ball will initially be attached to a pendulum.

This provides repeatable motion while allowing the tracking system to be tested under real movement.

The system will collect a sequence of 3D measurements over time:

```text
t₀ → (X₀, Y₀, Z₀)
t₁ → (X₁, Y₁, Z₁)
t₂ → (X₂, Y₂, Z₂)
t₃ → (X₃, Y₃, Z₃)
...
```

From this sequence, the system can estimate:

- Position
- Velocity
- Direction of motion
- Acceleration
- Motion history

The pendulum stage validates the tracking pipeline before introducing freely moving objects.

## 7. Trajectory Estimation

The sequence of observed 3D positions will be used to estimate the object's trajectory.

The project will investigate suitable mathematical and computational approaches for fitting the observed motion.

Controlled pendulum motion will be used for the initial experiments before moving toward more complex motion.

---

# Phase 3 — Projectile Tracking and Prediction

After static localization and controlled motion tracking are working reliably, the system will progress to the final application: projectile motion.

## 8. Projectile Motion

The completed detection and tracking pipeline will be applied to a freely moving projectile.

At this stage, the system will need to handle:

- Rapid movement
- Changing position and orientation
- Limited observation time
- Continuous stereo detection
- 3D localization over time

The goal is to maintain a reliable sequence of three-dimensional observations while the projectile is in motion.

## 9. Trajectory Prediction

Once projectile tracking is reliable, the observed motion will be used to predict the projectile's future position.

The final system should be able to determine:

> Where is the projectile now?

> Where is it going?

> Where will it be after a given amount of time?

This prediction capability forms the final objective of the project.

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
