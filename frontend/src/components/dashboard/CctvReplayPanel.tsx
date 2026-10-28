import { useEffect, useMemo, useState } from "react";
import { useCctvFrames, useLiveInference } from "../../hooks/useTraffixData";
import { apiUrl } from "../../lib/api";
import { fmtInt, fmtNum } from "../../lib/format";
import { Btn, Card, PanelHead, Segmented, StateBlock, StatusPill, cn } from "../ui";
import { Icon } from "../ui/icons";
import type { CctvFrame, LiveInferenceResult } from "../../types";

type Period = "semua" | "pagi" | "siang" | "malam";
const PERIODS: { value: Period; label: string }[] = [
  { value: "semua", label: "Semua" },
  { value: "pagi", label: "Pagi" },
  { value: "siang", label: "Siang" },
  { value: "malam", label: "Malam" },
];
const STEP_MS = 2500;
const CLASS_LABEL: Record<string, string> = {
  car: "mobil",
  motorcycle: "motor",
  bus: "bus",
  truck: "truk",
  gol1_non_truk: "Gol. I",
  gol2_truk_2_gandar: "Gol. II",
  gol3_truk_3_gandar: "Gol. III",
  gol4_truk_4_gandar: "Gol. IV",
  gol5_truk_5plus_gandar: "Gol. V",
};

/** Kotak deteksi hasil inferensi langsung, digambar di atas frame mentah. */
const BoxOverlay = ({ result }: { result: LiveInferenceResult }) => (
  <svg
    viewBox={`0 0 ${result.width} ${result.height}`}
    className="pointer-events-none absolute inset-0 h-full w-full"
    aria-hidden="true"
  >
    {result.boxes.map((b, i) => (
      <g key={i}>
        <rect
          x={b.xyxy[0]}
          y={b.xyxy[1]}
          width={b.xyxy[2] - b.xyxy[0]}
          height={b.xyxy[3] - b.xyxy[1]}
          fill="none"
          stroke="rgb(var(--c-primary))"
          strokeWidth={2.5}
        />
        <text x={b.xyxy[0] + 3} y={b.xyxy[1] - 4} fill="rgb(var(--c-primary))" fontSize={14} fontWeight={600}>
          {b.class} {b.confidence.toFixed(2)}
        </text>
      </g>
    ))}
  </svg>
);

/** Replay rekaman CCTV publik + deteksi YOLOv8. Bukan siaran langsung: setiap frame
    adalah potongan rekaman, kotak berasal dari bobot `best.pt` (tersimpan atau dijalankan sekarang). */
export const CctvReplayPanel = () => {
  const { data, isLoading, isError, refetch } = useCctvFrames();
  const live = useLiveInference();
  const [period, setPeriod] = useState<Period>("semua");
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [liveResult, setLiveResult] = useState<LiveInferenceResult | null>(null);

  const frames = useMemo<CctvFrame[]>(
    () => (data?.frames ?? []).filter((f) => period === "semua" || f.period === period),
    [data, period],
  );
  const frame = frames.length ? frames[index % frames.length] : undefined;

  useEffect(() => {
    if (!playing || frames.length < 2) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % frames.length);
      setLiveResult(null);
    }, STEP_MS);
    return () => window.clearInterval(id);
  }, [playing, frames.length]);

  if (isLoading) return <StateBlock state="loading" height={320} />;
  if (isError)
    return (
      <StateBlock state="error" height={320} hint="Endpoint /api/v1/cameras/frames tidak merespons." onRetry={() => refetch()} />
    );
  if (!data?.available || !frame)
    return (
      <StateBlock
        state="empty"
        height={320}
        emptyText={data?.reason ?? "Belum ada frame CCTV dengan deteksi YOLO."}
      />
    );

  const showLive = liveResult?.frame_id === frame.frame_id;
  const count = showLive ? liveResult.vehicle_count : frame.vehicle_count;
  const classCounts = showLive
    ? liveResult.boxes.reduce<Record<string, number>>((acc, b) => ({ ...acc, [b.class]: (acc[b.class] ?? 0) + 1 }), {})
    : (frame.by_class ?? {});
  const classLine = Object.entries(classCounts)
    .map(([name, n]) => `${CLASS_LABEL[name] ?? name} ${n}`)
    .join(" · ");
  const go = (delta: number) => {
    setPlaying(false);
    setLiveResult(null);
    setIndex((i) => (i + delta + frames.length) % frames.length);
  };
  const runLive = () => {
    setPlaying(false);
    live.mutate(frame.frame_id, { onSuccess: setLiveResult });
  };

  return (
    <Card pad={false}>
      <PanelHead
        title="Kamera CCTV · deteksi kendaraan YOLOv8"
        sub="Rekaman CCTV publik Bina Marga, tol Jakarta–Tangerang · bukan simpang simulasi"
        icon="car"
        right={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <StatusPill tone="warn" label="Replay rekaman · bukan live" icon="play" />
            <StatusPill
              tone={showLive ? "ok" : "info"}
              label={showLive ? `Inferensi langsung · ${fmtNum(liveResult.inference_ms, 0)} ms` : "Inferensi tersimpan"}
              icon="activity"
            />
          </div>
        }
      />
      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="min-w-0 space-y-2">
          <div className="relative overflow-hidden rounded-card border border-line bg-raised">
            <img
              src={apiUrl(`/api/v1/cameras/frames/${encodeURIComponent(frame.frame_id)}/image?annotated=${!showLive}`)}
              alt={`Frame CCTV ${frame.location ?? frame.video} detik ${frame.second}`}
              width={frame.width}
              height={frame.height}
              className="block h-auto w-full"
            />
            {showLive && <BoxOverlay result={liveResult} />}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Segmented
              options={PERIODS}
              value={period}
              onChange={(v) => {
                setPeriod(v);
                setIndex(0);
                setLiveResult(null);
              }}
            />
            <div className="flex items-center gap-1.5">
              <Btn variant="ghost" icon="undo" onClick={() => go(-1)} aria-label="Frame sebelumnya" />
              <Btn
                variant="ghost"
                icon={playing ? "pause" : "play"}
                onClick={() => setPlaying((p) => !p)}
                aria-label={playing ? "Jeda replay" : "Putar replay"}
              />
              <Btn variant="ghost" icon="chevron-right" onClick={() => go(1)} aria-label="Frame berikutnya" />
            </div>
          </div>
          <p className="num text-micro text-ink-muted">
            frame {fmtInt((index % frames.length) + 1)} / {fmtInt(frames.length)} · {frame.video} · detik {frame.second}
          </p>
        </div>

        <div className="min-w-0 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-card border border-line bg-raised px-3 py-2">
              <p className="label-caps">Kotak terdeteksi</p>
              <p className="num text-metric font-semibold text-ink">{fmtInt(count)}</p>
              <p className="text-micro text-ink-muted">{classLine || "tidak ada kendaraan"}</p>
              {!showLive && frame.team_model_vehicle_count != null && (
                <p className="num text-micro text-ink-muted" title="best.pt, model 1 kelas yang dilatih tim">
                  model tim: {fmtInt(frame.team_model_vehicle_count)}
                </p>
              )}
            </div>
            <div className="rounded-card border border-line bg-raised px-3 py-2">
              <p className="label-caps">Lokasi</p>
              <p className="text-body font-semibold text-ink">{frame.location ?? "tidak ada di metadata"}</p>
              <p className="text-micro text-ink-muted">
                {frame.ruas ?? "ruas tol"} · {frame.period}
              </p>
            </div>
          </div>
          <dl className="space-y-1 text-micro">
            {[
              ["Direkam", frame.recorded_at_wib ?? "—"],
              ["Cuaca (Open-Meteo)", frame.temperature_c != null ? `${fmtNum(frame.temperature_c, 1)} °C · hujan ${fmtNum(frame.precipitation_mm ?? 0, 1)} mm` : "—"],
              ["Rata-rata confidence", frame.mean_confidence != null ? fmtNum(frame.mean_confidence, 2) : "—"],
              [
                "Detektor",
                `${data.model?.weights.split("/").pop()?.replace(".pt", "")} · ${data.model?.mode === "sliced" ? "sliced 3×3" : "full frame"} · ${data.model?.imgsz} px · conf ≥ ${data.model?.conf_threshold}`,
              ],
              ["Bobot", `${data.model?.weights.split("/").pop()} · ${data.model?.sha256.slice(0, 10)}…`],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 border-b border-line/60 pb-1 last:border-0">
                <dt className="text-ink-muted">{k}</dt>
                <dd className="num text-right text-ink-soft">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="space-y-1.5">
            <Btn
              variant="primary"
              icon="activity"
              className="w-full"
              onClick={runLive}
              disabled={!data.live_inference_available || live.isPending}
            >
              {live.isPending ? "YOLO berjalan…" : "Jalankan YOLO sekarang pada frame ini"}
            </Btn>
            {!data.live_inference_available && (
              <p className="text-micro text-ink-muted">{data.live_inference_reason}</p>
            )}
            {live.isError && (
              <p role="alert" className="flex items-center gap-1.5 text-micro text-crit">
                <Icon name="alert-triangle" size={13} />
                Inferensi gagal — frame tersimpan tetap ditampilkan.
              </p>
            )}
          </div>
          <ul className="space-y-1.5">
            {(data.caveats ?? []).map((c) => (
              <li key={c} className={cn("flex items-start gap-1.5 text-micro text-ink-muted")}>
                <Icon name="alert-triangle" size={12} className="mt-0.5 shrink-0 text-warn" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
};
