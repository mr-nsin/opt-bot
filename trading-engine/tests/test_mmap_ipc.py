import os
import struct
import tempfile
import time
import pytest
from protocol.mmap_ipc import MmapIpcWriter, HEADER_FORMAT, HEADER_SIZE, POSITION_FORMAT, POSITION_SIZE, FILE_SIZE

def test_mmap_ipc_flow():
    # Instantiate writer
    writer = MmapIpcWriter()
    
    # Assert file size
    assert os.path.exists(writer.file_path)
    assert os.path.getsize(writer.file_path) == FILE_SIZE
    
    # Mock data
    positions = [
        {
            "symbol": "AAPL260731C00200000",
            "strike": 200.0,
            "right": "C",
            "expiry": "20260731",
            "quantity": 10,
            "avg_price": 5.25,
            "current_price": 6.10,
            "pnl": 85.0,
            "pnl_percent": 16.19,
            "bid": 6.05,
            "ask": 6.15,
            "last": 6.10,
            "stoploss_price": 4.50,
            "profit_price": 8.00,
            "entry_time": "2026-07-31T10:00:00",
            "trailing_active": True,
            "has_ib_pnl": False
        },
        {
            "symbol": "TSLA260731P00180000",
            "strike": 180.0,
            "right": "P",
            "expiry": "20260731",
            "quantity": -5,
            "avg_price": 3.40,
            "current_price": 3.00,
            "pnl": 20.0,
            "pnl_percent": 11.76,
            "bid": 2.95,
            "ask": 3.05,
            "last": 3.00,
            "stoploss_price": 4.00,
            "profit_price": 2.00,
            "entry_time": "2026-07-31T10:15:00",
            "trailing_active": False,
            "has_ib_pnl": True
        }
    ]
    
    daily_pnl = 105.0
    unrealized_pnl = 200.0
    realized_pnl = -95.0
    
    # Write snapshot to shared memory
    writer.write_snapshot(positions, daily_pnl, unrealized_pnl, realized_pnl)
    
    # Read back the bytes from the file directly to verify
    with open(writer.file_path, "rb") as f:
        data = f.read()
        
    # Check header
    header = struct.unpack(HEADER_FORMAT, data[0:HEADER_SIZE])
    assert header[0] == b"QDPB"
    assert header[1] == 1  # version
    assert header[2] > 0.0  # timestamp
    assert header[3] == 2  # pos_count
    assert header[4] == daily_pnl
    assert header[5] == unrealized_pnl
    assert header[6] == realized_pnl
    
    # Check Position 1
    offset = HEADER_SIZE
    pos1 = struct.unpack(POSITION_FORMAT, data[offset : offset + POSITION_SIZE])
    assert pos1[0].decode("utf-8").strip("\x00") == "AAPL260731C00200000"
    assert pos1[1] == 200.0
    assert pos1[2].decode("utf-8").strip("\x00") == "C"
    assert pos1[3].decode("utf-8").strip("\x00") == "20260731"
    assert pos1[4] == 10
    assert pos1[5] == 5.25
    assert pos1[6] == 6.10
    assert pos1[7] == 85.0
    assert pos1[8] == 16.19
    assert pos1[9] == 6.05
    assert pos1[10] == 6.15
    assert pos1[11] == 6.10
    assert pos1[12] == 4.50
    assert pos1[13] == 8.00
    assert pos1[14].decode("utf-8").strip("\x00") == "2026-07-31T10:00:00"
    assert pos1[15] == 1  # flags: bit 0 set (trailing_active)
    
    # Check Position 2
    offset += POSITION_SIZE
    pos2 = struct.unpack(POSITION_FORMAT, data[offset : offset + POSITION_SIZE])
    assert pos2[0].decode("utf-8").strip("\x00") == "TSLA260731P00180000"
    assert pos2[1] == 180.0
    assert pos2[2].decode("utf-8").strip("\x00") == "P"
    assert pos2[3].decode("utf-8").strip("\x00") == "20260731"
    assert pos2[4] == -5
    assert pos2[5] == 3.40
    assert pos2[6] == 3.00
    assert pos2[7] == 20.0
    assert pos2[8] == 11.76
    assert pos2[9] == 2.95
    assert pos2[10] == 3.05
    assert pos2[11] == 3.00
    assert pos2[12] == 4.00
    assert pos2[13] == 2.00
    assert pos2[14].decode("utf-8").strip("\x00") == "2026-07-31T10:15:00"
    assert pos2[15] == 2  # flags: bit 1 set (has_ib_pnl)
    
    # Clean up
    writer.close()
