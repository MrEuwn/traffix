import { useState, type ReactNode } from "react";
import {
  useSimulationControls,
  useSystemStatus,
} from "../hooks/useTraffixData";
import { useTheme } from "../lib/ThemeContext";
import { fmtInt } from "../lib/format";
import {
  Btn,
  Card,
  Modal,
  PanelHead,
  Segmented,
  StateBlock,
  StatusPill,
  cn,
  useToast,
} from "../components/ui";

type Density = "comfortable" | "compact";

/** Tinggi state seragam supaya tata letak tidak bergeser saat memuat/galat. */
const BLOCK_H = 200;

const TOKENS: { token: string; swatch: string; use: string }[] = [
  { token: "primary", swatch: "bg-primary", use: "satu aksen interaksi" },
  { token: "ok", swatch: "bg-ok", use: "layanan normal" },
  { token: "info", swatch: "bg-info", use: "informasi model" },
  { token: "warn", swatch: "bg-warn", use: "perhatian" },
  { token: "high", swatch: "bg-high", use: "kepadatan tinggi" },
  { token: "crit", swatch: "bg-crit", use: "gangguan kritis" },
];

export const Settings = () => {
  const { data: status, isLoading, isError, isFetching, refetch } = useSystemStatus();
  const { start, stop } = useSimulationControls();
  const { theme, toggleTheme } = useTheme();
  const toast = useToast();

  const [density, setDensity] = useState<Density>("comfortable");
  const [confirmStop, setConfirmStop] = useState(false);

  const pad = density === "compact" ? "py-2" : "py-4";
  /** `s` = status yang sudah pasti ada; dipakai supaya TS menyempitkan tipenya. */
  const s = status && !isLoading ? status : null;
  const state = isLoading ? "loading" : isError || !s ? "error" : "ready";

  const Row = ({
    label,
    sub,
    children,
  }: {
    label: string;
    sub?: string;
    children: ReactNode;
  }) => (
    <div
      className={cn(
        "flex items-center justify-between gap-4 border-b border-line/60 last:border-0",
        pad,
      )}
    >
      <div className="min-w-0">
        <p className="text-body text-ink">{label}</p>
        {sub && <p className="mt-0.5 text-micro text-ink-muted">{sub}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-3">{children}</div>
    </div>
  );

  const handleStart = () =>
    start.mutate(undefined, {
      onSuccess: () => toast.push({ message: "Simulasi dimulai" }),
      onError: () => toast.push({ message: "Gagal memulai simulasi" }),
    });

  const handleStop = () => {
    setConfirmStop(false);
    stop.mutate(undefined, {
      onSuccess: () => toast.push({ message: "Simulasi dihentikan" }),
      onError: () => toast.push({ message: "Gagal menghentikan simulasi" }),
    });
  };

  return (
    <div className="space-y-4">
      <header className="space-y-1 border-b border-line pb-4">
        <p className="label-caps flex items-center gap-1.5">
          Konsol operator <span className="text-ink-muted">/</span>{" "}
          <span className="text-ink">Pengaturan</span>
        </p>
        <h1 className="text-title-md font-semibold tracking-tight text-ink">Pengaturan</h1>
        <p className="max-w-2xl text-body text-ink-soft">
          Status runtime, kendali simulasi, preferensi tampilan, dan keterbukaan sumber data
          Traffix.
        </p>
      </header>

      {/* 1. Status sistem */}
      <Card pad={false}>
        <PanelHead
          title="Status sistem"
          sub="Kondisi layanan dan modul diagnostik"
          icon="gauge"
          right={
            <Btn variant="ghost" icon="refresh" onClick={() => refetch()} disabled={isFetching}>
              Periksa
            </Btn>
          }
        />
        <div className="px-4">
          {!s ? (
            <StateBlock
              state={state}
              height={BLOCK_H}
              hint="Backend tidak merespons /api/v1/system/status"
              onRetry={() => refetch()}
            />
          ) : (
            <>
              <Row label="Layanan backend" sub={s.service}>
                <StatusPill
                  tone={s.status === "ok" ? "ok" : "warn"}
                  label={s.status === "ok" ? "Operasional" : `Terbatas (${s.status})`}
                  icon={s.status === "ok" ? "check-circle" : "alert-triangle"}
                />
              </Row>
              <Row label="Model klasifikasi penyebab" sub={`Mode ${s.ml_mode}`}>
                <StatusPill
                  tone={s.ml_ready ? "ok" : "crit"}
                  label={s.ml_ready ? "Siap" : "Belum siap"}
                  icon={s.ml_ready ? "check-circle" : "alert-triangle"}
                />
                {s.ml_fallback_active && (
                  <StatusPill tone="warn" label="Fallback aktif" icon="lightbulb-off" />
                )}
              </Row>
              <Row label="Simulasi replay" sub="Mesin tick data sintetis">
                <StatusPill
                  tone={s.simulation_active ? "ok" : "idle"}
                  label={s.simulation_active ? "Berjalan" : "Berhenti"}
                  icon={s.simulation_active ? "play" : "pause"}
                />
              </Row>
              <Row label="Dataset operasional" sub="Buffer time-series 6 simpang · 30 ruas">
                <StatusPill
                  tone={s.dataset_ready ? "ok" : "idle"}
                  label={s.dataset_ready ? "Tersedia" : "Tidak tersedia"}
                  icon={s.dataset_ready ? "layers" : "inbox"}
                />
              </Row>
              <Row label="Kamera CCTV" sub="Pipeline deteksi kendaraan">
                <StatusPill
                  tone={s.camera_ready ? "ok" : "idle"}
                  label={s.camera_ready ? "Aktif" : "Nonaktif"}
                  icon={s.camera_ready ? "check-circle" : "lightbulb-off"}
                />
              </Row>
              <Row label="Cuaca" sub="Sumber kondisi luar untuk kelas hujan/banjir">
                <StatusPill
                  tone={s.weather_ready ? "ok" : "idle"}
                  label={s.weather_ready ? "Tersedia" : "Tidak tersedia"}
                  icon={s.weather_ready ? "cloud-rain" : "inbox"}
                />
              </Row>
              <Row label="Horizons prediksi" sub="Jangka waktu prediksi tersedia">
                <span className="num text-micro text-ink-soft">
                  {s.supported_horizons.join(" · ") || "—"}
                </span>
              </Row>
            </>
          )}
        </div>
      </Card>

      {/* 2. Kontrol simulasi */}
      <Card pad={false}>
        <PanelHead
          title="Kontrol simulasi"
          sub="Jalankan atau hentikan replay data sintetis"
          icon="sliders"
          right={<StatusPill tone="idle" label="Seed 42" icon="info" />}
        />
        <div className="px-4">
          {!s ? (
            <StateBlock
              state={state}
              height={BLOCK_H}
              hint="Kontrol butuh status sistem terkini"
              onRetry={() => refetch()}
            />
          ) : (
            <>
              <Row
                label="Mulai simulasi"
                sub={
                  s.simulation_active
                    ? "Simulasi sedang berjalan"
                    : "Lanjutkan replay tick berurutan"
                }
              >
                <Btn
                  variant="primary"
                  icon="play"
                  onClick={handleStart}
                  disabled={s.simulation_active || start.isPending}
                >
                  {start.isPending ? "Memulai..." : "Mulai"}
                </Btn>
              </Row>
              <Row
                label="Hentikan simulasi"
                sub="Replay berhenti pada tick terakhir; tidak bisa dilanjutkan dari titik ini"
              >
                <Btn
                  variant="danger"
                  icon="pause"
                  onClick={() => setConfirmStop(true)}
                  disabled={!s.simulation_active || stop.isPending}
                >
                  {stop.isPending ? "Menghentikan..." : "Hentikan"}
                </Btn>
              </Row>
            </>
          )}
        </div>
      </Card>

      {/* 3. Tampilan */}
      <Card pad={false}>
        <PanelHead title="Tampilan" sub="Tema dan kepadatan antarmuka" icon="settings" />
        <div className="px-4">
          <Row label="Tema" sub="Berlaku pada seluruh konsol">
            <Segmented
              options={[
                { value: "dark", label: "Gelap" },
                { value: "light", label: "Terang" },
              ]}
              value={theme}
              onChange={(v) => {
                if (v !== theme) toggleTheme();
              }}
            />
          </Row>
          <Row label="Kepadatan tampilan" sub="Nyaman = jarak baris 16px, Padat = 8px">
            <Segmented
              options={[
                { value: "comfortable", label: "Nyaman" },
                { value: "compact", label: "Padat" },
              ]}
              value={density}
              onChange={setDensity}
            />
          </Row>
          <Row
            label="Token warna"
            sub="Status tidak pernah hanya warna — selalu ada ikon dan label"
          >
            <ul className="flex flex-wrap justify-end gap-x-3 gap-y-1.5">
              {TOKENS.map((t) => (
                <li key={t.token} className="flex items-center gap-1.5 text-micro text-ink-soft">
                  <span
                    className={cn("h-3 w-3 rounded-bar border border-line", t.swatch)}
                    aria-hidden="true"
                  />
                  <span className="num text-ink">{t.token}</span>
                  <span className="text-ink-muted">{t.use}</span>
                </li>
              ))}
            </ul>
          </Row>
        </div>
      </Card>

      {/* 4. Sumber data */}
      <Card pad={false}>
        <PanelHead
          title="Sumber data"
          sub="Transparansi asal angka yang ditampilkan"
          icon="layers"
          right={<StatusPill tone="warn" label="Data sintetis" icon="info" />}
        />
        <div className="px-4">
          <Row label="Asal data" sub="Dihasilkan simulator, bukan rekaman lapangan">
            <span className="text-micro text-ink-soft">Sintetis · seed 42</span>
          </Row>
          <Row label="Cakupan jaringan" sub="Mulai 2026-05-01 WIB, resolusi 1 menit">
            <span className="num text-micro text-ink-soft">
              {fmtInt(6)} simpang · {fmtInt(30)} ruas
            </span>
          </Row>
          <Row label="Volume tick" sub="7 hari data sintetis">
            <span className="num text-micro text-ink-soft">{fmtInt(302400)} baris tik</span>
          </Row>
          <Row
            label="Muat ulang telemetri"
            sub={isFetching ? "Meminta data terbaru..." : "Paksa pembacaan ulang dari API"}
          >
            <Btn variant="ghost" icon="refresh" onClick={() => refetch()} disabled={isFetching}>
              Muat ulang
            </Btn>
          </Row>
        </div>
      </Card>

      <Modal
        open={confirmStop}
        title="Hentikan simulasi?"
        sub="Replay tick berhenti dan panel live tidak diperbarui sampai dimulai ulang."
        onClose={() => setConfirmStop(false)}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setConfirmStop(false)}>
              Batal
            </Btn>
            <Btn variant="danger" icon="pause" onClick={handleStop}>
              Ya, hentikan
            </Btn>
          </>
        }
      >
        <p className="text-body text-ink-soft">
          Data yang sudah terhimpun tetap tersimpan. Simulasi dapat dimulai kembali kapan saja
          dari panel Kontrol simulasi.
        </p>
      </Modal>
    </div>
  );
};
