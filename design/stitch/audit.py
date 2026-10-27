"""Audit Stitch exports against the Prompt A checklist (evidence-based, no guessing)."""
from __future__ import annotations

import re
from pathlib import Path

FILES = ["login", "dashboard", "livemap", "evaluasi", "settings"]
DOCS = {n: Path(f"{n}.html").read_text(encoding="utf-8", errors="ignore") for n in FILES}

CAUSES = ["normal", "volume puncak", "perbaikan jalan", "hujan", "banjir", "kecelakaan",
          "keramaian", "lampu mati", "kendaraan berat"]
SIMPAng = ["Meruya", "Tomang", "Cawang", "Grogol", "Kebayoran", "Bekasi"]

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def count_all(pattern: str, flags=re.I) -> dict[str, int]:
    return {n: len(re.findall(pattern, d, flags)) for n, d in DOCS.items()}


def show(label: str, pattern: str, flags=re.I) -> None:
    hits = count_all(pattern, flags)
    total = sum(hits.values())
    detail = ", ".join(f"{n}:{c}" for n, c in hits.items() if c)
    print(f"{label:52} total={total:<4} {detail}")


def snippets(pattern: str, limit: int = 3, width: int = 90) -> None:
    for n, d in DOCS.items():
        found = re.findall(pattern, d, re.I)
        for item in found[:limit]:
            text = re.sub(r"\s+", " ", item)
            print(f"    [{n}] {text[:width]}")
        if found:
            return


print("=== A. 10 CACAT ===")
show("1 label 'Keyakinan'", r"keyakinan")
show("2 satuan 'smp/jam'", r"smp/jam")
show("2b satuan 'kend' (kendaraan)", r"\bkend\b|kendaraan")
show("3 ikon svg", r"<svg")
show("3b pola (pattern-swatch/diagonal)", r"diagonal|pattern|repeating-linear|dots|cross")
show("4 font-size < 11px", r"font-size:\s*(?:[0-9]|10)(?:\.\d+)?px")
print("   font sizes dipakai:")
all_sizes = {}
for n, d in DOCS.items():
    for s in re.findall(r"font-size:\s*([\d.]+)px", d):
        all_sizes[s] = all_sizes.get(s, 0) + 1
print("   ", dict(sorted(all_sizes.items(), key=lambda kv: float(kv[0]))))
show("5 tabular-nums", r"tabular-nums|font-variant-numeric")
show("6 modal/dialog konfirmasi", r"role=\"dialog\"|modal|konfirmasi")
show("6b 'Urungkan' (undo)", r"urungkan")
show("6c 'Jejak audit'", r"jejak audit|audit")
show("6d tabel fase", r"fase")
print("   nama simpang muncul:")
for name in SIMPAng:
    hits = count_all(name)
    print(f"      {name:12} {hits}")
show("8 'Semua penyebab'", r"semua penyebab")
show("9 'Sekarang' di heat strip", r"sekarang|now marker|playhead")
show("9b scrub/slider", r"type=\"range\"|slider|scrub|role=\"slider\"")
show("10 'Sematkan'/dock peta", r"sematkan|dock")

print("\n=== B. ATURAN KERAS ===")
show("gradien", r"gradient")
show("blur/backdrop", r"blur\(")
show("emoji", EMOJI.pattern)
show("aksen #2F6FED / 2f6fed", r"2f6fed")
show("state loading", r"memuat|loading|skeleton|animate-pulse")
show("state kosong", r"belum ada data|tidak ada data|kosong")
show("state galat", r"gagal|galat|error")
show("focus-visible / ring", r"focus-visible|focus:ring|outline")
show("target 44px (h-11/min-h-11)", r"h-11|min-h-11|44px")
show("import eksternal (cdn/lib baru)", r"<script[^>]+src=\"http|<link[^>]+href=\"http")
print("   host eksternal yang dipanggil:")
hosts = set()
for d in DOCS.values():
    hosts |= set(re.findall(r"https?://([\w.-]+)/", d))
print("   ", sorted(hosts))

print("\n=== FORMAT ANGKA ===")
show("benar 0,847 / 3.982 (koma desimal)", r"\b\d{1,3}(?:\.\d{3})+(?:,\d+)?\b|\b0,\d+")
show("SALAH 0.847 (titik desimal)", r"0\.\d{2,4}\b")
show("persen tanpa label keyakinan", r"\d{1,3},\d%")

print("\n=== C. BUKTI D2 (evaluasi.html) ===")
ev = DOCS["evaluasi"]
for label, pat in [
    ("kata 'baseline'", r"baseline"),
    ("macro f1", r"macro"),
    ("matriks konfusi", r"konfusi"),
    ("split/protokol", r"split|latih|validasi|uji"),
    ("penjaga kebocoran", r"kebocoran|leakage"),
    ("batasan", r"batasan|limitasi"),
    ("angka 9x9 (angka acak besar)", r"\b\d{1,2}\.\d{3}\b"),
]:
    print(f"   {label:32} {len(re.findall(pat, ev, re.I))}")
print("   angka yang muncul di evaluasi:", sorted(set(re.findall(r"\b0,\d{3}\b", ev)))[:12])

print("\n=== TEKS ASING / PLACEHOLDER ===")
for word in ["lorem", "ipsum", "todo", "placeholder", "sample", "dummy", "xxx", "your ", "tbd"]:
    hits = count_all(rf"\b{word}")
    if sum(hits.values()):
        print(f"   {word}: {hits}")
print("\n=== JUDUL PER LAYAR (h1/h2) ===")
for n, d in DOCS.items():
    titles = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", d, re.S)
    clean = [re.sub(r"<[^>]+>|\s+", " ", t).strip()[:70] for t in titles[:4]]
    print(f"   {n:10} {clean}")
