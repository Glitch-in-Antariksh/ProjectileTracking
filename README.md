# Projectile Tracking

An embedded AI and computer vision project focused on real-time projectile detection, 3D localization, trajectory estimation, and trajectory prediction using stereo vision and depth perception.

## Overview

The objective of this project is to develop a computer vision system capable of detecting a moving projectile, estimating its position in three-dimensional space, tracking its motion, and predicting its future trajectory.

The project is being developed incrementally, beginning with a laptop-based stereo vision system. The first phase focuses entirely on **camera perception, object identification, 3D localization, motion tracking, and trajectory prediction**.

A physical actuation and interception system is planned as a future extension once the vision and prediction pipeline has been validated.

---

# Phase 1 — Vision and Trajectory Prediction

Phase 1 is the core computer vision stage of the project.

The entire system can be developed and tested using:

* ELP stereo camera
* Laptop
* Python
* OpenCV
* YOLO
* PyCharm

No Raspberry Pi or external actuation hardware is required during this phase.

The primary objective is to progress from raw stereo camera data to a predicted three-dimensional trajectory.

```text
                  ELP Stereo Camera
                          │
                          ▼
                  Stereo Image Pair
                    /          \
                   ▼            ▼
              Left Image     Right Image
                   │            │
                   └─────┬──────┘
                         ▼
                  Stereo Processing
                         │
                         ▼
                  Depth Estimation
                         │
                         ▼
                  3D Localization
                         │
                         ▼
                   Object Tracking
                         │
                         ▼
                 Trajectory Estimation
                         │
                         ▼
                 Trajectory Prediction
```

## 1. Camera Testing

The first implemented component is `camera_test.py`.

Its purpose is to understand and validate the connected camera hardware before it is integrated into the rest of the system.

The testing layer:

* Discovers available camera indices
* Allows the user to select a camera
* Inspects frame resolution, shape, channels, and aspect ratio
* Identifies feeds that are likely to contain stereo imagery
* Measures approximate camera FPS
* Provides a live preview of the selected camera
* Displays the suspected left and right views separately
* Produces a final camera-test summary

Camera indices are intentionally not hardcoded because they can vary between systems.

The stereo-camera identification is currently heuristic and is based on the aspect ratio of the captured frame. It is intended to assist with hardware identification rather than serve as definitive camera identification.

The purpose of this layer is to isolate hardware-specific testing from the rest of the project.

---

## 2. Stereo Camera Interface

After the hardware has been validated, the camera will be integrated through `camera.py`.

This module will provide a consistent interface for acquiring stereo frames while hiding hardware-specific details from the rest of the project.

The rest of the system should eventually be able to request a stereo image pair without needing to know:

* Which camera index is being used
* How the camera is exposed to the operating system
* How the stereo frame is packaged
* How the left and right views are extracted

The intended abstraction is conceptually:

```python
left_frame, right_frame = camera.read()
```

This creates a clean boundary between the physical camera and the computer vision pipeline.

---

## 3. Stereo Camera Calibration

Once reliable stereo images can be acquired, the camera will be calibrated.

Stereo calibration will establish the geometric properties required to estimate physical depth from the two camera views.

The calibration process will determine parameters such as:

* Camera intrinsic parameters
* Lens distortion
* Relative orientation of the two cameras
* Relative translation between the cameras
* Stereo rectification parameters

A calibration target such as a chessboard pattern will be used to obtain corresponding points between the two views.

Calibration data will be stored in:

```text
data/calibration/
```

The goal is to establish a reliable geometric model of the stereo camera before attempting metric depth estimation.

---

## 4. Stereo Rectification

After calibration, the stereo images will be rectified so that corresponding points between the left and right images can be compared more reliably.

```text
Raw Left Image       Raw Right Image
       │                    │
       └────────┬───────────┘
                ▼
        Stereo Calibration
                │
                ▼
        Stereo Rectification
                │
          ┌─────┴─────┐
          ▼           ▼
      Rectified    Rectified
        Left         Right
```

Rectification is an important intermediate stage between calibration and depth estimation.

---

## 5. Depth Estimation

Once the stereo camera has been calibrated and rectified, the system will estimate depth from the disparity between corresponding points in the two images.

```text
Left Image + Right Image
           │
           ▼
        Disparity
           │
           ▼
        Depth Map
```

The first experiments will use objects placed at known distances from the camera.

For example:

```text
Actual Distance    Estimated Distance
      0.5 m                ?
      1.0 m                ?
      1.5 m                ?
      2.0 m                ?
```

These experiments will be used to evaluate the accuracy and stability of the stereo-depth system before introducing a moving target.

---

## 6. Projectile Identification

After the stereo-depth pipeline is functional, object detection will be introduced.

The initial target will be a small, lightweight **paper projectile** or another soft test projectile whose appearance can be reliably detected by the vision system.

YOLO will be used to identify the projectile in the camera frames.

The initial objective is straightforward:

> Detect the projectile reliably.

At this stage, the focus is on object identification rather than trajectory prediction.

---

## 7. 3D Projectile Localization

Object detection and stereo depth will then be combined.

YOLO provides the projectile's location within the image, while the stereo system provides depth information.

Together, these measurements can be used to estimate the projectile's position in three-dimensional space.

```text
                 YOLO Detection
                       │
                       ▼
               Image Coordinates
                       │
                       ├───────────────┐
                       │               │
                       ▼               ▼
                 Stereo Position     Depth
                       │               │
                       └───────┬───────┘
                               ▼
                          3D Position
                           (X, Y, Z)
```

The goal is to move from simply detecting a projectile in an image to determining **where it is in physical space**.

---

## 8. Moving Projectile Tracking

Once static 3D localization is reliable, the system will be tested with a moving projectile.

A controlled **pendulum-mounted paper projectile** will initially be used.

The pendulum provides a repeatable motion that allows the tracking system to be evaluated before introducing a freely launched projectile.

The system will collect a sequence of 3D measurements over time:

```text
t₀ → (X₀, Y₀, Z₀)
t₁ → (X₁, Y₁, Z₁)
t₂ → (X₂, Y₂, Z₂)
t₃ → (X₃, Y₃, Z₃)
...
```

From this sequence, the system can estimate quantities such as:

* Position
* Velocity
* Direction of motion
* Acceleration
* Motion history

---

## 9. Trajectory Estimation

The sequence of observed 3D positions will be used to estimate the projectile's trajectory.

The project will investigate suitable mathematical and computational approaches for fitting the observed motion.

The initial experiments will use controlled motion before moving toward more complex projectile trajectories.

The goal is to obtain a reliable representation of the projectile's current motion.

---

## 10. Trajectory Prediction

Once trajectory estimation is reliable, the system will use the observed motion to predict the projectile's future position.

```text
Observed 3D Motion
        │
        ▼
Trajectory Estimation
        │
        ▼
 Motion Model
        │
        ▼
Future Position
        │
        ▼
Predicted Trajectory
```

The eventual objective is for the system to determine not only:

> Where is the projectile now?

but also:

> Where is the projectile going?

and:

> Where will it be after a given amount of time?

This prediction capability forms the final objective of Phase 1.

---

# System Architecture

The Phase 1 architecture is designed to keep each major responsibility independent.

```text
                    ELP Stereo Camera
                           │
                           ▼
                      camera_test.py
                           │
                    Hardware Validation
                           │
                           ▼
                        camera.py
                           │
                    Stereo Image Pair
                           │
                           ▼
                     calibration.py
                           │
                    Stereo Calibration
                           │
                           ▼
                    Stereo Rectification
                           │
                           ▼
                         depth.py
                           │
                    Depth Estimation
                           │
                           ▼
                       YOLO Detection
                           │
                           ▼
                      3D Localization
                           │
                           ▼
                       tracking.py
                           │
                           ▼
                     trajectory.py
                           │
                           ▼
                 Trajectory Prediction
```

The goal is to keep hardware handling, calibration, depth estimation, object detection, tracking, and trajectory prediction as separate modules.

This allows each stage to be tested independently and prevents hardware-specific complexity from spreading throughout the project.

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

---

# Future Work — Phase 2

After the vision and trajectory-prediction pipeline is validated, the project may be extended into a physical interception system.

This stage would introduce embedded hardware such as a Raspberry Pi, sensors, servos, actuators, and a suitable interception mechanism.

The predicted trajectory from Phase 1 would be used to determine a suitable interception point, after which the physical system could position or activate an actuator to interact with the predicted trajectory.

The exact hardware architecture will be determined after Phase 1 has been successfully completed.

The Raspberry Pi is therefore intentionally **not part of the current vision-development workflow**.

---

# Development Roadmap

The project is being developed incrementally. Each major stage should be validated before the next stage is introduced.

* [x] Project planning and repository setup
* [x] Git and GitHub integration
* [x] Initial project structure
* [x] Laptop development environment
* [x] ELP stereo camera acquisition
* [x] Camera discovery and testing
* [x] Camera selection
* [x] Stereo-feed inspection
* [x] Camera preview
* [x] Approximate FPS measurement
* [ ] Reusable stereo camera interface
* [ ] Stereo image acquisition
* [ ] Stereo camera calibration
* [ ] Stereo rectification
* [ ] Depth estimation
* [ ] Known-distance depth validation
* [ ] Projectile identification using YOLO
* [ ] 3D projectile localization
* [ ] Moving projectile tracking
* [ ] Trajectory estimation
* [ ] Trajectory prediction
* [ ] Phase 1 system validation
* [ ] Physical interception system design
* [ ] Raspberry Pi integration
* [ ] Actuator and sensor integration
* [ ] Phase 2 system testing

---

# Current Status

The initial project structure and development environment have been established.

The ELP stereo camera has been successfully connected to the laptop and validated using `camera_test.py`. Camera discovery, selection, frame inspection, stereo-feed inspection, live preview, and approximate FPS measurement are currently functional.

The next development milestone is to implement the reusable stereo camera interface and begin the stereo calibration process.
