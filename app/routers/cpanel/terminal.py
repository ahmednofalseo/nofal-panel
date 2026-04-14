"""
cPanel Web Terminal Router
Provides a browser-based terminal for each user via WebSocket + subprocess
"""
import asyncio
import os
import pty
import fcntl
import struct
import termios
import subprocess
import json
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from app.auth import get_cpanel_user, decode_token
from app.templating import templates

router = APIRouter(prefix="/cpanel", tags=["cpanel-terminal"])


@router.get("/terminal", response_class=HTMLResponse)
async def terminal_page(request: Request, user=Depends(get_cpanel_user)):
    return templates.TemplateResponse("cpanel/terminal.html", {
        "request": request,
        "user": user,
        "page": "terminal"
    })


@router.websocket("/terminal/ws")
async def terminal_ws(websocket: WebSocket):
    """
    WebSocket endpoint for interactive terminal.
    Spawns a restricted shell for the user using their Linux account.
    Falls back to a safe shell if user doesn't exist on system.
    """
    await websocket.accept()

    # Authenticate via cookie
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.send_text("\r\n\x1b[31m[ERROR] Not authenticated.\x1b[0m\r\n")
        await websocket.close()
        return

    payload = decode_token(token)
    if not payload:
        await websocket.send_text("\r\n\x1b[31m[ERROR] Invalid session.\x1b[0m\r\n")
        await websocket.close()
        return

    username = payload.get("sub", "")
    role = payload.get("role", "user")

    # Determine shell command
    if role == "admin":
        # Admin gets bash (still restricted to their session)
        shell_cmd = ["/bin/bash", "--login"]
        shell_user = None
    else:
        # Try to run as the Linux user if they exist
        home_dir = f"/home/{username}"
        if os.path.exists(home_dir):
            shell_cmd = ["sudo", "-u", username, "/bin/bash", "--login"]
            shell_user = username
        else:
            # Restricted fallback shell - simulate environment
            shell_cmd = ["/bin/bash", "--restricted", "--norc"]
            shell_user = None

    # Create PTY
    master_fd, slave_fd = pty.openpty()

    try:
        env = os.environ.copy()
        env.update({
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "HOME": f"/home/{username}" if role != "admin" else "/root",
            "USER": username,
            "LOGNAME": username,
            "SHELL": "/bin/bash",
            "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin",
            "LANG": "en_US.UTF-8",
        })

        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            preexec_fn=os.setsid,
            close_fds=True,
        )
    except Exception as e:
        # Last resort fallback
        try:
            process = await asyncio.create_subprocess_exec(
                "/bin/sh",
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                preexec_fn=os.setsid,
            )
        except Exception as e2:
            await websocket.send_text(f"\r\n\x1b[31m[ERROR] Could not start terminal: {e2}\x1b[0m\r\n")
            await websocket.close()
            os.close(master_fd)
            os.close(slave_fd)
            return

    os.close(slave_fd)

    # Set non-blocking
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    async def read_output():
        """Read from PTY and send to WebSocket"""
        loop = asyncio.get_event_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, _read_fd, master_fd)
                if data:
                    await websocket.send_bytes(data)
                else:
                    await asyncio.sleep(0.01)
            except (OSError, WebSocketDisconnect):
                break

    def _read_fd(fd):
        try:
            return os.read(fd, 4096)
        except (OSError, BlockingIOError):
            return b""

    read_task = asyncio.ensure_future(read_output())

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive(), timeout=300)
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_text("")
                except Exception:
                    break
                continue

            if "bytes" in raw:
                data = raw["bytes"]
                # Handle resize message (JSON)
                if data.startswith(b"\x01"):
                    try:
                        msg = json.loads(data[1:])
                        if msg.get("type") == "resize":
                            cols = msg.get("cols", 80)
                            rows = msg.get("rows", 24)
                            _resize_pty(master_fd, cols, rows)
                    except Exception:
                        pass
                else:
                    os.write(master_fd, data)
            elif "text" in raw:
                text = raw["text"]
                if text:
                    try:
                        msg = json.loads(text)
                        if msg.get("type") == "resize":
                            cols = msg.get("cols", 80)
                            rows = msg.get("rows", 24)
                            _resize_pty(master_fd, cols, rows)
                    except Exception:
                        os.write(master_fd, text.encode("utf-8"))
            elif raw.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        read_task.cancel()
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
        try:
            os.close(master_fd)
        except Exception:
            pass


def _resize_pty(fd, cols, rows):
    """Send resize signal to PTY"""
    try:
        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, size)
    except Exception:
        pass
