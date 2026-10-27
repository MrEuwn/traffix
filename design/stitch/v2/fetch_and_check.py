"""Tarik 6 layar Stitch kanonik (pasca-perbaikan) + verifikasi aturan & angka.

Jalankan: python design/stitch/v2/fetch_and_check.py
Bukti tersimpan: design/stitch/v2/*.html, *.png, LAPORAN.txt
"""
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
D = "https://contribution.usercontent.google.com/download?c="
LC = "https://lh3.googleusercontent.com/aida/"

SCREENS = {
    # nama: (id layar, hash html, hash screenshot)
    "dashboard": ("4da0c0e39fc243fc9d25f651320613c7",
                  "CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzYyMTRkNzc2MGFiYTQwODBhOGI0NDNmMzYyMmU4M2FmEgsSBxCFz53ZqQ0YAZIBIwoKcHJvamVjdF9pZBIVQhM0NzA3OTIzMTIyODI3MDk5MDQx",
                  "AEtjO1VI072_MuiLQ84FQKenPQ1mBjbk9j_YfLX-JMbYhcQV0O0fsgSIsbJo1xzXU5YSG0MtXTc6b1iAoLuSHWu6Gs6tsKh2e3muStAEJ7eMY-4PXLnVtAi5Z4Vq3Sk1fNulxiUhcmu3iRva1f4j_l_bOicj1FWqDj1dX-5eygqZW3aB_wQoR7_FgEwGDFzIlUDw2eBIagao3JzAK7_iv1472MZwRKhIk7Ack-gioJKR9gn0ajv6M-pWvDPt3w"),
    "livemap": ("3d90ec7e1c5e43bdb071c10690b32d0f",
                 "CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzlhNzM5ZGU0ODMyNTRmZThiMWYzNzZjYjMwN2YzOTkzEgsSBxCFz53ZqQ0YAZIBIwoKcHJvamVjdF9pZBIVQhM0NzA3OTIzMTIyODI3MDk5MDQx",
                 "AEtjO1WjKuzIrAXlSJTA-01o-y6qW1xRjMJIIg8jF14WHVM613uiN9uSbVBabYITmXUHsC-Brt8Usz2q3rCuRNfkaM5S5JloUgJIBV7eUM5lcllMUgkQFf2Pv0OCUKUTrBx4E7tIe9Y2-CxNaf9P1gz2_M7rNkI2iXhuWfbY7Ykjrf5auZ2HUidficLVMA1CXHoPEl7lomoROmEhnBTei09k-z5_ck6fUL2j_4YwHLrJN6SlulaG-onKg-rd1Q"),
    "evaluasi": ("0b056d679b8044e1b7c8c49a1895ef56",
                 "CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzhjNDJhNDI1YWI5NjQyZGJhOTliMmRkZGRlYTAyMzNmEgsSBxCFz53ZqQ0YAZIBIwoKcHJvamVjdF9pZBIVQhM0NzA3OTIzMTIyODI3MDk5MDQx",
                 "AEtjO1XW4OtQn--aZgOn6KdReZN1Uw_LMUuA5SK2chnUamUDrJJykRVuLGIJircXb7U8sQ0VHkvrhNYtdmbdbl4-ELM2VT1AkXLAAjKkwtesQgZTaHyA5BEe3NN2YBJ1DN8fb9tQlhvVlqPHZH8FxHmbiYJwuQBJ4sJioDtZ81-cUdZNEcGiKWxS7rZRiSdUTkskW5xLDm2aE6gB5dbHfvVivRz0QEbZqbQgFExrBPkbsW8tXEsNUGufY17kusM"),
    "settings": ("ad78ff6c10c74f14b93cda40eb1210e1",
                 "CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sX2UzMzBlYzBiYjEwZjRkNjg4MzBjMGYzNmFmOTZjN2QxEgsSBxCFz53ZqQ0YAZIBIwoKcHJvamVjdF9pZBIVQhM0NzA3OTIzMTIyODI3MDk5MDQx",
                 "AEtjO1WPxabr8AciUmyzJXCpxTkWy3m3P947F2QyTYuNXJBbInTDn8XnHk8pfgFzkC30pK929lHAAmgU4-vZWO-3L_uYbW3WAAYeacyrjTAmnHBSizlQuxVkwqz_3GAYhQE7nXlHC2NKrBKWHPaomlTaq-0-ItGrkl8C4lRpXrmJXUEQrTkPQUaRoVn-FM2Pxt0flj8pRbjo4ltTsNpd_lfxkmjeHLx2TqYgP2e3vMeipgTrMsUKICCdVUsHzrU"),
    "login": ("8019019636ff43edba363628a06e5236",
              "CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sX2Y3Yzk0OThjM2IzMTRlMjk4YTJkMzYzMmI5NmZmYTU0EgsSBxCFz53ZqQ0YAZIBIwoKcHJvamVjdF9pZBIVQhM0NzA3OTIzMTIyODI3MDk5MDQx",
              "AEtjO1Vkm_oFqoY1Y4ptW4mEGFQHMNrpVBHM9rR29zt_sQoG9fSMYt4WdLUO7FAzzVpQ58-YdSiwWgcZByG1mvLPyR7T9Wa_zXq-lFSy9xcvDvZl3FjixymWK4DqlsjpXQ33xWQP3SS9Leg5Da8poPMwViohVvpTfRleDRmLPo0ktSHD9YwsfQkMHmeWidgQhP2by5GyZ7OHdEKgZQTG8IJNCgfET3elXXnavK_YqYyW4kaOEO5FO310ivsm450"),
    "component": ("09b7e47633894310b08333acf868ac8c",
                  "CgthaWRhX2NvZGVmeBJ7Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpaCiVodG1sXzBlY2JlMDA4Yzk5NDRhOWZhZjYwODAxMzZkMmNiNjEzEgsSBxCFz53ZqQ0YAZIBIwoKcHJvamVjdF9pZBIVQhM0NzA3OTIzMTIyODI3MDk5MDQx",
                  "AEtjO1WR_2XW4fQP2DSpbV-jwd32hPr_W6IAaIFXgYYCyw0hmLJa1sSj45XWctR7nlkXnhVhMRQjqVIUDj5FwbHfU7x3GT86VEk9Yg-8LhRLXTf4ibCrXIhalffvfAO776F3HZnNLLlm6xXytKdRjuB2whPdIYcP95ef2AhoUDFdxthl5dZuMJmn5LYUPtJCxjVgpnA_wmvzLQsGEB_Bzxt3Ffuz6wM62sz1C1Bz4gnINbo51P7kooh4AZlX9mA"),
}


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    dest.write_bytes(data)
    return len(data)


# ---------- muat kebenaran dari model ----------
M = json.load(open(ROOT / "backend/ml/bottleneck/artifacts/metrics.json"))
PER = {c["cause"]: c for c in M["per_class"]}
CM = M["confusion_matrix"]["matrix"]
CM_LABELS = M["confusion_matrix"]["labels"]
truth_dec = set()
for c in PER.values():
    for k in ("precision", "recall", "f1"):
        truth_dec.add(f"{c[k]:.4f}".replace(".", ","))
truth_int = {c["support"] for c in PER.values()}
truth_int |= {v for row in CM for v in row if v}
truth_int |= {sum(truth_int & {c["support"] for c in PER.values()}), M["n_test"]}

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")


def check(name, html):
    t = []
    sizes = [float(x) for x in re.findall(r"text-\[(\d+(?:\.\d+)?)px\]", html)]
    sizes += [float(x) for x in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", html)]
    small = sorted({s for s in sizes if s < 11})
    t.append(f"ukuran teks: min {min(sizes) if sizes else '-'}px · nilai <11px: {small or 'tidak ada'}")
    t.append(f"emoji: {len(EMOJI.findall(html))}")
    for tok in ("#6B7885", "#6b7885", "#4B5B6E", "#4b5b6e", "#30363D", "#30363d"):
        n = len(re.findall(tok, html, re.I))
        if n:
            t.append(f"token di luar aturan terpakai: {tok.upper()} x{n}")
    t.append(f"gradient CSS: {len(re.findall(r'linear-gradient|radial-gradient', html))} · blur: {len(re.findall('blur' + chr(92) + '(', html))}")
    kw = {
        "Keyakinan model": 0, "Semua penyebab": 0, "Sekarang": 0, "Sematkan": 0,
        "Konfirmasi perubahan fase": 0, "Urungkan": 0, "Jejak audit": 0,
        "Belum ada data": 0, "Gagal memuat data": 0, "Baseline": 0,
        "smp/jam": 0, "kend": 0, "tabular-nums": 0, "Maks sel 20.151": 0, "43.200": 0,
    }
    for k in kw:
        kw[k] = len(re.findall(re.escape(k), html, re.I))
    t.append("kata kunci: " + " · ".join(f"{k}={v}" for k, v in kw.items() if v))
    if not any(kw.values()):
        pass
    # angka desimal 4 digit vs metrics.json
    decs = set(re.findall(r"\b\d,\d{4}\b", html))
    if decs:
        bad = sorted(d for d in decs if d not in truth_dec)
        t.append(f"desimal 4 digit: {len(decs)} ditemukan · TIDAK cocok metrics.json: {bad or 'tidak ada'}")
    return t


report = []
for name, (sid, h, s) in SCREENS.items():
    hp = OUT / f"{name}.html"
    n = fetch(D + h + "&filename=&opi=96797242", hp)
    sp = OUT / f"{name}.png"
    fetch(LC + s, sp)
    html = hp.read_text(encoding="utf-8", errors="replace")
    report.append(f"=== {name} (layar {sid}) · {n/1024:.0f} KB html · {sp.stat().st_size/1024:.0f} KB png")
    report += ["  " + line for line in check(name, html)]
    report.append("")

LAPORAN = "\n".join(report)
(OUT / "LAPORAN.txt").write_text(LAPORAN, encoding="utf-8")
print(LAPORAN)
