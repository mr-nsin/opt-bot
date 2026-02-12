#!/usr/bin/env python3
"""
Build script for the trading engine sidecar.
Uses PyInstaller to create a standalone executable that Tauri can run.
"""

import os
import sys
import platform
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)


def get_target_triple():
    """Get the Tauri-compatible target triple for the current platform."""
    machine = platform.machine().lower()
    system = platform.system().lower()

    if system == "darwin":
        arch = "aarch64" if machine == "arm64" else "x86_64"
        return f"{arch}-apple-darwin"
    elif system == "windows":
        arch = "x86_64" if machine in ("amd64", "x86_64") else machine
        return f"{arch}-pc-windows-msvc"
    elif system == "linux":
        arch = "x86_64" if machine in ("amd64", "x86_64") else machine
        return f"{arch}-unknown-linux-gnu"
    else:
        return f"{machine}-{system}"


def build():
    """Build the trading engine as a PyInstaller executable."""
    target = get_target_triple()
    output_name = f"trading-engine-{target}"
    output_dir = os.path.join(ROOT_DIR, "src-tauri", "binaries")

    os.makedirs(output_dir, exist_ok=True)

    # Collect hidden imports for ibapi and other modules
    hidden_imports = [
        "ibapi",
        "ibapi.client",
        "ibapi.wrapper",
        "ibapi.contract",
        "ibapi.order",
        "ibapi.execution",
        "pandas",
        "numpy",
        "yfinance",
        "pytz",
    ]

    # Also include the existing project modules
    data_additions = [
        f"{ROOT_DIR}/common.py{os.pathsep}.",
        f"{ROOT_DIR}/tws_api_client.py{os.pathsep}.",
        f"{ROOT_DIR}/order_manager.py{os.pathsep}.",
        f"{ROOT_DIR}/data_access.py{os.pathsep}.",
        f"{ROOT_DIR}/Indicators.py{os.pathsep}.",
        f"{ROOT_DIR}/logger.py{os.pathsep}.",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", output_name,
        "--distpath", output_dir,
        "--specpath", os.path.join(SCRIPT_DIR, "build"),
        "--workpath", os.path.join(SCRIPT_DIR, "build", "work"),
        "--clean",
        "--noconfirm",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    for data in data_additions:
        cmd.extend(["--add-data", data])

    cmd.append(os.path.join(SCRIPT_DIR, "main.py"))

    print(f"Building: {output_name}")
    print(f"Output: {output_dir}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)

    if result.returncode == 0:
        print(f"\nBuild successful! Binary: {os.path.join(output_dir, output_name)}")
    else:
        print(f"\nBuild failed with exit code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
