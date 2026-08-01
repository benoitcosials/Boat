#!/usr/bin/env python3
"""Onshape workspace manager — branch-based FeatureScript injection via Playwright.

Usage:
    inject  — Inject FeatureScript into a Part Studio on ai/main branch
    merge   — Merge ai/main into main (with user approval)
    analyze — Compare feature trees between branches
    list-parts — Show mapping from parts/*.fs to Part Studios

Run with --help on any subcommand for details.
"""

import argparse
import sys
import time
from pathlib import Path


# ─── helpers ──────────────────────────────────────────────────────────────

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
        print(
            "Playwright not installed. Run: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)


def login_or_wait(page, email, password, debug=False):
    """Auto-login with .env credentials or prompt for manual login."""
    # Detect login page via URL or page title
    url_lower = page.url.lower()
    title_lower = page.title().lower()
    is_login_page = (
        "login" in url_lower or "signin" in url_lower or
        "sign in" in title_lower or "login" in title_lower
    )
    if debug:
        print(f"  Login check: url={page.url[:80]}, title='{page.title()}', is_login={is_login_page}")
        print(f"  Credentials: email={'set' if email else 'None'}, password={'set' if password else 'None'}")
    if not is_login_page:
        return

    if email and password:
        if debug:
            print("  Auto-login with credentials from .env...")
        try:
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="mail" i]',
                'input[placeholder*="Email"]',
                'input[aria-label*="email" i]',
                'input[id*="email" i]',
            ]
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
            next_btn = page.wait_for_selector(
                'button:has-text("Next"), button:has-text("Continue"), button[type="submit"], .continue-button',
                timeout=5000,
            )
            next_btn.click()
            time.sleep(2)
            try:
                pwd_field = page.wait_for_selector('input[type="password"]', timeout=10000)
                pwd_field.click()
                pwd_field.fill(password)
                time.sleep(0.5)
                signin_btn = page.wait_for_selector(
                    'button:has-text("Sign in"), button:has-text("Log in"), button[type="submit"]',
                    timeout=5000,
                )
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


def find_editor(page, debug=False):
    """Find and return the FeatureScript editor element."""
    page.screenshot(path="tmp/find_editor_debug.png")
    if debug:
        print("  Debug screenshot saved to tmp/find_editor_debug.png")
    
    # Dump all visible text content to understand what's on screen
    try:
        page_text = page.evaluate("""
            () => document.body.innerText.slice(0, 3000)
        """)
        if debug:
            print("  Page text content:", page_text[:2000])
    except Exception:
        pass
    
    # Dump all textarea and code editor elements
    try:
        editors = page.evaluate("""
            () => {
                const candidates = [];
                // Textareas
                document.querySelectorAll('textarea').forEach(el => {
                    candidates.push({tag: 'textarea', class: el.className?.slice(0, 60), visible: el.offsetParent !== null});
                });
                // Code editors (Monaco, CodeMirror, Ace, etc.)
                document.querySelectorAll('.monaco-editor, .CodeMirror, .ace_editor, [class*="editor"], [class*="Editor"]').forEach(el => {
                    candidates.push({tag: el.tagName, class: el.className?.slice(0, 60), visible: el.offsetParent !== null});
                });
                return candidates;
            }
        """)
        import json
        if debug:
            print("  Editor candidates:", json.dumps(editors, indent=2))
    except Exception:
        pass
    
    selectors = [
        ".monaco-editor textarea",
        ".monaco-editor .inputarea",
        "textarea.feature-script-editor",
        '[data-testid="featurescript-textarea"]',
        "textarea",
        ".CodeMirror textarea",
        ".ace_text-input",
        '[class*="editor"] textarea',
        '[class*="Editor"] textarea',
        '[role="textbox"]',
        '[contenteditable="true"]',
    ]
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=3000)
            if el and el.is_visible():
                if debug:
                    print(f"  Found editor via: {sel}")
                return el
        except Exception:
            continue
    raise RuntimeError("Could not find FeatureScript editor. Onshape UI may have changed.")


def click_accept(page, debug=False):
    """Click the Accept/OK button in FeatureScript dialog."""
    selectors = [
        'button:has-text("Accept")',
        'button:has-text("OK")',
        '[data-testid="accept-button"]',
    ]
    for sel in selectors:
        try:
            btn = page.wait_for_selector(sel, timeout=3000)
            if btn and btn.is_visible():
                btn.click()
                return True
        except Exception:
            continue
    return False


def wait_compilation(page, timeout=30000):
    """Wait for FeatureScript compilation. Returns (success: bool, errors: list)."""
    try:
        page.wait_for_selector(".feature-status-icon.success", timeout=timeout)
        return True, []
    except Exception:
        errors = []
        for sel in [".feature-error-message", '[data-status="error"]']:
            for el in page.query_selector_all(sel):
                text = el.text_content()
                if text and text.strip():
                    errors.append(text.strip())
        return False, errors


# ─── subcommands ───────────────────────────────────────────────────────────

def cmd_inject(args):
    """Inject FeatureScript into a Part Studio on ai/main branch."""
    sync_playwright = ensure_playwright()
    email, password = load_env_credentials()
    code = read_fs_file(args.featurescript)
    ps_name = part_studio_name(args.featurescript)

    user_data = Path(args.user_data_dir)
    user_data.mkdir(parents=True, exist_ok=True)

    print(f"Part Studio: {ps_name}")
    print(f"FeatureScript: {args.featurescript} ({len(code)} chars)")
    print(f"Branch: ai/main")

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
            # [1] Navigate to document
            print("\n[1/6] Opening Onshape document...")
            page.goto(args.document, wait_until="load")
            time.sleep(5)  # Wait for SPA to fully render
            login_or_wait(page, email, password, args.debug)
            page.wait_for_load_state("load")
            time.sleep(3)

            # [2] Switch to ai/main branch
            print("[2/6] Switching to ai/main branch...")
            # Click branch dropdown, select or create ai/main
            try:
                page.click('[aria-label="Branch"], [data-testid="branch-selector"]', timeout=5000)
            except Exception:
                print("  Warning: could not find branch selector — assuming ai/main exists")
            time.sleep(1)

            # [3] Find or create Part Studio
            print(f'[3/6] Selecting Part Studio "{ps_name}"...')
            try:
                page.click(f'text="{ps_name}"', timeout=5000)
            except Exception:
                # Create new Part Studio — click the "+" button at bottom-left
                print(f'  Creating Part Studio "{ps_name}"...')
                # First, close any open popups with Escape
                page.keyboard.press("Escape")
                time.sleep(1)
                
                # Click the "+" button to add new element
                add_element_selectors = [
                    '[aria-label="Add element"]',
                    '[data-testid="add-element"]',
                    'button:has-text("+")',
                    '.os-tab-add',
                    '.element-tab-add',
                ]
                clicked_add = False
                for sel in add_element_selectors:
                    try:
                        page.click(sel, timeout=3000)
                        clicked_add = True
                        if args.debug:
                            print(f"  Clicked add element: {sel}")
                        break
                    except Exception:
                        continue
                
                if not clicked_add:
                    # Try clicking the "+" icon at bottom-left of tab bar
                    try:
                        page.click('.tab-bar .add-button, [class*="tab"] [class*="add"]', timeout=3000)
                        clicked_add = True
                    except Exception:
                        pass
                
                if not clicked_add:
                    raise RuntimeError("Could not find '+' button to add new element")
                
                time.sleep(1)
                
                # Select "Part Studio" from the menu
                ps_selectors = [
                    'text=Create Part Studio',
                    'text="Create Part Studio"',
                    'li:has-text("Create Part Studio")',
                    '[data-option="Create Part Studio"]',
                ]
                for sel in ps_selectors:
                    try:
                        page.click(sel, timeout=3000)
                        if args.debug:
                            print(f"  Selected Part Studio: {sel}")
                        break
                    except Exception:
                        continue
                
                time.sleep(2)
                
                # Rename the new Part Studio
                try:
                    page.fill('input[aria-label="Element name"], input[placeholder*="name"]', ps_name)
                    page.keyboard.press("Enter")
                    time.sleep(1)
                except Exception:
                    pass

            page.wait_for_load_state("load")
            time.sleep(2)

            # [4] Create FeatureScript feature
            print("[4/6] Creating FeatureScript feature...")
            print("  ⚠️  MANUAL STEP: Click the FeatureScript button in Onshape")
            print("     (Look for '{ }' icon or 'Add custom feature' in the toolbar)")
            print("     Waiting 5 minutes for editor to appear...")
            
            # Wait for the FeatureScript editor to appear (up to 5 minutes)
            editor = None
            for attempt in range(60):
                time.sleep(5)
                try:
                    # Try to find any editor-like element
                    editor = page.wait_for_selector(
                        'textarea, .monaco-editor, .CodeMirror, [role="textbox"], [contenteditable="true"]',
                        timeout=3000
                    )
                    if editor and editor.is_visible():
                        print(f"  ✅ Editor detected after {attempt * 5}s")
                        break
                except Exception:
                    if attempt % 6 == 0:
                        print(f"  Still waiting... ({attempt * 5}s)")
                    continue
            
            if not editor:
                raise RuntimeError("FeatureScript editor did not appear within 5 minutes")
            
            time.sleep(2)

            # [5] Fill and compile
            print(f"[5/6] Injecting {len(code)} chars of FeatureScript...")
            editor = find_editor(page, args.debug)
            editor.click()
            time.sleep(0.5)
            page.keyboard.press("Meta+a")
            time.sleep(0.2)
            page.keyboard.press("Backspace")
            time.sleep(0.2)
            page.keyboard.insert_text(code)
            time.sleep(0.5)

            click_accept(page, args.debug)
            time.sleep(3)

            success, errors = wait_compilation(page)
            if success:
                print("  ✅ FeatureScript compiled successfully.")
            else:
                print("  ❌ Compilation failed:")
                for e in errors:
                    print(f"     {e}")
                if not args.debug:
                    raise RuntimeError("Compilation failed. Re-run with --debug.")

            # [6] Screenshot
            screenshot = args.screenshot or f"parts/{Path(args.featurescript).stem}_result.png"
            print(f"[6/6] Screenshot → {screenshot}")
            time.sleep(2)
            page.screenshot(path=screenshot, full_page=False)

            if success:
                print(f"\n✅ Injected into ai/main — Part Studio \"{ps_name}\"")
                print(f"   Run 'merge' to push to main after review.")
            else:
                print("\n⚠️  Injection done but with compilation errors.")

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


def cmd_merge(args):
    """Merge ai/main branch into main after user confirmation."""
    sync_playwright = ensure_playwright()
    email, password = load_env_credentials()
    user_data = Path(args.user_data_dir)
    user_data.mkdir(parents=True, exist_ok=True)

    print(f"Merging {args.branch} → main")
    if not args.approve:
        print("⚠️  This will update the main branch with AI changes.")
        print("   Make sure you've reviewed the injected FeatureScript.")
        confirm = input("Proceed with merge? [y/N] ")
        if confirm.lower() not in ("y", "yes"):
            print("Merge cancelled.")
            return

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data.resolve()),
            headless=args.headless,
            viewport={"width": 1920, "height": 1080},
        )
        page = browser.new_page()
        page.set_default_timeout(args.timeout)

        try:
            page.goto(args.document, wait_until="domcontentloaded")
            login_or_wait(page, email, password, args.debug)
            page.wait_for_load_state("load")
            time.sleep(3)

            # Navigate to Versions & History → Merge
            # Onshape merge flow: click branch selector → "Merge branch" → select ai/main → confirm
            print("\nOpening merge dialog...")
            try:
                page.click('[aria-label="Branch"], [data-testid="branch-selector"]', timeout=5000)
                time.sleep(1)
                page.click('text=Merge branch', timeout=5000)
                time.sleep(1)
                # Select ai/main as source
                page.click(f'text={args.branch}', timeout=5000)
                time.sleep(1)
                # Confirm merge
                page.click('button:has-text("Merge"), button:has-text("Continue")', timeout=5000)
                time.sleep(3)
                print(f"✅ Merged {args.branch} → main")
            except Exception as e:
                print(f"⚠️  Could not complete merge automatically: {e}")
                print(f"   Please merge {args.branch} → main manually in Onshape.")
                print(f"   Document: {args.document}")

            if args.screenshot:
                page.screenshot(path=args.screenshot)

        except Exception as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            if args.debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)
        finally:
            browser.close()


def cmd_analyze(args):
    """Analyze feature differences between two branches."""
    sync_playwright = ensure_playwright()
    email, password = load_env_credentials()
    user_data = Path(args.user_data_dir)
    user_data.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing: {args.target} vs {args.base}")
    if args.part:
        print(f"Part Studio: {args.part}")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data.resolve()),
            headless=args.headless,
            viewport={"width": 1920, "height": 1080},
        )
        page = browser.new_page()
        page.set_default_timeout(args.timeout)

        try:
            # Open base branch first
            print(f"\n[1/3] Opening base branch ({args.base})...")
            page.goto(args.document, wait_until="domcontentloaded")
            login_or_wait(page, email, password, args.debug)
            page.wait_for_load_state("load")
            time.sleep(3)

            # Switch to base branch and capture feature tree
            base_features = _capture_feature_tree(page, args.part)

            # Switch to target branch and capture feature tree
            print(f"[2/3] Opening target branch ({args.target})...")
            try:
                page.click('[aria-label="Branch"]', timeout=5000)
                time.sleep(1)
                page.click(f'text={args.target}', timeout=5000)
                time.sleep(3)
            except Exception:
                print(f"  Warning: could not switch to branch {args.target}")

            target_features = _capture_feature_tree(page, args.part)

            # Compare
            print("[3/3] Computing diff...\n")
            diff = _compute_diff(base_features, target_features, args.part)

            # Output structured report
            print("=== DIFF REPORT ===")
            print(f"Base: {args.base}")
            print(f"Target: {args.target}")
            if args.part:
                print(f"Part Studio: {args.part}")

            for part_name, changes in diff.items():
                print(f"\nPart Studio: {part_name}")
                if changes["added"]:
                    print("  Added features:")
                    for f in changes["added"]:
                        print(f"    + {f}")
                if changes["removed"]:
                    print("  Removed features:")
                    for f in changes["removed"]:
                        print(f"    - {f}")
                if changes["modified"]:
                    print("  Modified features:")
                    for f in changes["modified"]:
                        print(f"    ~ {f}")
                if not any(changes.values()):
                    print("  (no changes)")

            if args.screenshot:
                page.screenshot(path=args.screenshot)

        except Exception as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            if args.debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)
        finally:
            browser.close()


def _capture_feature_tree(page, part_filter=None):
    """Extract feature names from the current Part Studio's feature tree."""
    features = {}
    try:
        # Feature tree items in Onshape
        items = page.query_selector_all(
            '.feature-list-item, .feature-item, [data-feature-name]'
        )
        for item in items:
            name = item.text_content().strip()
            if name and (not part_filter or part_filter.lower() in name.lower()):
                features[name] = True
    except Exception:
        pass
    return features


def _compute_diff(base_features, target_features, part_filter=None):
    """Compute added/removed/modified features between two branches."""
    diff = {}
    all_keys = set(base_features.keys()) | set(target_features.keys())

    for key in sorted(all_keys):
        in_base = key in base_features
        in_target = key in target_features
        changes = {"added": [], "removed": [], "modified": []}

        if not in_target and in_base:
            changes["removed"].append(key)
        elif not in_base and in_target:
            changes["added"].append(key)

        if any(changes.values()):
            diff[key] = changes

    return diff if diff else {"—": {"added": [], "removed": [], "modified": []}}


def cmd_list_parts(args):
    """List mapping from parts/*.fs to Part Studios."""
    parts_dir = Path("parts")
    if not parts_dir.exists():
        print("No parts/ directory found.")
        return

    fs_files = sorted(parts_dir.glob("*.fs"))
    if not fs_files:
        print("No .fs files in parts/")
        return

    print(f"{'File':30s} → Part Studio")
    print("-" * 50)
    for f in fs_files:
        ps_name = part_studio_name(str(f))
        print(f"{f:30s} → {ps_name}")


# ─── main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Onshape workspace manager — branch-based FeatureScript injection"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # inject
    p_inject = sub.add_parser("inject", help="Inject FeatureScript into ai/main")
    p_inject.add_argument("--document", required=True, help="Onshape document URL")
    p_inject.add_argument("--featurescript", required=True, help="Path to .fs file")
    p_inject.add_argument("--screenshot", help="Screenshot output path")
    p_inject.add_argument("--headless", action="store_true")
    p_inject.add_argument("--debug", action="store_true")
    p_inject.add_argument("--slow-mo", type=int, default=0)
    p_inject.add_argument("--user-data-dir", default="./.browser-data")
    p_inject.add_argument("--timeout", type=int, default=60000)
    p_inject.set_defaults(func=cmd_inject)

    # merge
    p_merge = sub.add_parser("merge", help="Merge ai/main → main")
    p_merge.add_argument("--document", required=True, help="Onshape document URL")
    p_merge.add_argument("--branch", default="ai/main", help="Branch to merge from")
    p_merge.add_argument("--approve", action="store_true", help="Skip confirmation prompt")
    p_merge.add_argument("--screenshot", help="Screenshot output path")
    p_merge.add_argument("--headless", action="store_true")
    p_merge.add_argument("--debug", action="store_true")
    p_merge.add_argument("--user-data-dir", default="./.browser-data")
    p_merge.add_argument("--timeout", type=int, default=60000)
    p_merge.set_defaults(func=cmd_merge)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze feature differences between branches")
    p_analyze.add_argument("--document", required=True, help="Onshape document URL")
    p_analyze.add_argument("--base", default="ai/main", help="Base branch")
    p_analyze.add_argument("--target", required=True, help="Target branch to compare")
    p_analyze.add_argument("--part", help="Specific Part Studio to analyze")
    p_analyze.add_argument("--screenshot", help="Screenshot output path")
    p_analyze.add_argument("--headless", action="store_true")
    p_analyze.add_argument("--debug", action="store_true")
    p_analyze.add_argument("--user-data-dir", default="./.browser-data")
    p_analyze.add_argument("--timeout", type=int, default=60000)
    p_analyze.set_defaults(func=cmd_analyze)

    # list-parts
    p_list = sub.add_parser("list-parts", help="Show parts/*.fs → Part Studio mapping")
    p_list.set_defaults(func=cmd_list_parts)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
