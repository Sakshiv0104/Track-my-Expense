#!/usr/bin/env python3
"""Records a demo walkthrough of the deployed Spendly app.

Steps: log in, add a random expense, delete a random expense, log out.
Produces a .webm video via Playwright's built-in video recording.

Dev tooling only — not part of the Flask app or its requirements.txt.
Install with: pip install -r tools/requirements-demo.txt && playwright install chromium

Usage:
    SPENDLY_DEMO_PASSWORD=... python tools/record_demo.py \
        --url https://expense-tracker-production-7149.up.railway.app \
        --email sakshiv0102@gmail.com
"""
import argparse
import os
import random
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
DESCRIPTIONS = [
    "Coffee run", "Weekly groceries", "Uber ride", "Streaming subscription",
    "Pharmacy pickup", "Lunch with friends", "Phone bill", "Book purchase",
]
PAUSE_MS = 800


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True, help="Public base URL of the deployed app (no trailing slash)")
    p.add_argument("--email", required=True, help="Login email")
    p.add_argument("--out-dir", default="tools/recordings", help="Directory to save the video into")
    p.add_argument("--headed", action="store_true", help="Show the browser window while recording")
    return p.parse_args()


def main():
    args = parse_args()
    base_url = args.url.rstrip("/")
    password = os.environ.get("SPENDLY_DEMO_PASSWORD")
    if not password:
        print("SPENDLY_DEMO_PASSWORD is not set in the environment.", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            record_video_dir=str(out_dir),
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        try:
            print("Step 1/4: logging in...")
            page.goto(f"{base_url}/login")
            page.fill("#email", args.email)
            page.fill("#password", password)
            page.wait_for_timeout(PAUSE_MS)
            page.click("button.btn-submit")
            page.wait_for_url(f"{base_url}/profile", timeout=15000)
            page.wait_for_timeout(PAUSE_MS)

            print("Step 2/4: adding a random expense...")
            page.click("a.combined-add-btn")
            page.wait_for_url(f"{base_url}/expenses/add")
            amount = round(random.uniform(5, 250), 2)
            category = random.choice(CATEGORIES)
            description = random.choice(DESCRIPTIONS)
            # Leave #date at the server's pre-filled default (today, per the
            # server's own clock) rather than computing it locally — the
            # server rejects future dates and local/server clocks can drift
            # across a day boundary (timezone offset, container UTC clock).
            server_today = page.input_value("#date")
            page.fill("#amount", str(amount))
            page.select_option("#category", category)
            page.fill("#description", description)
            page.wait_for_timeout(PAUSE_MS)
            page.click("button.btn-submit")
            page.wait_for_url(f"{base_url}/profile", timeout=15000)
            page.wait_for_selector(f"text={description}", timeout=10000)
            print(f"  added: {category} A${amount:.2f} on {server_today} — {description}")
            page.wait_for_timeout(PAUSE_MS)

            print("Step 3/4: deleting a random existing expense...")
            delete_links = page.locator("a.recent-delete-link")
            count = delete_links.count()
            if count == 0:
                raise RuntimeError("No expenses found to delete")
            idx = random.randrange(count)
            delete_links.nth(idx).click()
            page.wait_for_selector("button.btn-danger", timeout=10000)
            page.wait_for_timeout(PAUSE_MS)
            page.click("button.btn-danger")
            page.wait_for_url(f"{base_url}/profile", timeout=15000)
            page.wait_for_timeout(PAUSE_MS)

            print("Step 4/4: logging out...")
            page.click("text=Log out")
            page.wait_for_url(f"{base_url}/", timeout=15000)
            page.wait_for_timeout(PAUSE_MS)
        finally:
            context.close()
            browser.close()

        video_path = page.video.path()

    print(f"VIDEO_PATH={video_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
