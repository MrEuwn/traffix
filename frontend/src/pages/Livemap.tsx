import { useEffect, useMemo, useRef, useState } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  useBottlenecks,
  useBottlenecksByIntersection,
  useIntersections,
  useManualOverride,
  useSegments,
  useSignalsSummary,
  useSimulation,
} from "../hooks/useTraffixData";
import {
  Btn,
  Card,
  CauseBadge,
  Chip,
  Confidence,
  HeatStrip,
  LosBadge,
  PanelHead,
  ProbabilityBar,
  SeedBadge,
  StateBlock,
  StatusPill,
  cn,
  useToast,
} from "../components/ui";
import { Icon } from "../components/ui/icons";
import { CAUSE_ORDER, causeMeta } from "../lib/causes";
import { fmtInt, fmtNum, fmtPct } from "../lib/format";
import type { BottleneckPerIntersection, Intersection, SegmentItem } from "../types";

/* Koordinat master v4 — satu-satunya angka statis di halaman ini, diambil apa adanya dari
   data/data_synthetic/v4/intersections.csv (tidak ada endpoint yang menyajikan lat/lon).
   ponytail: peta koordinat statis; pindahkan ke API bila backend mulai menyajikan lat/lon. */
const COORDS: Record<string, [number, number]> = {
  "INT-001": [-6.187, 106.735],
  "INT-002": [-6.176, 106.79],
  "INT-003": [-6.24, 106.87],
  "INT-004": [-6.166, 106.789],
  "INT-005": [-6.244, 106.799],
  "INT-006": [-6.218, 106.989],
};

/* Lampu: status selalu label + ikon, tidak pernah warna saja. */
const LAMP: Record<string, { label: string; tone: "ok" | "warn" | "crit"; icon: string }> = {
  GREEN: { label: "Hijau", tone: "ok", icon: "check-circle" },
  YELLOW: { label: "Kuning", tone: "warn", icon: "clock" },
  RED: { label: "Merah", tone: "crit", icon: "alert-triangle" },
};

const LOS_RANK = ["A", "B", "C", "D", "E", "F"];
const worstLos = (list: string[]) => [...LOS_RANK].reverse().find((l) => list.includes(l)) ?? null;

const mean = (list: number[]) =>
  list.length ? list.reduce((a, b) => a + b, 0) / list.length : null;

const tipeLabel = (tipe?: string | null) =>
  tipe === "perempatan" ? "Perempatan" : tipe === "pertigaan" ? "Pertigaan" : "Tipe belum tersedia";

const playheadNow = () => {
  const d = new Date();
  return ((d.getHours() * 60 + d.getMinutes()) / (24 * 60)) * 100;
};

const LIST_H = 400;
const DOCK_H = 168;
const HEAT_H = 120;

interface Row {
  ix: Intersection;
  cause: string | null;
  confidence: number | null;
  tipe: string | null;
  lengan: number | null;
  arusSmp: number | null;
  antreanKend: number | null;
  antreanM: number | null;
  los: string | null;
  vc: number | null;
  waitMin: number | null;
  cycleS: number | null;
}

/* Pin peta: bulat warna causeMeta + ikon penyebab; tanpa popup mengambang. */
const pin = (cause: string, active: boolean) => {
  const meta = causeMeta(cause);
  const size = active ? 28 : 22;
  return L.divIcon({
    className: "",
    html: `<span class="flex items-center justify-center rounded-full border-2 ${
      active ? "h-7 w-7 border-ink animate-live-pulse" : "h-[22px] w-[22px] border-ink-soft"
    }" style="background:${meta.color};color:#fff">${renderToStaticMarkup(
      <Icon name={meta.icon} size={size - 12} />,
    )}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
};

/* Ikon di-cache per (simpang, penyebab, aktif): polling 1 dtk tidak me-render ulang pin. */
const pins = new Map<string, L.DivIcon>();
const pinFor = (id: string, cause: string, active: boolean) => {
  const key = `${id}:${cause}:${active}`;
  let icon = pins.get(key);
  if (!icon) {
    icon = pin(cause, active);
    pins.set(key, icon);
  }
  return icon;
};

const Recenter = ({ target }: { target: [number, number] | null }) => {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, Math.max(map.getZoom(), 15));
  }, [map, target]);
  return null;
};

const MapMiss = ({ onMiss }: { onMiss: () => void }) => {
  useMapEvents({ click: onMiss });
  return null;
};

export const LiveMap = () => {
  const { data: intersections = [], isLoading, isError, refetch } = useIntersections();
  const {
    data: bottlenecks,
    isLoading: bnLoading,
    isError: bnError,
    refetch: refetchBn,
  } = useBottlenecks();
  const { data: segments } = useSegments();
  const { data: signals } = useSignalsSummary();
  const { push } = useToast();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pinned, setPinned] = useState(false);
  const [causeFilter, setCauseFilter] = useState<string | null>(null);
  const [playhead, setPlayhead] = useState(playheadNow);
  const [simOpen, setSimOpen] = useState(false);

  const detail = useBottlenecksByIntersection(selectedId ?? "");
  const sim = useSimulation(selectedId, simOpen);
  const override = useManualOverride();

  /* Satu baris gabungan: live (intersections) + dataset v4 (bottlenecks/signals/segments). */
  const rows = useMemo<Row[]>(() => {
    const per = new Map((bottlenecks?.per_intersection ?? []).map((b) => [b.intersection_id, b]));
    const sig = new Map((signals?.per_intersection ?? []).map((s) => [s.intersection_id, s]));
    const items: SegmentItem[] = segments?.items ?? [];
    return intersections.map((ix) => {
      const b = per.get(ix.intersection_id);
      const s = sig.get(ix.intersection_id);
      const secs = items.filter(
        (i) => i.section_type === "approach" && i.intersection_id === ix.intersection_id,
      );
      const kend = secs.length ? secs.reduce((a, i) => a + i.queue_length_veh, 0) : null;
      const kap = secs.reduce((a, i) => a + i.kapasitas_kendaraan, 0);
      const panjang = secs.reduce((a, i) => a + i.panjang_m, 0);
      return {
        ix,
        cause: b?.dominant_cause ?? null,
        confidence: b?.confidence ?? null,
        tipe: s?.tipe_persimpangan ?? b?.tipe_persimpangan ?? null,
        lengan: s?.jumlah_lengan ?? null,
        arusSmp: secs.length
          ? secs.reduce((a, i) => a + i.vc_ratio * i.kapasitas_smp_per_jam, 0)
          : null,
        antreanKend: kend ?? ix.queue_length,
        /* meter = porsi ruas yang tersisi antrean; dari kapasitas_kendaraan + panjang_m API */
        antreanM: kend != null && kap > 0 ? Math.round((kend / kap) * panjang) : null,
        los: worstLos(secs.map((i) => i.los)),
        vc: mean(secs.map((i) => i.vc_ratio)),
        waitMin: secs.length
          ? mean(secs.map((i) => i.wait_time_min))
          : (s?.avg_wait_time_min ?? null),
        cycleS: s?.cycle_length_s ?? null,
      };
    });
  }, [intersections, bottlenecks, segments, signals]);

  const causeCount = useMemo(() => {
    const m = new Map<string, number>();
    (bottlenecks?.causes ?? []).forEach((c) => m.set(c.cause, c.sections));
    return m;
  }, [bottlenecks]);

  const visible = causeFilter ? rows.filter((r) => r.cause === causeFilter) : rows;
  const selected = rows.find((r) => r.ix.intersection_id === selectedId) ?? null;
  const detailData: BottleneckPerIntersection | undefined = detail.data;

  /* Dock harus terlihat sejak muat pertama (aturan audit: dock + "Sematkan"), sekali saja. */
  const autoPicked = useRef(false);
  useEffect(() => {
    if (!autoPicked.current && rows.length) {
      autoPicked.current = true;
      setSelectedId(rows[0].ix.intersection_id);
    }
  }, [rows]);

  const center = useMemo<[number, number]>(() => {
    const pts = rows.map((r) => COORDS[r.ix.intersection_id]).filter(Boolean);
    if (!pts.length) return COORDS["INT-002"];
    return [
      pts.reduce((a, p) => a + p[0], 0) / pts.length,
      pts.reduce((a, p) => a + p[1], 0) / pts.length,
    ];
  }, [rows]);

  const selCoords = useMemo(
    () => (selectedId ? (COORDS[selectedId] ?? null) : null),
    [selectedId],
  );

  /* Leaflet meneruskan klik marker ke peta; kunci sekali agar dock tidak langsung tertutup. */
  const markerClick = useRef(false);
  const openDock = (id: string) => {
    markerClick.current = true;
    setSelectedId(id);
    setSimOpen(false);
  };
  const missMap = () => {
    if (markerClick.current) {
      markerClick.current = false;
      return;
    }
    if (!pinned) setSelectedId(null);
  };

  const listState =
    isLoading || bnLoading ? "loading" : isError || bnError ? "error" : visible.length ? "ready" : "empty";

  /* Heat strip: 24 blok jam dari history replay (60 tick terakhir) simpang terpilih. */
  const heatRows = useMemo(() => {
    if (!selected || !detailData?.history?.length) return [];
    const cells: (string | null)[] = Array.from({ length: 24 }, () => null);
    detailData.history.forEach((h) => {
      const hour = Number(h.timestamp_wib?.slice(11, 13));
      if (Number.isInteger(hour) && hour >= 0 && hour < 24) cells[hour] = h.dominant_cause;
    });
    return [{ label: selected.ix.intersection_name, cells }];
  }, [selected, detailData]);

  const hourIdx = Math.min(23, Math.floor((playhead / 100) * 24));
  const hourPoint = detailData?.history?.find(
    (h) => Number(h.timestamp_wib?.slice(11, 13)) === hourIdx,
  );
  const heatState = !selectedId
    ? "empty"
    : detail.isLoading
      ? "loading"
      : detail.isError
        ? "error"
        : "empty";
  const top3 = detailData?.top3 ?? [];

  return (
    <div className="flex flex-col gap-3">
      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-title-sm font-semibold text-ink">Live Map Telemetri Simpang</h1>
          <p className="mt-0.5 text-micro text-ink-muted">
            {bottlenecks
              ? `tick ${fmtInt(bottlenecks.tick)} · ${bottlenecks.timestamp_wib ?? "—"} · ruas terdampak ${fmtInt(
                  bottlenecks.affected_section_count,
                )} dari ${fmtInt(bottlenecks.section_count)}`
              : "menunggu analitik dataset v4"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill
            tone={isError || bnError ? "crit" : "info"}
            icon="map"
            label={`${fmtInt(rows.length)} simpang`}
          />
          <SeedBadge />
        </div>
      </Card>

      {/* Filter penyebab: selalu terlihat, tidak ikut menciut bersama daftar simpang. */}
      <Card>
        <div className="flex items-center justify-between gap-2">
          <span className="label-caps">Filter penyebab</span>
          <span className="text-micro text-ink-muted">jumlah = ruas terdampak</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Chip
            active={causeFilter === null}
            label="Semua penyebab"
            count={rows.length}
            onClick={() => setCauseFilter(null)}
          />
          {CAUSE_ORDER.map((c) => {
            const meta = causeMeta(c);
            return (
              <Chip
                key={c}
                active={causeFilter === c}
                dot={meta.color}
                icon={meta.icon}
                label={meta.label}
                count={causeCount.get(c) ?? 0}
                onClick={() => setCauseFilter(causeFilter === c ? null : c)}
              />
            );
          })}
        </div>
      </Card>

      <div className="flex flex-col gap-3 lg:flex-row">
        {/* ── peta + dock ── */}
        <div className="relative h-[560px] min-w-0 flex-1 overflow-hidden rounded-card border border-line bg-base lg:h-[620px]">
          <MapContainer
            center={center}
            zoom={12}
            zoomControl
            attributionControl={false}
            className="h-full w-full !bg-base"
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              subdomains="abcd"
              attribution="© OpenStreetMap · CARTO"
            />
            <Recenter target={selCoords} />
            <MapMiss onMiss={missMap} />
            {rows.map(
              (r) =>
                COORDS[r.ix.intersection_id] && (
                  <Marker
                    key={r.ix.intersection_id}
                    position={COORDS[r.ix.intersection_id]}
                    icon={pinFor(r.ix.intersection_id, r.cause ?? "normal", r.ix.intersection_id === selectedId)}
                    eventHandlers={{ click: () => openDock(r.ix.intersection_id) }}
                  />
                ),
            )}
          </MapContainer>

          <div className="absolute left-14 top-3 z-[500] flex items-center gap-2 rounded-control border border-line bg-surface px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-ok animate-live-pulse" aria-hidden="true" />
            <span className="num text-micro text-ink-soft">LIVE 1s</span>
            <span className="num border-l border-line pl-2 text-micro text-ink-muted">
              {bottlenecks?.timestamp_wib ?? "—"}
            </span>
          </div>
          <p className="absolute bottom-2 left-3 z-[500] text-micro text-ink-muted">
            © OpenStreetMap · CARTO
          </p>

          {selected && (
            <aside className="absolute inset-y-0 right-0 z-[1000] flex w-dock max-w-full flex-col overflow-x-hidden border-l border-line-strong bg-surface">
              <header className="border-b border-line px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill
                        tone={LAMP[selected.ix.signal_state].tone}
                        icon={LAMP[selected.ix.signal_state].icon}
                        label={LAMP[selected.ix.signal_state].label}
                      />
                      <span className="truncate text-title-sm font-semibold text-ink">
                        {selected.ix.intersection_name}
                      </span>
                      <span className="num shrink-0 text-micro text-ink-muted">
                        [{selected.ix.intersection_id}]
                      </span>
                    </div>
                    <p className="mt-1 text-micro text-ink-muted">
                      {tipeLabel(selected.tipe)} · {fmtInt(selected.lengan)} lengan ·{" "}
                      {selected.ix.weather_condition}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Btn
                      variant="ghost"
                      icon="pin"
                      aria-pressed={pinned}
                      onClick={() => setPinned((p) => !p)}
                    >
                      {pinned ? "Lepas sematan" : "Sematkan"}
                    </Btn>
                    <Btn
                      variant="ghost"
                      icon="close"
                      aria-label="Tutup detail"
                      onClick={() => {
                        setSelectedId(null);
                        setPinned(false);
                      }}
                    />
                  </div>
                </div>
              </header>

              <div className="flex-1 space-y-4 overflow-y-auto p-4">
                <CauseBadge cause={selected.cause ?? "normal"} confidence={selected.confidence} />

                <div className="grid grid-cols-2 gap-2">
                  {[
                    { l: "Arus", v: fmtInt(selected.arusSmp), u: "smp/jam" },
                    { l: "Kecepatan", v: fmtInt(selected.ix.avg_speed), u: "km/jam" },
                    {
                      l: "Antrean",
                      v: fmtInt(selected.antreanKend),
                      u:
                        selected.antreanM != null
                          ? `kend (${fmtInt(selected.antreanM)} m)`
                          : "kend",
                    },
                    { l: "Okupansi", v: fmtPct(selected.ix.occupancy_rate), u: "" },
                  ].map((m) => (
                    <div key={m.l} className="rounded-control border border-line bg-raised px-3 py-2">
                      <div className="label-caps">{m.l}</div>
                      <div className="num mt-1 text-title-sm font-semibold text-ink">
                        {m.v}
                        {m.u && (
                          <span className="ml-1 text-micro font-normal text-ink-muted">{m.u}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <section className="space-y-2">
                  <h3 className="label-caps">Rincian sinyal</h3>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="rounded-control border border-line bg-raised px-3 py-2">
                      <div className="label-caps">Hijau saat ini</div>
                      <div className="num mt-1 text-cell text-ink">
                        {fmtInt(selected.ix.green_duration_seconds)}
                        <span className="ml-1 text-micro text-ink-muted">dtk</span>
                      </div>
                      <div className="text-micro text-ink-muted">
                        siklus {selected.cycleS != null ? `${fmtInt(selected.cycleS)} dtk` : "—"}
                      </div>
                    </div>
                    <div className="rounded-control border border-line bg-raised px-3 py-2">
                      <div className="label-caps">V/C</div>
                      <div className="num mt-1 text-cell text-ink">{fmtNum(selected.vc, 2)}</div>
                      <div className="text-micro text-ink-muted">volume/kapasitas</div>
                    </div>
                    <div className="rounded-control border border-line bg-raised px-3 py-2">
                      <div className="label-caps">Rata-rata tunggu</div>
                      <div className="num mt-1 text-cell text-ink">
                        {fmtNum(selected.waitMin, 1)}
                        <span className="ml-1 text-micro text-ink-muted">menit</span>
                      </div>
                      <div className="text-micro text-ink-muted">pendekat simpang</div>
                    </div>
                  </div>
                </section>

                <section className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    <Btn
                      variant="primary"
                      icon="clock"
                      disabled={override.isPending}
                      onClick={() =>
                        override.mutate(
                          {
                            intersectionId: selected.ix.intersection_id,
                            greenDurationSeconds:
                              Math.round(selected.ix.green_duration_seconds) + 12,
                          },
                          {
                            onSuccess: () =>
                              push({
                                message: `Hijau +12 dtk diterapkan di ${selected.ix.intersection_name}`,
                              }),
                            onError: () =>
                              push({ message: "Gagal menerapkan override; lampu tidak berubah" }),
                          },
                        )
                      }
                    >
                      Terapkan +12 dtk
                    </Btn>
                    <Btn
                      variant="ghost"
                      icon={simOpen ? "pause" : "activity"}
                      onClick={() => setSimOpen((s) => !s)}
                    >
                      Simulasi
                    </Btn>
                  </div>
                  <p className="text-micro text-ink-muted">
                    Simulasi pada data sintetis — tidak mengubah lampu nyata
                  </p>

                  {simOpen && (
                    <div className="rounded-control border border-line bg-raised px-3 py-2">
                      {sim.isLoading && (
                        <p className="text-micro text-ink-muted">Menjalankan simulasi...</p>
                      )}
                      {sim.isError && <p className="text-micro text-crit">Simulasi gagal dimuat</p>}
                      {sim.data && (
                        <dl className="space-y-1">
                          {[
                            {
                              l: "Antrean",
                              v: `${fmtInt(sim.data.current.queue_length)} ke ${fmtInt(
                                sim.data.projected.queue_length,
                              )} kend`,
                            },
                            {
                              l: "Kecepatan",
                              v: `${fmtNum(sim.data.current.avg_speed, 1)} ke ${fmtNum(
                                sim.data.projected.avg_speed,
                                1,
                              )} km/jam`,
                            },
                            {
                              l: "Hijau",
                              v: `${fmtInt(sim.data.current_green_seconds)} ke ${fmtInt(
                                sim.data.proposed_green_seconds,
                              )} dtk`,
                            },
                            {
                              l: "Risiko",
                              v: `${fmtPct(sim.data.risk_before)} ke ${fmtPct(sim.data.risk_after)}`,
                            },
                          ].map((r) => (
                            <div key={r.l} className="flex justify-between gap-3 text-micro">
                              <dt className="text-ink-muted">{r.l}</dt>
                              <dd className="num text-ink">{r.v}</dd>
                            </div>
                          ))}
                          <p className="text-micro text-ink-muted">{sim.data.summary}</p>
                        </dl>
                      )}
                    </div>
                  )}
                </section>

                <section className="space-y-2">
                  <h3 className="label-caps">3 Sinyal Terkuat</h3>
                  {detail.isLoading ? (
                    <StateBlock state="loading" height={DOCK_H} />
                  ) : detail.isError ? (
                    <StateBlock
                      state="error"
                      height={DOCK_H}
                      hint="Analitik penyebab simpang gagal dimuat"
                      onRetry={() => detail.refetch()}
                    />
                  ) : top3.length ? (
                    <div className="space-y-2">
                      <ul className="space-y-1.5">
                        {top3.map((t) => (
                          <li key={t.cause} className="flex items-center justify-between gap-2">
                            <CauseBadge cause={t.cause} size="sm" />
                            <span className="num text-micro text-ink-soft">
                              {fmtPct(t.probability)}
                            </span>
                          </li>
                        ))}
                      </ul>
                      {detailData?.probabilities && (
                        <ProbabilityBar probabilities={detailData.probabilities} />
                      )}
                      {detailData?.model_available === false && (
                        <p className="text-micro text-ink-muted">
                          Model belum tersedia — probabilitas dari aturan fallback
                        </p>
                      )}
                    </div>
                  ) : (
                    <StateBlock
                      state="empty"
                      height={DOCK_H}
                      emptyText="Diagnosa belum tersedia"
                      hint="Simpang ini belum punya hasil klasifikasi"
                    />
                  )}
                </section>
              </div>
            </aside>
          )}
        </div>

        {/* ── kolom kanan: daftar simpang, menciut jadi rail ikon saat dock terbuka ── */}
        <aside
          className={cn(
            "flex h-[560px] shrink-0 flex-col overflow-hidden rounded-card border border-line bg-surface lg:h-[620px]",
            selected ? "w-full lg:w-rail" : "w-full lg:w-80",
          )}
        >
          {selected ? (
            <div className="flex flex-1 flex-col items-center gap-1 overflow-y-auto py-2">
              {rows.map((r) => {
                const meta = causeMeta(r.cause ?? "normal");
                return (
                  <button
                    key={r.ix.intersection_id}
                    type="button"
                    title={`${r.ix.intersection_name} · ${meta.label}`}
                    aria-label={`${r.ix.intersection_name} · ${meta.label}`}
                    onClick={() => openDock(r.ix.intersection_id)}
                    className={cn(
                      "flex h-11 w-11 items-center justify-center rounded-control border transition-colors duration-150",
                      r.ix.intersection_id === selectedId
                        ? "border-primary bg-primary-quiet"
                        : "border-line bg-raised hover:border-line-strong",
                    )}
                  >
                    <Icon name={meta.icon} size={16} style={{ color: meta.color }} />
                  </button>
                );
              })}
            </div>
          ) : (
            <>
              <PanelHead
                title="Daftar Simpang Terpantau"
                sub="Klik baris untuk menyorot titik di peta"
                icon="map"
                right={<StatusPill tone="ok" label="LIVE 1s" />}
              />
              <div className="flex-1 overflow-y-auto p-3">
                {listState === "ready" ? (
                  <ul className="space-y-2">
                    {visible.map((r) => {
                      const meta = causeMeta(r.cause ?? "normal");
                      return (
                        <li key={r.ix.intersection_id}>
                          <button
                            type="button"
                            aria-pressed={r.ix.intersection_id === selectedId}
                            onClick={() => openDock(r.ix.intersection_id)}
                            style={{ borderLeftColor: meta.color }}
                            className="w-full rounded-control border border-l-[3px] border-line bg-raised px-3 py-2.5 text-left transition-colors duration-150 hover:border-line-strong"
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className="truncate text-cell font-semibold text-ink">
                                    {r.ix.intersection_name}
                                  </span>
                                  <span className="num shrink-0 text-micro text-ink-muted">
                                    [{r.ix.intersection_id}]
                                  </span>
                                </div>
                                <span className="text-micro text-ink-muted">
                                  {tipeLabel(r.tipe)} · {fmtInt(r.lengan)} lengan
                                </span>
                              </div>
                              {r.los ? <LosBadge los={r.los} /> : <StatusPill tone="idle" label="LOS —" />}
                            </div>
                            <div className="mt-2">
                              <CauseBadge
                                cause={r.cause ?? "normal"}
                                confidence={r.confidence}
                                size="sm"
                              />
                            </div>
                            <dl className="mt-2 grid grid-cols-2 gap-2 border-t border-line pt-2">
                              <div>
                                <dt className="label-caps">Arus</dt>
                                <dd className="num text-cell text-ink">
                                  {fmtInt(r.arusSmp)}
                                  <span className="ml-1 text-micro font-normal text-ink-muted">
                                    smp/jam
                                  </span>
                                </dd>
                              </div>
                              <div>
                                <dt className="label-caps">Antrean</dt>
                                <dd className="num text-cell text-ink">
                                  {fmtInt(r.antreanKend)}
                                  <span className="ml-1 text-micro font-normal text-ink-muted">
                                    {r.antreanM != null ? `kend (${fmtInt(r.antreanM)} m)` : "kend"}
                                  </span>
                                </dd>
                              </div>
                            </dl>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <StateBlock
                    state={listState}
                    height={LIST_H}
                    emptyText="Tidak ada simpang pada filter ini"
                    hint={
                      causeFilter
                        ? `Penyebab ${causeMeta(causeFilter).label} belum terdeteksi`
                        : undefined
                    }
                    onRetry={() => {
                      refetch();
                      refetchBn();
                    }}
                  />
                )}
              </div>
            </>
          )}
        </aside>
      </div>

      {/* ── heat strip 24 jam ── */}
      <Card pad={false} className="overflow-hidden">
        <PanelHead
          title="Riwayat 24 Jam Diagnosa Simpang"
          sub="1 blok = 1 jam · replay tick menit"
          icon="clock"
          right={
            <Btn variant="ghost" icon="refresh" onClick={() => setPlayhead(playheadNow())}>
              Sekarang
            </Btn>
          }
        />
        <div className="p-4">
          {heatRows.length ? (
            <HeatStrip rows={heatRows} playhead={playhead} onScrub={setPlayhead} />
          ) : (
            <StateBlock
              state={heatState}
              height={HEAT_H}
              emptyText="Riwayat 24 jam belum tersedia"
              hint={
                selectedId
                  ? "Simpang ini belum punya cuplikan history"
                  : "Pilih simpang untuk memuat history"
              }
              onRetry={selectedId ? () => detail.refetch() : undefined}
            />
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-micro text-ink-muted">
            <span className="num">
              {String(hourIdx).padStart(2, "0")}:00 WIB · jam tinjauan {fmtNum((playhead / 100) * 24, 1)}
            </span>
            {hourPoint ? (
              <>
                <CauseBadge cause={hourPoint.dominant_cause} size="sm" />
                {hourPoint.confidence != null && <Confidence value={hourPoint.confidence} />}
                {hourPoint.vc_ratio != null && (
                  <span className="num">V/C {fmtNum(hourPoint.vc_ratio, 2)}</span>
                )}
              </>
            ) : (
              <span>Tidak ada cuplikan pada jam ini</span>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};
