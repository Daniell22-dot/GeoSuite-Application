import os
import signal
import asyncio
import json
import ptyprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Optional

from app.config import settings
from app.database import get_db
from app.services.auth_service import auth_service

router = APIRouter()

active_sessions: Dict[WebSocket, ptyprocess.PtyProcess] = {}


async def pty_to_websocket(pty: ptyprocess.PtyProcess, websocket: WebSocket):
    """Bridge: Reads from PTY and sends to WebSocket"""
    loop = asyncio.get_running_loop()
    try:
        while True:
            data = await loop.run_in_executor(None, pty.read, 1024)
            if not data:
                break
            await websocket.send_text(data.decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"PTY Read Error: {e}")
    finally:
        await websocket.close()


@router.websocket("/ws")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()

    db: Optional[Session] = None
    if settings.TERMINAL_AUTH_REQUIRED:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        db = next(get_db())
        user = auth_service.get_current_user(db, token)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    start_dir = os.path.abspath("data")
    if not os.path.exists(start_dir):
        os.makedirs(start_dir, exist_ok=True)

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["PS1"] = "\033[1;36mGeoSuite\033[0m:\033[1;34m\w\033[0m$ "

    pty = None
    read_task = None
    try:
        pty = ptyprocess.PtyProcess.spawn(
            [settings.TERMINAL_SHELL],
            cwd=start_dir,
            env=env,
            dimensions=(24, 80),
        )
        active_sessions[websocket] = pty

        read_task = asyncio.create_task(pty_to_websocket(pty, websocket))

        while True:
            msg_str = await websocket.receive_text()
            try:
                msg_json = json.loads(msg_str)
                if msg_json.get("type") == "resize":
                    cols = msg_json.get("cols", 80)
                    rows = msg_json.get("rows", 24)
                    pty.setwinsize(rows, cols)
                    continue
            except json.JSONDecodeError:
                if pty.isalive():
                    pty.write(msg_str.encode("utf-8"))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Terminal Error: {e}")
    finally:
        if read_task:
            read_task.cancel()
        if websocket in active_sessions:
            pty = active_sessions.pop(websocket)
            if pty is not None and pty.isalive():
                pty.terminate(force=True)
        if db is not None:
            db.close()