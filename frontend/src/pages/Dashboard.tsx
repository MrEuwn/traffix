import { useMemo, useState } from "react";
import {
  useBottlenecks,
  useIntersections,
  useRecommendations,
  useSegments,
  useSegmentsSummary,
  useSignalsSummary,
  useSystemStatus,
  useWeather,
} from "../hooks/useTraffixData";
import { KpiCard, SeedBadge, StateBlock, StatusPill, useToast } from "../components/ui";
import { DiagnosisPanel } from "../components/dashboard/DiagnosisPanel";
import { SignalTimingCard } from "../components/dashboard/SignalTimingCard";
import { IntersectionList } from "../components/dashboard/IntersectionList";
import { BottleneckPanel } from "../components/dashboard/BottleneckPanel";
import { HistoryStrip } from "../components/dashboard/HistoryStrip";
import { SegmentTable } from "../components/dashboard/SegmentTable";
import { AuditTrail, type AuditEntry } from "../components/dashboard/AuditTrail";
import { fmtInt, fmtNum } from "../lib/format";
import { weatherLabel, wibClock, wibHm } from "../components/dashboard/format";
import { useAuth } from "../lib/AuthContext";

/* Ambang operator (bukan data): kecepatan padat < 35 km/jam, tunggu > 2,5 menit, V/C jenuh >= 1. */
const SPEED_WARN = 35;
const SPEED_CRIT = 20;
const WAIT_WARN_MIN = 1.5;
const WAIT_CRIT_MIN = 2.5;
const VC_WARN = 0.85;
const VC_CRIT = 1;

type Tone = "idle" | "ok" | "warn" | "crit";

const toneBelow = (value: number | null | undefined, warn: number, crit: number): Tone =>
  value == null ? "idle" : value < crit ? "crit" : value < warn ? "warn" : "ok";

const toneFromVc = (value: number | null | undefined): Tone =>
  value == null ? "idle" : value >= VC_CRIT ? "crit" : value >= VC_WARN ? "warn" : "ok";

/** Ruang kendali: KPI jaringan, diagnosis penyebab, waktu lampu, daftar simpang,
    riwayat, tabel ruas, dan jejak audit intervensi operator. */
export const Dashboard = () => {
  const {
    data: intersections = [],
    isLoading: ixLoading,
    isError: ixError,
    refetch: refetchIx,
  } = useIntersections();
  const { data: bottlenecks } = useBottlenecks();
  const { data: recommendations = [] } = useRecommendations();
  const { data: segments, isLoading: segItemsLoading, isError: segItemsError } = useSegments();
  const {
    data: summary,
    isLoading: sumLoading,
    isError: sumError,
    refetch: refetchSummary,
  } = useSegmentsSummary();
  const {
    data: signals,
    isLoading: sigLoading,
    isError: sigError,
    refetch: refetchSignals,
  } = useSignalsSummary("all");
  const { data: weather } = useWeather();
  const { data: status } = useSystemStatus();
  const { user } = useAuth();
  const toast = useToast();

  const [selectedId, setSelectedId] = useState<string>("");
  const [entries, setEntries] = useState<AuditEntry[]>([]);

  const items = useMemo(() => segments?.items ?? [], [segments]);
  const diag = useMemo(() => bottlenecks?.per_intersection ?? [], [bottlenecks]);

  /* Simpang fokus: pilihan operator, jika tidak ada -> keyakinan penyebab non-normal tertinggi. */
  const targetId = useMemo(() => {
    if (selectedId) return selectedId;
    if (!diag.length) return intersections[0]?.intersection_id ?? "";
    const abnormal = diag.filter((d) => d.dominant_cause !== "normal");
    const pool = abnormal.length ? abnormal : diag;
    return pool.reduce((best, d) => (d.confidence > best.confidence ? d : best)).intersection_id;
  }, [selectedId, diag, intersections]);

  const targetName =
    intersections.find((ix) => ix.intersection_id === targetId)?.intersection_name ??
    diag.find((d) => d.intersection_id === targetId)?.intersection_name ??
    targetId;

  const arusSmp = summary?.total_kendaraan?.smp_ekivalen ?? null;
  const speed = summary?.avg_speed_kmh ?? null;
  const queueKend = items.length
    ? items.reduce((sum, s) => sum + (s.queue_length_veh ?? 0), 0)
    : null;

  const scopeWait = (scope: "perempatan" | "pertigaan") =>
    signals?.items?.find((i) => i.scope === scope)?.avg_wait_time_min ?? null;
  const waitFour = scopeWait("perempatan");
  const waitThree = scopeWait("pertigaan");
  /* Rata-rata semua simpang = rata-rata agregat perempatan + pertigaan. */
  const waitAll =
    waitFour != null && waitThree != null
      ? (waitFour + waitThree) / 2
      : (signals?.avg_wait_time_min ?? null);

  const kpiLoading = sumLoading || sigLoading || segItemsLoading;
  const kpiError = sumError && sigError && segItemsError;

  const handleApply = ({ action, detail }: { action: string; detail: string }) => {
    const entry: AuditEntry = {
      id: `${Date.now()}`,
      time: wibClock(),
      action,
      operator: user?.username ?? "Operator",
      detail,
    };
    setEntries((prev) => [entry, ...prev]);
    toast.push({
      message: "Perubahan diterapkan",
      action: {
        label: "Urungkan",
        run: () => {
          setEntries((prev) => [
            {
              id: `${Date.now()}-undo`,
              time: wibClock(),
              action: `Urungkan · ${action}`,
              operator: user?.username ?? "Operator",
              detail: "Perubahan simulasi dibatalkan operator",
            },
            ...prev,
          ]);
          toast.push({ message: "Perubahan diurungkan" });
        },
      },
    });
  };

  const weatherLine = weather
    ? `${weatherLabel(weather.condition)} · ${fmtNum(weather.temperature_celsius, 1)} °C · RH ${fmtInt(
        weather.humidity_percent,
      )} %`
    : null;

  return (
    <div className="flex flex-col gap-3">
      {/* ── Konteks: waktu replay, cuaca, status layanan ── */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-title-sm font-semibold text-ink">Ruang kendali lalu lintas</h1>
          <p className="mt-0.5 text-micro text-ink-muted">
            tick {fmtInt(bottlenecks?.tick)} · {wibHm(bottlenecks?.timestamp_wib)} WIB
            {weatherLine ? ` · ${weatherLine}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill
            tone={status?.ml_ready ? "ok" : "idle"}
            label={status?.ml_mode ?? "ML memuat"}
            icon="chart"
          />
          <StatusPill
            tone={status?.simulation_active ? "ok" : "idle"}
            label={status?.simulation_active ? "Simulasi jalan" : "Simulasi berhenti"}
            icon="play"
          />
          <StatusPill
            tone={status?.dataset_ready ? "ok" : "idle"}
            label="Dataset v4"
            icon="layers"
          />
          <SeedBadge />
        </div>
      </header>

      {/* ── (1) KPI jaringan ── */}
      {kpiLoading ? (
        <StateBlock state="loading" height={96} />
      ) : kpiError ? (
        <StateBlock
          state="error"
          height={96}
          hint="Endpoint segments/summary dan signals/summary tidak merespons."
          onRetry={() => {
            refetchSummary();
            refetchSignals();
          }}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            label="Arus jaringan"
            value={fmtInt(arusSmp)}
            unit="smp/jam"
            context={`${fmtInt(summary?.section_count)} ruas · ${fmtInt(
              summary?.approach_count,
            )} pendekat · ${fmtInt(summary?.corridor_count)} koridor`}
            tone={toneFromVc(summary?.avg_vc_ratio)}
          />
          <KpiCard
            label="Kecepatan rata-rata"
            value={fmtNum(speed, 1)}
            unit="km/jam"
            context={`ambang padat ${fmtNum(SPEED_WARN, 1)} km/jam`}
            tone={toneBelow(speed, SPEED_WARN, SPEED_CRIT)}
          />
          <KpiCard
            label="Antrean total"
            value={fmtInt(queueKend)}
            unit="kend"
            context={`${fmtInt(items.length)} ruas · V/C ${fmtNum(summary?.avg_vc_ratio, 2)}`}
            tone={toneFromVc(summary?.avg_vc_ratio)}
          />
          <KpiCard
            label="Waktu tunggu"
            value={fmtNum(waitAll, 2)}
            unit="menit"
            context={`4-lengan ${fmtNum(waitFour, 2)} · 3-lengan ${fmtNum(waitThree, 2)} menit`}
            tone={
              waitAll == null
                ? "idle"
                : waitAll >= WAIT_CRIT_MIN
                  ? "crit"
                  : waitAll >= WAIT_WARN_MIN
                    ? "warn"
                    : "ok"
            }
          />
        </div>
      )}

      <div className="grid gap-3 xl:grid-cols-3">
        <div className="flex flex-col gap-3 xl:col-span-2">
          {/* ── (2) + (7) Diagnosis hero & persetujuan rekomendasi ── */}
          <DiagnosisPanel intersectionId={targetId} onApply={handleApply} />

          {/* ── (4) Daftar simpang ── */}
          {ixError && !intersections.length ? (
            <StateBlock
              state="error"
              height={176}
              hint="Endpoint /api/v1/intersections tidak merespons."
              onRetry={() => refetchIx()}
            />
          ) : ixLoading && !intersections.length ? (
            <StateBlock state="loading" height={176} />
          ) : (
            <IntersectionList
              intersections={intersections}
              bottleneck={diag}
              items={items}
              recommendations={recommendations}
              selectedId={targetId}
              onSelect={setSelectedId}
            />
          )}

          {/* ── Sebaran penyebab jaringan (30 ruas) ── */}
          <BottleneckPanel />
        </div>

        <div className="flex flex-col gap-3">
          {/* ── (3) Waktu lampu ── */}
          <SignalTimingCard />

          {/* ── (6) Riwayat 24 jam dengan scrub ── */}
          {targetId ? (
            <HistoryStrip intersectionId={targetId} name={targetName} />
          ) : (
            <StateBlock state="empty" height={176} emptyText="Belum ada simpang terpilih" />
          )}

          {/* ── (7) Jejak audit ── */}
          <AuditTrail entries={entries} />
        </div>
      </div>

      {/* ── (5) Tabel ruas ── */}
      <SegmentTable />
    </div>
  );
};
