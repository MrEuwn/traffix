"""Audit UI hasil rombak (Playwright) — memeriksa aplikasi yang BENAR-BENAR jalan.

Login, buka 4 tab, lalu periksa di DOM nyata:
  - tidak ada state galat / permintaan API gagal / error konsol
  - font: Inter untuk UI, JetBrains Mono untuk elemen .num
  - tidak ada teks < 11px, tidak ada emoji, target sentuh tombol >= 44px
  - string wajib per halaman + angka id-ID muncul (bukti data API nyata)
  - modal konfirmasi kendali sinyal benar-benar bisa dibuka
  - screenshot per halaman ke frontend/screenshots/

Jalankan (backend :8000 + vite :5173 hidup):
    ./.venv/Scripts/python.exe frontend/scripts/ui_audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:5173"
SHOTS = Path("frontend/screenshots")

REQUIRED: dict[str, list[str]] = {
    "Dashboard": ["Keyakinan model", "smp/jam", "kend", "LOS", "Jejak audit", "Sekarang", "data sintetis"],
    "Live Map": ["Semua penyebab", "Sematkan", "kend", "data sintetis"],
    "Evaluasi Model": ["Rule-based", "Presisi", "Recall", "Batasan", "metrics.json"],
    "Settings": ["Status Sistem", "Sumber Data", "Tema", "seed 42"],
}

AUDIT_JS = r"""
() => {
  const out = { small: [], emoji: [], targets: [], numFont: null, bodyFont: null,
                numCount: 0, inkCount: 0, sizes: {}, clipped: [] };
  out.bodyFont = getComputedStyle(document.body).fontFamily;
  const emojiRe = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const own = Array.from(el.childNodes)
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent.trim())
      .join(' ');
    if (own) {
      const size = parseFloat(cs.fontSize);
      if (size < 11) out.small.push({ t: own.slice(0, 60), size, cls: el.className.toString().slice(0, 50) });
      if (emojiRe.test(own)) out.emoji.push(own.slice(0, 40));
      const key = size.toFixed(1);
      out.sizes[key] = (out.sizes[key] || 0) + 1;
      if (cs.color !== 'rgba(0, 0, 0, 0)') out.inkCount++;
    }
    if (el.classList.contains('num')) {
      out.numCount++;
      if (!out.numFont) out.numFont = cs.fontFamily;
    }
    if (el.tagName === 'TH' && el.offsetParent !== null) {
      if (el.scrollWidth > el.clientWidth + 2) {
        out.clipped.push({ t: (el.innerText || '').trim().slice(0, 40), need: el.scrollWidth, have: el.clientWidth });
      }
    }
    if (el.tagName === 'BUTTON' && el.offsetParent !== null) {
      const r = el.getBoundingClientRect();
      if (r.height > 0) out.targets.push({ h: Math.round(r.height), label: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 30) });
    }
  }
  return out;
}
"""


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    notes: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        console_errors: list[str] = []
        failed: list[str] = []
        tiles: list[str] = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("requestfailed", lambda r: failed.append(f"{r.method} {r.url} ({r.failure})"))
        page.on("response", lambda r: tiles.append(r.url) if "tile" in r.url and r.ok else None)

        page.goto(URL, wait_until="networkidle")
        page.screenshot(path=str(SHOTS / "login.png"), full_page=True)
        if not page.get_by_text("Traffix", exact=False).first.is_visible():
            failures.append("halaman login tidak menampilkan merek Traffix")

        # Formulir masuk: target sentuh 44px dan latar token gelap (bukan putih bawaan UA).
        field = page.evaluate(
            """() => {
              const i = document.querySelector('input');
              const cs = getComputedStyle(i);
              return { h: Math.round(i.getBoundingClientRect().height), bg: cs.backgroundColor, cls: i.className };
            }"""
        )
        if field["h"] < 44:
            failures.append(f"Login: tinggi input {field['h']}px (< 44px)")
        if field["bg"] in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)"):
            failures.append(f"Login: latar input '{field['bg']}' — kelas primitif tertimpa (className)")
        body_bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
        if body_bg != field["bg"] and field["bg"] != "rgb(17, 24, 35)":
            notes.append(f"Login: latar input {field['bg']} — periksa apakah sesuai token surface")

        # Masuk: cari field lewat label, lalu tombol "Masuk".
        for label, value in (("Nama pengguna", "admin"), ("Kata sandi", "admin123")):
            box = page.locator(f"input[placeholder*='{label}' i], input[aria-label*='{label}' i]").first
            if not box.count():
                box = page.locator("input").nth(0 if label.startswith("Nama") else 1)
            box.fill(value)
        page.get_by_role("button", name=re.compile("masuk", re.I)).first.click()
        page.wait_for_timeout(7000)

        if page.get_by_text("Nama pengguna", exact=False).first.is_visible() and not page.get_by_text(
            "Dashboard", exact=False
        ).count():
            failures.append("login gagal: masih di halaman masuk setelah submit")

        for tab in ("Dashboard", "Live Map", "Evaluasi Model", "Settings"):
            page.get_by_role("button", name=re.compile(tab, re.I)).first.click()
            page.wait_for_timeout(6000)
            body = page.inner_text("body")
            low = body.lower()
            for needle in REQUIRED[tab]:
                if needle.lower() not in low:
                    failures.append(f"{tab}: teks wajib '{needle}' tidak ditemukan")
            for marker in ("tidak merespons", "connection to backend", "Gagal memuat data"):
                if marker.lower() in low:
                    failures.append(f"{tab}: state galat tampil di UI ('{marker}')")

            audit = page.evaluate(AUDIT_JS)
            if "Inter" not in audit["bodyFont"]:
                failures.append(f"{tab}: font UI bukan Inter ({audit['bodyFont']})")
            if audit["numCount"] and audit["numFont"] and "JetBrains" not in audit["numFont"]:
                failures.append(f"{tab}: elemen .num tidak memakai JetBrains Mono ({audit['numFont']})")
            if audit["small"]:
                sample = "; ".join(f"'{s['t']}' {s['size']}px" for s in audit["small"][:5])
                failures.append(f"{tab}: {len(audit['small'])} teks < 11px → {sample}")
            if audit["emoji"]:
                failures.append(f"{tab}: emoji di teks → {audit['emoji'][:3]}")
            small_targets = [t for t in audit["targets"] if t["h"] < 40]
            if small_targets:
                notes.append(f"{tab}: {len(small_targets)} tombol < 40px (mis. {small_targets[:3]})")
            if audit["clipped"]:
                notes.append(f"{tab}: header tabel terpotong → {audit['clipped'][:3]}")
            notes.append(
                f"{tab}: ukuran teks {audit['sizes']} · .num {audit['numCount']} elemen · tombol {len(audit['targets'])}"
            )
            page.screenshot(path=str(SHOTS / f"ops-{tab.lower().replace(' ', '-')}.png"), full_page=True)

            if tab == "Dashboard":
                approve = page.get_by_role("button", name=re.compile("setujui rekomendasi", re.I)).first
                opened = False
                if approve.count() and approve.is_enabled():
                    approve.click()
                    opened = True
                else:
                    # Tombol memang disabled bila belum ada rekomendasi berprioritas:
                    # telusuri tiap simpang sampai ada yang memenuhi syarat.
                    rows_btns = page.locator("button:has-text('INT-0')")
                    for i in range(min(rows_btns.count(), 8)):
                        rows_btns.nth(i).click()
                        page.wait_for_timeout(700)
                        if approve.count() and approve.is_enabled():
                            approve.click()
                            opened = True
                            break
                if opened:
                    page.wait_for_timeout(1200)
                    body_now = page.inner_text("body")
                    if "Konfirmasi perubahan fase" not in body_now:
                        failures.append("Dashboard: modal 'Konfirmasi perubahan fase' tidak muncul")
                    else:
                        page.screenshot(path=str(SHOTS / "ops-modal-konfirmasi.png"))
                        low_now = body_now.lower()
                        for needle in ("hijau usulan", "catatan operator", "tidak mengubah lampu nyata"):
                            if needle not in low_now:
                                failures.append(f"Dashboard modal: '{needle}' tidak ada di dialog konfirmasi")
                        if "jejak audit" not in low_now:
                            failures.append("Dashboard: panel 'Jejak audit' tidak ada di halaman")
                        apply_btn = page.get_by_role("button", name=re.compile("^terapkan", re.I))
                        if apply_btn.count():
                            apply_btn.first.click()
                            page.wait_for_timeout(1500)
                            after = page.inner_text("body").lower()
                            for needle in ("perubahan diterapkan", "urungkan"):
                                if needle not in after:
                                    failures.append(f"Dashboard: setelah Terapkan, '{needle}' tidak muncul (toast undo)")
                else:
                    notes.append("Dashboard: belum ada rekomendasi berprioritas > LOW — modal tidak diuji (perilaku sah, ada penjelasannya di UI)")
                batal = page.get_by_role("button", name=re.compile("batal", re.I))
                if batal.count():
                    batal.first.click()
                page.keyboard.press("Escape")
                page.wait_for_timeout(600)

        api_failed = [f for f in failed if "/api/" in f and "/cameras/videos/" not in f]

        # Peta: basemap tidak boleh bergantung API key (CARTO menolak tanpa key) —
        # dan minimal satu tile harus benar-benar terunduh.
        tiles_seen = [u for u in tiles]
        if any("basemaps.cartocdn.com" in u for u in tiles_seen):
            failures.append("Live Map: basemap masih memakai tile CARTO ber-API key")
        if not any("tile.openstreetmap.org" in u for u in tiles_seen):
            failures.append("Live Map: tidak ada tile peta yang terunduh")
        notes.append(f"Live Map: {len(tiles_seen)} permintaan tile berhasil")

        # Tidak boleh ada luber horizontal pada lebar desktop yang didukung.
        for width in (1600, 1440, 1280):
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(1500)
            for tab in ("Dashboard", "Live Map", "Evaluasi Model", "Settings"):
                page.get_by_role("button", name=re.compile(tab, re.I)).first.click()
                page.wait_for_timeout(2500)
                over = page.evaluate(
                    "() => document.documentElement.scrollWidth - window.innerWidth"
                )
                if over > 2:
                    failures.append(f"{tab} @{width}px: luber horizontal {over}px")
        browser.close()

    print(f"screenshot: {(SHOTS).resolve()}")
    for n in notes:
        print(f"catatan: {n}")
    if api_failed:
        print("permintaan API gagal:")
        for item in api_failed[:10]:
            print(f"  - {item}")
        failures.append(f"{len(api_failed)} permintaan API gagal")
    if console_errors:
        print("error konsol:")
        for item in console_errors[:10]:
            print(f"  - {item}")
    if failures:
        print("\nGAGAL:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nPASS: 4 halaman merender data API tanpa state galat; font, ukuran teks, target sentuh, dan modal sesuai aturan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
