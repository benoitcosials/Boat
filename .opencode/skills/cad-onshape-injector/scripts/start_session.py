#!/usr/bin/env python3
"""Start and manage a persistent Onshape browser session.

This script launches a Chromium browser that stays open for the entire design
session. The browser uses a persistent user data directory (.browser-data/) so
login state survives between runs.

Other scripts use the OnshapeSession class which automatically reuses the saved
cookies from .browser-data/ for API REST calls - no need to launch a new browser.

Usage:
    # Start a new session (opens browser window)
    .venv/bin/python3 start_session.py

    # Start in headless mode (no visible window)
    .venv/bin/python3 start_session.py --headless

    # Close the session
    .venv/bin/python3 start_session.py --close

    # Check if a session is running
    .venv/bin/python3 start_session.py --status

The browser stays open until you explicitly close it or press Ctrl+C.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

LOCK_FILE = Path(".browser-session.lock")


def is_session_running() -> bool:
    """Check if a session is currently running."""
    if not LOCK_FILE.exists():
        return False
    
    try:
        data = json.loads(LOCK_FILE.read_text())
        pid = data.get("pid")
        if pid:
            os.kill(pid, 0)
            return True
    except (ProcessLookupError, json.JSONDecodeError, KeyError):
        LOCK_FILE.unlink(missing_ok=True)
    
    return False


def start_session(headless: bool = False) -> None:
    """Start a new persistent browser session."""
    if is_session_running():
        print("❌ A session is already running.")
        print("   Use --status to check, or --close to stop it.")
        sys.exit(1)
    
    print("🌐 Starting persistent Onshape session...")
    print("   Browser will stay open until you close it.")
    print()
    
    # Write lock file with PID
    LOCK_FILE.write_text(json.dumps({"pid": os.getpid()}))
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Launch persistent context (keeps login state in .browser-data/)
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(Path(".browser-data").resolve()),
                headless=headless,
                slow_mo=100,
                viewport={"width": 1920, "height": 1080},
            )
            
            # Navigate to Onshape
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://cad.onshape.com/documents", wait_until="load")
            
            print("✅ Session started!")
            print(f"   Headless: {headless}")
            print(f"   User data: .browser-data/")
            print()
            print("   Other scripts will automatically use the saved cookies")
            print("   from .browser-data/ for API REST calls.")
            print()
            print("   Press Ctrl+C to close the session.")
            print()
            
            # Keep alive until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n🛑 Closing session...")
            finally:
                context.close()
                LOCK_FILE.unlink(missing_ok=True)
                print("✅ Session closed.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        LOCK_FILE.unlink(missing_ok=True)
        sys.exit(1)


def close_session() -> None:
    """Close the running session."""
    if not is_session_running():
        print("✅ No session is running.")
        return
    
    try:
        data = json.loads(LOCK_FILE.read_text())
        pid = data.get("pid")
        if pid:
            print(f"🛑 Sending SIGTERM to session (PID {pid})...")
            os.kill(pid, signal.SIGTERM)
            
            for _ in range(10):
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    print("✅ Session closed.")
                    return
            
            print("⚠️  Session did not exit gracefully. Sending SIGKILL...")
            os.kill(pid, signal.SIGKILL)
            print("✅ Session killed.")
    except Exception as e:
        print(f"❌ Error closing session: {e}")
    finally:
        LOCK_FILE.unlink(missing_ok=True)


def show_status() -> None:
    """Show the current session status."""
    if not is_session_running():
        print("❌ No session is running.")
        return
    
    try:
        data = json.loads(LOCK_FILE.read_text())
        pid = data.get("pid")
        started = data.get("started_at")
        
        print("✅ Session is running:")
        print(f"   PID: {pid}")
        if started:
            duration = time.time() - started
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"   Duration: {minutes}m {seconds}s")
        print(f"   User data: .browser-data/")
    except Exception as e:
        print(f"❌ Error reading session info: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage persistent Onshape browser session")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no visible window)")
    parser.add_argument("--close", action="store_true", help="Close the running session")
    parser.add_argument("--status", action="store_true", help="Show session status")
    
    args = parser.parse_args()
    
    if args.close:
        close_session()
    elif args.status:
        show_status()
    else:
        start_session(headless=args.headless)


if __name__ == "__main__":
    main()
