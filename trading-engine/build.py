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
    """Get the Tauri-compatible target triple for the current platform.
    On Windows, PyInstaller will add .exe to the output name automatically."""
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
    # Ensure loguru and other deps are installed so PyInstaller can bundle them
    req_path = os.path.join(SCRIPT_DIR, "requirements.txt")
    if os.path.isfile(req_path):
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", req_path],
            cwd=ROOT_DIR,
            check=True,
        )

    target = get_target_triple()
    output_name = f"trading-engine-{target}"
    output_dir = os.path.join(ROOT_DIR, "src-tauri", "binaries")

    os.makedirs(output_dir, exist_ok=True)

    # Hidden imports: everything required at start/trading - all dependencies embedded into exe
    # - loguru: common.py uses loguru for logging
    # - ibapi: BOT, common, tws_api_client, order_manager use client/wrapper/contract/order/execution/ticktype/utils
    # - data: BOT uses Indicators (yfinance, pandas, numpy), tws_api_client uses pandas
    # - multiprocessing: BOT uses Process, Pool
    # - shutil: trading_engine copies expiryStrike.json when frozen
    hidden_imports = [
        "engine",
        "engine.trading_engine",
        "engine.models",
        "protocol",
        "protocol.handler",
        "protocol.emitter",
        "protocol.messages",
        "loguru",
        "logging",
        "ibapi",
        "ibapi.client",
        "ibapi.wrapper",
        "ibapi.contract",
        "ibapi.order",
        "ibapi.execution",
        "ibapi.ticktype",
        "ibapi.utils",
        "pandas",
        "numpy",
        "yfinance",
        "pandas_ta",
        "numba",
        "numba.core",
        "llvmlite",
        "pytz",
        "sqlite3",
        "pathlib",
        "dataclasses",
        "queue",
        "concurrent.futures",
        "multiprocessing",
        "multiprocessing.spawn",
        "shutil",
        "json",
        "bisect",
        "threading",
        "copy",
        "typing",
    ]

    # Project-root modules (BOT.py, common, etc.) — bundled so sidecar finds them in _MEIPASS
    data_additions = [
        f"{ROOT_DIR}/common.py{os.pathsep}.",
        f"{ROOT_DIR}/BOT.py{os.pathsep}.",
        f"{ROOT_DIR}/tws_api_client.py{os.pathsep}.",
        f"{ROOT_DIR}/order_manager.py{os.pathsep}.",
        f"{ROOT_DIR}/data_access.py{os.pathsep}.",
        f"{ROOT_DIR}/Indicators.py{os.pathsep}.",
        f"{ROOT_DIR}/logger.py{os.pathsep}.",
        # Empty strike file so BOT never hits "[Errno 2] No such file or directory: expiryStrike.json"
        f"{SCRIPT_DIR}/expiryStrike.json{os.pathsep}.",
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

    # Ensure PyInstaller finds engine/protocol when analyzing (packaged exe runs from different cwd)
    cmd.extend(["--paths", SCRIPT_DIR])

    # Collect full packages so behavior matches Mac (all submodules available)
    cmd.extend(["--collect-submodules", "logging"])
    cmd.extend(["--collect-submodules", "ibapi"])
    cmd.extend(["--collect-submodules", "loguru"])

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
