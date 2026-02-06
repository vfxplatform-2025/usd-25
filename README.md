# usd 25.11 (Major v25)

VFX Platform 2025 compatible build package for usd.

## Package Information

- **Package Name**: usd
- **Version**: 25.11
- **Major Version**: 25
- **Repository**: vfxplatform-2025/usd-25
- **Description**: Universal Scene Description (OpenUSD) with Arnold plugin support

## Build Instructions

```bash
rez-build -i
```

## Package Structure

```
usd/
├── 25.11/
│   ├── package.py      # Rez package configuration
│   ├── rezbuild.py     # Build script
│   ├── get_source.sh   # Source download script (if applicable)
│   └── README.md       # This file
```

## Installation

When built with `install` target, installs to: `/core/Linux/APPZ/packages/usd/25.11`

## Version Strategy

This repository contains **Major Version 25** of usd. Different major versions are maintained in separate repositories:

- Major v25: `vfxplatform-2025/usd-25`

## VFX Platform 2025

This package is part of the VFX Platform 2025 initiative, ensuring compatibility across the VFX industry standard software stack.
