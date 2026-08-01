#!/usr/bin/env python3
"""Onshape Feature Studio injector — creates Feature Studio, injects code, commits, creates Part Studio."""

import argparse
import sys
import time
from pathlib import Path


def load_env_credentials():
    """Load ONSHAPE_EMAIL and ONSHAPE_PASSWORD from .env file."""
    email, password = None, None
    env_path = Path(".env")
    if env_path.exists():
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


def read_fs_file(path_str):
    """Read a FeatureScript file, return its content."""
    path = Path(path_str)
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        print(f"Error: File is empty: {path}", file=sys.stderr)
        sys.exit(1)
    return content


def part_studio_name(fs_path):
    """Extract Part Studio name from FeatureScript filename: hull.fs → Hull"""
    stem = Path(fs_path).stem
    return stem.replace("_", " ").title()


def ensure_playwright():
    """Import Playwright or exit with instructions."""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(1)


def login_or_wait(page, email, password, debug=False):
    """Auto-login with .env credentials or prompt for manual login."""
    url_lower = page.url.lower()
    title_lower = page.title().lower()
    is_login_page = ("login" in url_lower or "signin" in url_lower or
                     "sign in" in title_lower or "login" in title_lower)
    if debug:
        print(f"  Login check: url={page.url[:80]}, title='{page.title()}', is_login={is_login_page}")
    if not is_login_page:
        return

    if email and password:
        if debug:
            print("  Auto-login with credentials from .env...")
        try:
            email_selectors = ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="mail" i]']
            email_field = None
            for sel in email_selectors:
                try:
                    email_field = page.wait_for_selector(sel, timeout=3000)
                    if email_field:
                        break
                except Exception:
                    continue
            if not email_field:
                raise RuntimeError("Could not find email field")
            email_field.click()
            email_field.fill(email)
            next_btn = page.wait_for_selector('button:has-text("Next"), button:has-text("Continue")', timeout=5000)
            next_btn.click()
            time.sleep(2)
            try:
                pwd_field = page.wait_for_selector('input[type="password"]', timeout=10000)
                pwd_field.click()
                pwd_field.fill(password)
                time.sleep(0.5)
                signin_btn = page.wait_for_selector('button:has-text("Sign in"), button:has-text("Log in")', timeout=5000)
                signin_btn.click()
                time.sleep(5)
            except Exception:
                pass
            page.wait_for_load_state("load", timeout=30000)
            time.sleep(3)
            if "login" not in page.url.lower() and "sign in" not in page.title().lower():
                return
            print("  Auto-login failed. Falling back to manual.")
        except Exception as e:
            print(f"  Auto-login error: {e}")

    print("\n*** MANUAL LOGIN REQUIRED ***")
    print("Please log in to Onshape in the browser window.")
    for i in range(60):
        time.sleep(5)
        if "login" not in page.url.lower() and "signin" not in page.url.lower():
            print("Login detected — continuing.")
            break
        if i % 6 == 0 and i > 0:
            print(f"  Still waiting... ({i * 5}s)")


def click_add_element(page, element_type, debug=False):
    """Click '+' button and select element type (Part Studio, Feature Studio, etc.)."""
    add_selectors = ['[aria-label="Add element"]', '[data-testid="add-element"]', 'button:has-text("+")']
    for sel in add_selectors:
        try:
            page.click(sel, timeout=3000)
            break
        except Exception:
            continue
    time.sleep(1)
    
    # Try multiple selectors for the element type
    type_selectors = {
        "Feature Studio": ['#create-feature-studio-button', 'text=Feature Studio'],
        "Part Studio": ['#create-part-studio-button', 'text=Part Studio'],
    }
    selectors = type_selectors.get(element_type, [f'text={element_type}'])
    for sel in selectors:
        try:
            page.click(sel, timeout=3000)
            if debug:
                print(f"  Clicked: {sel}")
            break
        except Exception:
            continue
    time.sleep(2)


def rename_element(page, name, debug=False):
    """Rename the newly created element."""
    try:
        page.fill('input[aria-label="Element name"]', name)
        page.keyboard.press("Enter")
        time.sleep(1)
    except Exception:
        pass


def find_monaco_editor(page, debug=False):
    """Find Monaco editor textarea."""
    selectors = [".monaco-editor textarea", ".monaco-editor .inputarea", "textarea"]
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=5000)
            if el and el.is_visible():
                if debug:
                    print(f"  Found editor via: {sel}")
                return el
        except Exception:
            continue
    return None


def cmd_inject(args):
    """Create Feature Studio, inject code, commit, create Part Studio."""
    sync_playwright = ensure_playwright()
    email, password = load_env_credentials()
    code = read_fs_file(args.featurescript)
    ps_name = part_studio_name(args.featurescript)
    fs_name = ps_name + " Feature"

    user_data = Path(args.user_data_dir)
    user_data.mkdir(parents=True, exist_ok=True)

    print(f"Feature Studio: {fs_name}")
    print(f"Part Studio: {ps_name}")
    print(f"FeatureScript: {args.featurescript} ({len(code)} chars)")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data.resolve()),
            headless=args.headless,
            slow_mo=args.slow_mo,
            viewport={"width": 1920, "height": 1080},
        )
        page = browser.new_page()
        page.set_default_timeout(args.timeout)

        try:
            # [1] Open document
            print("\n[1/6] Opening Onshape document...")
            page.goto(args.document, wait_until="load")
            time.sleep(5)
            login_or_wait(page, email, password, args.debug)
            page.wait_for_load_state("load")
            time.sleep(3)

            # [2] Create Feature Studio
            print(f'[2/6] Creating Feature Studio "{fs_name}"...')
            try:
                page.click(f'text="{fs_name}"', timeout=5000)
                print("  Feature Studio already exists")
            except Exception:
                click_add_element(page, "Feature Studio", args.debug)
                rename_element(page, fs_name, args.debug)

            # [3] Inject FeatureScript
            print(f"[3/6] Injecting FeatureScript ({len(code)} chars)...")
            editor = find_monaco_editor(page, args.debug)
            if not editor:
                raise RuntimeError("Could not find FeatureScript editor")
            editor.click()
            time.sleep(0.5)
            page.keyboard.press("Meta+a")
            time.sleep(0.2)
            page.keyboard.press("Backspace")
            time.sleep(0.2)
            page.keyboard.insert_text(code)
            time.sleep(1)

            # [4] Commit
            print("[4/6] Committing Feature Studio...")
            try:
                page.click('button:has-text("Commit")', timeout=5000)
                time.sleep(3)
            except Exception:
                print("  Warning: could not find Commit button")

            # [5] Create Part Studio
            print(f'[5/6] Creating Part Studio "{ps_name}"...')
            try:
                page.click(f'text="{ps_name}"', timeout=5000)
                print("  Part Studio already exists")
            except Exception:
                click_add_element(page, "Part Studio", args.debug)
                rename_element(page, ps_name, args.debug)

            # [6] Screenshot
            screenshot = args.screenshot or f"parts/{Path(args.featurescript).stem}_result.png"
            print(f"[6/6] Screenshot → {screenshot}")
            time.sleep(2)
            page.screenshot(path=screenshot, full_page=False)

            print(f"\n✅ Feature Studio \"{fs_name}\" committed")
            print(f"✅ Part Studio \"{ps_name}\" created")
            print(f"   Custom feature should be available in Part Studio toolbar")

        except Exception as e:
            print(f"\n❌ Error: {e}", file=sys.stderr)
            if args.debug:
                import traceback
                traceback.print_exc()
                input("Press Enter to close browser...")
            sys.exit(1)
        finally:
            if not args.debug:
                browser.close()


def main():
    parser = argparse.ArgumentParser(description="Onshape Feature Studio injector")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inject = sub.add_parser("inject", help="Create Feature Studio and inject code")
    p_inject.add_argument("--document", required=True, help="Onshape document URL")
    p_inject.add_argument("--featurescript", required=True, help="Path to .fs file")
    p_inject.add_argument("--screenshot", help="Screenshot output path")
    p_inject.add_argument("--headless", action="store_true")
    p_inject.add_argument("--debug", action="store_true")
    p_inject.add_argument("--slow-mo", type=int, default=0)
    p_inject.add_argument("--user-data-dir", default="./.browser-data")
    p_inject.add_argument("--timeout", type=int, default=60000)
    p_inject.set_defaults(func=cmd_inject)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
