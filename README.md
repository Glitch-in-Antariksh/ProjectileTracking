# ProjectileTracking

An embedded AI and computer vision project focused on real-time projectile detection, 3D localization, and trajectory estimation using stereo vision and depth perception.

## Overview

The objective of this project is to develop a modular system capable of detecting and tracking fast-moving projectiles in real time. The system will use a stereo camera setup to estimate depth, calculate the projectile's position in three-dimensional space, and predict its trajectory. The project is designed with a modular architecture so that each component can be developed, tested, and improved independently.

## Planned Workflow

The development process is divided into the following stages:

* [x] Project planning and repository setup
* [x] Raspberry Pi development environment
* [x] Git and GitHub integration
* [x] Initial project structure
* [x] Camera setup and testing
* [x] Capture synchronized stereo images
* [x] Camera calibration
* [ ] Stereo rectification
* [ ] Depth estimation
* [ ] Projectile detection
* [ ] Projectile tracking
* [ ] 3D position estimation
* [ ] Trajectory prediction
* [ ] Performance optimization
* [ ] System testing and validation

## Project Structure

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
├── data/
│   ├── calibration/
│   └── captures/
├── docs/
├── tests/
├── requirements.txt
└── README.md
```

## Camera Testing

The first implemented component of the project is `camera_test.py`, which is responsible for discovering and validating camera hardware before it is integrated into the main computer vision pipeline.

The testing layer is designed to avoid making assumptions about camera indices, since camera indices can vary between systems depending on the connected hardware and operating system.

### Features

`camera_test.py` currently provides:

* Automatic scanning of available camera indices
* Detection of cameras capable of providing readable frames
* Resolution and frame-shape inspection
* Channel and aspect-ratio detection
* Heuristic identification of cameras that may provide a stereo feed
* A graphical interface for selecting the camera to test
* Automatic highlighting of the most likely stereo camera
* Measurement of the camera's approximate real-world FPS
* Live preview of the selected camera
* Separate preview of the left and right halves of a suspected side-by-side stereo feed
* Final camera-test summary containing the detected properties

The stereo-camera identification is currently heuristic and is based on the frame's aspect ratio. It is intended to assist the user during hardware testing rather than serve as a definitive camera identification method.

### Purpose

The purpose of this testing layer is to isolate hardware-specific behavior from the rest of the project.

Once the camera behavior has been established, the reusable camera interface can be implemented in `camera.py`. This allows later modules such as calibration, depth estimation, tracking, and trajectory estimation to work with a consistent camera interface without needing to handle camera discovery and hardware-specific testing themselves.

## Current Status

The development environment, repository structure, and software architecture have been established. The camera testing layer has now been implemented using OpenCV and Tkinter.

`camera_test.py` successfully discovers connected cameras, allows the user to select a camera, inspects its frame properties, measures approximate FPS, and provides a live preview. The stereo camera feed can also be inspected as separate left and right views.

The next development stage is to use the information obtained from camera testing to implement the reusable camera interface and proceed toward stereo image acquisition and camera calibration.
