import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../lib/AuthContext";
import { Btn, Card, Field, SeedBadge } from "../components/ui";
import { Icon } from "../components/ui/icons";

/** Fakta produk apa adanya — tanpa angka karangan. */
const FACTS = [
  "Mengklasifikasi 9 penyebab bottleneck: banjir, kecelakaan, lampu mati, perbaikan jalan, keramaian event, hujan, kendaraan berat, volume puncak, normal.",
  "Macro-F1 0,847 vs baseline aturan 0,176 — rinciannya di tab Evaluasi Model.",
  "Data sintetis seed 42 · 6 simpang · 30 ruas, mulai 2026-05-01 WIB.",
];

const wibClock = () =>
  new Intl.DateTimeFormat("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "Asia/Jakarta",
  }).format(new Date());

export const LoginPage = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wib, setWib] = useState(wibClock);

  useEffect(() => {
    const id = window.setInterval(() => setWib(wibClock()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Nama pengguna dan kata sandi wajib diisi");
      return;
    }
    setError(login(username, password));
  };

  return (
    <div className="grid min-h-screen bg-base lg:grid-cols-[58fr_42fr]">
      {/* Panel kiri: editorial */}
      <section className="flex flex-col justify-between gap-10 border-line px-6 py-8 md:px-10 lg:border-r lg:py-14">
        <div className="space-y-6">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-control border border-line bg-primary-quiet text-primary">
              <Icon name="activity" size={16} />
            </span>
            <span className="text-title-sm font-semibold tracking-tight text-ink">
              Traffix<span className="text-primary"> Ops</span>
            </span>
          </div>

          <h1 className="max-w-xl text-title-lg font-semibold tracking-tight text-ink sm:text-hero">
            Diagnosis penyebab macet, bukan sekadar prediksi volume
          </h1>
          <p className="max-w-md text-body text-ink-soft">
            Konsol operasional petugas lalu lintas: apa penyebab bottleneck, di ruas
            mana, dan tindakan apa yang disarankan.
          </p>

          <ul className="max-w-xl space-y-2">
            {FACTS.map((fact, i) => (
              <li
                key={fact}
                className="flex gap-3 rounded-card border border-line bg-surface px-4 py-3"
              >
                <span className="num shrink-0 text-micro text-ink-muted">
                  [{String(i + 1).padStart(2, "0")}]
                </span>
                <span className="text-body text-ink-soft">{fact}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
          <SeedBadge />
          <span className="num text-micro text-ink-soft" title="Waktu WIB">
            {wib} WIB
          </span>
        </div>
      </section>

      {/* Panel kanan: formulir masuk */}
      <section className="flex items-center justify-center px-6 py-8 lg:px-10">
        <Card className="w-full max-w-[400px]">
          <header className="border-b border-line pb-4">
            <p className="label-caps">Otentikasi konsol</p>
            <h2 className="mt-1 text-title-sm font-semibold text-ink">Masuk</h2>
            <p className="mt-0.5 text-micro text-ink-muted">
              Akun petugas pengawas lalu lintas
            </p>
          </header>

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <Field
              label="Nama pengguna"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              autoComplete="username"
              autoFocus
            />

            {/* Tombol tampilkan disematkan pada input (label-caps 16px + mb 6px = 22px). */}
            <div className="relative">
              <Field
                label="Kata sandi"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Kata sandi"
                autoComplete="current-password"
                className="pr-24"
              />
              <Btn
                type="button"
                variant="ghost"
                aria-pressed={showPassword}
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-1 top-[22px] border-0 bg-transparent px-2 hover:bg-transparent"
              >
                {showPassword ? "Sembunyikan" : "Tampilkan"}
              </Btn>
            </div>

            <label className="flex min-h-11 w-fit cursor-pointer select-none items-center gap-2">
              <input type="checkbox" defaultChecked className="h-4 w-4 accent-primary" />
              <span className="text-micro text-ink-soft">Ingat saya</span>
            </label>

            {error && (
              <p role="alert" className="flex items-center gap-1.5 text-micro text-crit">
                <Icon name="alert-triangle" size={13} />
                {error}
              </p>
            )}

            <Btn type="submit" variant="primary" className="w-full">
              Masuk
            </Btn>
          </form>

          <footer className="mt-4 flex items-center gap-2 border-t border-line pt-3">
            <SeedBadge />
            <span className="text-micro text-ink-muted">Autentikasi lokal</span>
          </footer>
        </Card>
      </section>
    </div>
  );
};
