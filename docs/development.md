# Development Environment

## Supported Linux Userspace

Ubuntu 24.04

## Toolchain

- Python 3.12
- uv
- Node.js 22
- ROS 2 Jazzy
- Gazebo Harmonic

## Arch Linux

ROS development runs inside an Ubuntu 24.04 Distrobox.

## Windows

ROS development runs inside WSL2 Ubuntu 24.04.

Repositories should be cloned into the WSL Linux filesystem,
not `/mnt/c`.

## Python Setup

```bash
uv sync --all-packages --dev
make check
```