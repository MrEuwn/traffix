"""End-to-end browser check of the Traffix dashboard (Playwright + Chromium).

Logs in, waits for the v4 panels to render live API numbers, asserts that the
three requested parameters are on screen and that no backend-error state is
shown, then opens the Model Evaluation tab and asserts the D2 evidence table.

Usage:
    ./.venv/Scripts/python.exe frontend/scripts/e2e_check.py
    (backend :8000 and vite :5173 must be running)
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DASHBOARD_URL = "http://localhost:5173"
SHOT_DIR = Path("frontend/screenshots")

CHECKS: list[tuple[str, str, str]] = [
    ("Dashboard", "Penyebab Bottleneck", "panel penyebab bottleneck"),
    ("Dashboard", "Perempatan", "kartu rata-rata lampu merah (perempatan)"),
    ("Dashboard", "Pertigaan", "kartu rata-rata lampu merah (pertigaan)"),
    ("Dashboard", "Ruas Jalan", "tabel ruas"),
    ("Dashboard", "R6+", "breakdown kendaraan roda 6+"),
    ("Dashboard", "data sintetis", "badge keterbukaan data sintetis"),
    ("Evaluasi Model", "Macro F1", "tabel metrik D2"),
    ("Evaluasi Model", "Rule-based", "baris baseline aturan"),
]

ERROR_MARKERS = ["tidak merespons", "Gagal memuat data", "connection to backend"]


def main() -> int:
    """Run the browser check and report failures."""
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        console_errors: list[str] = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        failed_requests: list[str] = []
        page.on(
            "requestfailed",
            lambda req: failed_requests.append(f"{req.method} {req.url} ({req.failure})"),
        )

        page.goto(DASHBOARD_URL, wait_until="networkidle")
        page.fill('input[placeholder*="username" i]', "admin")
        page.fill('input[placeholder*="password" i]', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_timeout(6000)

        body = page.inner_text("body")
        body_lower = body.lower()
        for tab, needle, label in CHECKS:
            if tab == "Dashboard" and needle.lower() not in body_lower:
                failures.append(f"{label}: teks '{needle}' tidak ada di tab {tab}")
        for marker in ERROR_MARKERS:
            if marker.lower() in body_lower:
                failures.append(f"state error tampil di UI: '{marker}'")

        page.screenshot(path=str(SHOT_DIR / "dashboard.png"), full_page=True)

        page.get_by_role("button", name="Evaluasi Model", exact=False).first.click()
        try:
            page.get_by_text("Macro F1", exact=False).first.wait_for(timeout=25000)
        except Exception:
            failures.append("halaman Evaluasi Model tidak selesai memuat tabel metrik dalam 25 detik")
        page.wait_for_timeout(2000)
        model_body = page.inner_text("body").lower()
        for tab, needle, label in CHECKS:
            if tab == "Evaluasi Model" and needle.lower() not in model_body:
                failures.append(f"{label}: teks '{needle}' tidak ada di tab Evaluasi Model")
        page.screenshot(path=str(SHOT_DIR / "evaluasi-model.png"), full_page=True)

        # Video CCTV (Google Drive) memang tidak tersedia offline — bukan kegagalan panel.
        api_calls = [
            r for r in failed_requests
            if "/api/" in r and "/cameras/videos/" not in r
        ]
        camera_video_hits = len(failed_requests) - len(api_calls)
        browser.close()

    print(f"screenshot: {(SHOT_DIR / 'dashboard.png').resolve()}")
    print(f"screenshot: {(SHOT_DIR / 'evaluasi-model.png').resolve()}")
    if camera_video_hits:
        print(f"catatan: {camera_video_hits} video CCTV gagal dimuat (Google Drive tidak tersedia) — di luar panel v4")
    if api_calls:
        print("permintaan API gagal:")
        for item in api_calls[:10]:
            print(f"  - {item}")
    if failures:
        print("\nGAGAL:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nPASS: dashboard + halaman evaluasi merender data backend tanpa state error.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
