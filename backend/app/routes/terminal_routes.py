import os
import signal
import asyncio
import json
import ptyprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict

router = APIRouter()

# Store active sessions: websocket -> pty_process
active_sessions: Dict[WebSocket, ptyprocess.PtyProcess] = {}

async def pty_to_websocket(pty: ptyprocess.PtyProcess, websocket: WebSocket):
    """Bridge: Reads from PTY and sends to WebSocket"""
    loop = asyncio.get_event_loop()
    try:
        while True:
            # Read from PTY in a non-blocking way
            # We use a small timeout to keep the loop responsive
            data = await loop.run_in_executor(None, pty.read, 1024)
            if not data:
                break
            await websocket.send_text(data.decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"PTY Read Error: {e}")
    finally:
        await websocket.close()

@router.websocket("/ws")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()
    
    # Configuration
    # We start in /app/data (shared volume)
    start_dir = os.path.abspath("data")
    if not os.path.exists(start_dir):
        os.makedirs(start_dir, exist_ok=True)

    # Spawn the shell
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["PS1"] = "\033[1;36mGeoSuite\033[0m:\033[1;34m\w\033[0m$ "
    
    try:
        pty = ptyprocess.PtyProcess.spawn(
            ["/bin/bash"],
            cwd=start_dir,
            env=env,
            dimensions=(24, 80)
        )
        active_sessions[websocket] = pty
        
        # Start the read loop
        read_task = asyncio.create_task(pty_to_websocket(pty, websocket))
        
        # Main loop: Receive from WebSocket and write to PTY
        while True:
            msg_str = await websocket.receive_text()
            try:
                # Check if it's a control message (like resize)
                msg_json = json.loads(msg_str)
                if msg_json.get("type") == "resize":
                    cols = msg_json.get("cols", 80)
                    rows = msg_json.get("rows", 24)
                    pty.setwinsize(rows, cols)
                    continue
            except json.JSONDecodeError:
                # Normal input (not JSON)
                if pty.isalive():
                    pty.write(msg_str.encode('utf-8'))
            
    except WebSocketDisconnect:
        print("Terminal WebSocket Disconnected")
    except Exception as e:
        print(f"Terminal Error: {e}")
    finally:
        # Cleanup
        if websocket in active_sessions:
            pty = active_sessions.pop(websocket)
            if pty.isalive():
                pty.terminate(force=True)
        if 'read_task' in locals():
            read_task.cancel()
