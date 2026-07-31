import os
import mmap
import struct
import tempfile
import time
from typing import List, Dict, Any

# Header format: magic (4s), version (I), timestamp (d), pos_count (i), daily_pnl (d), unrealized_pnl (d), realized_pnl (d), padding (20x)
HEADER_FORMAT = "<4s I d i d d d 20x"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 64 bytes

# Position entry format (exactly 256 bytes):
# symbol (32s), strike (d), right (8s), expiry (16s), quantity (i), avg_price (d), current_price (d),
# pnl (d), pnl_percent (d), bid (d), ask (d), last (d), stoploss (d), profit (d),
# entry_time (32s), flags (B), padding (83x)
POSITION_FORMAT = "<32s d 8s 16s i d d d d d d d d d 32s B 83x"
POSITION_SIZE = struct.calcsize(POSITION_FORMAT)  # 256 bytes

MAX_POSITIONS = 200
FILE_SIZE = HEADER_SIZE + (POSITION_SIZE * MAX_POSITIONS)  # 64 + (256 * 200) = 51,264 bytes

class MmapIpcWriter:
    def __init__(self):
        self.temp_dir = os.path.join(tempfile.gettempdir(), "quantdrift")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.file_path = os.path.join(self.temp_dir, "quantdrift_positions.mmap")
        
        # Open file and map it
        self.file = open(self.file_path, "a+b")
        # Ensure file is of correct size
        if self.file.tell() < FILE_SIZE:
            self.file.write(b"\x00" * FILE_SIZE)
            self.file.flush()
        
        self.mmap = mmap.mmap(self.file.fileno(), FILE_SIZE)
        
    def close(self):
        try:
            self.mmap.close()
            self.file.close()
        except Exception:
            pass

    def write_snapshot(self, positions: List[Dict[str, Any]], daily_pnl: float, unrealized_pnl: float, realized_pnl: float):
        """Write the positions list and PNL metrics to shared memory in binary format."""
        pos_count = min(len(positions), MAX_POSITIONS)
        timestamp = time.time()
        
        # 1. Pack Header
        # magic (4s), version (I), timestamp (d), pos_count (i), daily_pnl (d), unrealized_pnl (d), realized_pnl (d)
        header_bytes = struct.pack(
            HEADER_FORMAT,
            b"QDPB",
            1,
            timestamp,
            pos_count,
            daily_pnl,
            unrealized_pnl,
            realized_pnl
        )
        
        # Write header to mmap
        self.mmap[0:HEADER_SIZE] = header_bytes
        
        # 2. Pack Positions
        offset = HEADER_SIZE
        for i in range(pos_count):
            pos = positions[i]
            
            # Helper to encode strings safely
            def enc(val: Any, length: int) -> bytes:
                s = str(val or "")
                return s.encode("utf-8")[:length].ljust(length, b"\x00")
            
            # Resolve flags
            # bit 0: trailing_active, bit 1: has_ib_pnl
            flags = 0
            if pos.get("trailing_active") or pos.get("trailing_active") == "True":
                flags |= 1
            if pos.get("has_ib_pnl"):
                flags |= 2
                
            pos_bytes = struct.pack(
                POSITION_FORMAT,
                enc(pos.get("symbol"), 32),
                float(pos.get("strike", 0.0) or 0.0),
                enc(pos.get("right"), 8),
                enc(pos.get("expiry"), 16),
                int(pos.get("quantity") or pos.get("qty") or 0),
                float(pos.get("avg_price", 0.0) or 0.0),
                float(pos.get("current_price", 0.0) or 0.0),
                float(pos.get("pnl", 0.0) or 0.0),
                float(pos.get("pnl_percent", 0.0) or 0.0),
                float(pos.get("bid", -1.0) or -1.0),
                float(pos.get("ask", -1.0) or -1.0),
                float(pos.get("last", -1.0) or -1.0),
                float(pos.get("stoploss_price", 0.0) or 0.0),
                float(pos.get("profit_price", 0.0) or 0.0),
                enc(pos.get("entry_time"), 32),
                flags
            )
            
            self.mmap[offset : offset + POSITION_SIZE] = pos_bytes
            offset += POSITION_SIZE
            
        # Flush to OS memory manager
        self.mmap.flush()
