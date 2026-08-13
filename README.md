# ProjectileTracking

An embedded AI and computer vision project focused on real-time projectile detection, 3D localization, and trajectory estimation using stereo vision and depth perception.

## Overview

The objective of this project is to develop a modular system capable of detecting and tracking fast-moving projectiles in real time. The system will use a stereo camera setup to estimate depth, calculate the projectile's position in three-dimensional space, and predict its trajectory. The project is designed with a modular architecture so that each component can be developed, tested, and improved independently.

## Planned Workflow

The development process is divided into the following stages:

- [x] Project planning and repository setup
- [x] Raspberry Pi development environment
- [x] Git and GitHub integration
- [x] Initial project structure
- [x] Camera setup and testing
- [x] Capture synchronized stereo images
- [x] Camera calibration
- [ ] Stereo rectification
- [ ] Depth estimation
- [ ] Projectile detection
- [ ] Projectile tracking
- [ ] 3D position estimation
- [ ] Trajectory prediction
- [ ] Performance optimization
- [ ] System testing and validation

## Project Structure

```
ProjectileTracking/
├── src/
│   ├── main.py
│   ├── camera.py
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

## Current Status

The development environment has been successfully configured on both the development machine and Raspberry Pi. The project repository, version control workflow, and software architecture have been established. The next milestone is integrating the stereo camera modules and implementing image acquisition.