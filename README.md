# Network Topology Tool

## Overview
This tool automatically generates a hierarchical network topology from Cisco router configuration files, performs validation, analysis, load checks, and simulates network activity.

## Directory Structure
- `configs/` : Router configuration files (place config.dump files here)
- `modules/` : Python modules for parsing, validation, simulation, etc.
- `logs/` : Log files generated during execution
- `tests/` : Unit tests (to be expanded)
- `main.py` : Main CLI entry point

## Usage
1. Place your router config files under `configs/Rx/config.dump`.
2. Activate the virtual environment:  
   ```bash
   source venv/Scripts/activate  # Windows PowerShell: .\venv\Scripts\Activate.ps1
