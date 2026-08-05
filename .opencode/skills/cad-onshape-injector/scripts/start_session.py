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
SESSION_FILE = Path(".browser-session.json")


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


def load_env_credentials():
    """Load ONSHAPE_EMAIL and ONSHAPE_PASSWORD from .env file."""
    email, password = None, None
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        return None, None
    
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        if key == "ONSHAPE_EMAIL":
            email = val
        elif key == "ONSHAPE_PASSWORD":
            password = val
    
    return email, password


def auto_login(page, email, password):
    """Auto-login to Onshape using credentials.
    
    Args:
        page: Playwright page object
        email: Onshape email address
        password: Onshape password
    
    Returns:
        bool: True if login successful, False otherwise
    """
    if not email or not password:
        print("⚠️  No credentials provided. Manual login required.")
        return False
    
    print("🔐 Auto-login...")
    
    # Wait for page to be ready
    try:
        page.wait_for_load_state("load", timeout=10000)
    except:
        pass
    time.sleep(3)
    
    # Check if we're on login page
    current_url = page.url.lower()
    if "login" not in current_url and "signin" not in current_url:
        print("✅ Already logged in")
        return True
    
    try:
        # Find and fill email field
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[placeholder*="mail" i]',
            'input[id*="email" i]',
            'input[autocomplete="email"]',
        ]
        
        email_field = None
        for selector in email_selectors:
            try:
                email_field = page.wait_for_selector(selector, timeout=3000)
                if email_field:
                    break
            except:
                continue
        
        if not email_field:
            print("❌ Could not find email field")
            return False
        
        # Clear and fill email with proper timing
        email_field.click()
        time.sleep(0.5)
        email_field.fill('')
        time.sleep(0.5)
        email_field.fill(email)
        time.sleep(0.5)
        
        # Verify email was filled correctly
        filled_value = email_field.input_value()
        if filled_value != email:
            print(f"⚠️  Email field value mismatch")
            return False
        
        print("  ✅ Email filled")
        
        # Click Next/Continue button
        next_selectors = [
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Suivant")',
            'button[type="submit"]',
        ]
        
        next_clicked = False
        for selector in next_selectors:
            try:
                page.click(selector, timeout=3000)
                next_clicked = True
                break
            except:
                continue
        
        if not next_clicked:
            email_field.press('Enter')
        
        time.sleep(3)
        
        # Find and fill password field
        try:
            password_field = page.wait_for_selector('input[type="password"]', timeout=10000)
        except:
            print("❌ Could not find password field")
            return False
        
        if not password_field:
            print("❌ Could not find password field")
            return False
        
        # Clear and fill password with proper timing
        password_field.click()
        time.sleep(0.5)
        password_field.fill('')
        time.sleep(0.5)
        password_field.fill(password)
        time.sleep(0.5)
        print("  ✅ Password filled")
        
        # Click Sign in button
        signin_selectors = [
            'button:has-text("Sign in")',
            'button:has-text("Log in")',
            'button:has-text("Se connecter")',
            'button[type="submit"]',
        ]
        
        signin_clicked = False
        for selector in signin_selectors:
            try:
                page.click(selector, timeout=3000)
                signin_clicked = True
                break
            except:
                continue
        
        if not signin_clicked:
            password_field.press('Enter')
        
        # Wait for login to complete
        print("  ⏳ Waiting for login...")
        try:
            page.wait_for_load_state("load", timeout=30000)
        except:
            pass
        time.sleep(5)
        
        # Check if login succeeded
        current_url = page.url.lower()
        if "login" not in current_url and "signin" not in current_url:
            print("✅ Login successful")
            return True
        else:
            print("❌ Login failed")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {e}")
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
            # Cookies are already saved from previous sessions - no login needed!
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(Path(".browser-data").resolve()),
                headless=headless,
                slow_mo=100,
                viewport={"width": 1920, "height": 1080},
            )
            
            # Extract cookies immediately (they're already in .browser-data/)
            cookies = context.cookies()
            xsrf_token = None
            for cookie in cookies:
                if cookie['name'] == 'XSRF-TOKEN':
                    xsrf_token = cookie['value']
                    break
            
            if not xsrf_token:
                print("⚠️  Warning: XSRF-TOKEN not found.")
                print("   You may need to login manually once in the browser.")
            else:
                print("✅ XSRF token extracted from saved session")
            
            # Save session info (cookies + XSRF token)
            session_info = {
                "cookies": cookies,
                "xsrf_token": xsrf_token,
                "headless": headless,
                "started_at": time.time(),
                "pid": os.getpid(),
            }
            SESSION_FILE.write_text(json.dumps(session_info, indent=2))
            
            # Navigate to Onshape and check if login is needed
            page = context.pages[0] if context.pages else context.new_page()
            print("🌐 Navigating to Onshape...")
            try:
                page.goto("https://cad.onshape.com", wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)
                
                # Check if we're on login page
                current_url = page.url.lower()
                if "login" in current_url or "signin" in current_url:
                    print("🔐 Login page detected")
                    # Load credentials from .env
                    email, password = load_env_credentials()
                    if email and password:
                        if not auto_login(page, email, password):
                            print("⚠️  Auto-login failed. Please login manually.")
                            print("   Waiting 60 seconds for manual login...")
                            time.sleep(60)
                    else:
                        print("⚠️  No credentials in .env. Please login manually.")
                        print("   Waiting 60 seconds for manual login...")
                        time.sleep(60)
                else:
                    print("✅ Already logged in (session persisted)")
            except Exception as e:
                print(f"⚠️  Could not navigate to Onshape: {e}")
                print("   Session is still active, just no page loaded.")
            
            print("✅ Session started!")
            print(f"   Headless: {headless}")
            print(f"   User data: .browser-data/")
            print(f"   Session file: .browser-session.json")
            print()
            print("   Other scripts will automatically use the saved cookies")
            print("   from .browser-session.json for API REST calls.")
            print()
            print("   Press Ctrl+C to close the session.")
            print()
            
            # Keep alive until interrupted
            try:
                while True:
                    # Update cookies periodically (in case they change)
                    time.sleep(60)
                    cookies = context.cookies()
                    for cookie in cookies:
                        if cookie['name'] == 'XSRF-TOKEN':
                            xsrf_token = cookie['value']
                            break
                    session_info["cookies"] = cookies
                    session_info["xsrf_token"] = xsrf_token
                    SESSION_FILE.write_text(json.dumps(session_info, indent=2))
            except KeyboardInterrupt:
                print("\n\n🛑 Closing session...")
            finally:
                context.close()
                SESSION_FILE.unlink(missing_ok=True)
                LOCK_FILE.unlink(missing_ok=True)
                print("✅ Session closed.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        SESSION_FILE.unlink(missing_ok=True)
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
