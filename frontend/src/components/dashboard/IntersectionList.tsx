import { useMemo, useState } from "react";
import {
  Card,
  CauseBadge,
  Chip,
  LosBadge,
  PanelHead,
  SeedBadge,
  StateBlock,
  StatusPill,
} from "../ui";
import { fmtInt } from "../../lib/format";
import { PanelState } from "./Panel";
import type {
  BottleneckPerIntersection,
  Intersection,
  Recommendation,
  SegmentItem,
} from "../../types";

const LOS_RANK: Record<string, number> = { A: 0, B: 1, C: 2, D: 3, E: 4, F: 5 };

const worstLos = (rows: SegmentItem[]) =>
  rows.reduce<string>((acc, row) => ((LOS_RANK[row.los] ?? 0) > (LOS_RANK[acc] ?? 0) ? row.los : acc), "A");

const PRIORITY_TONE: Record<string, "ok" | "warn" | "high" | "crit"> = {
  LOW: "ok",
  MEDIUM: "warn",
  HIGH: "high",
  CRITICAL: "crit",
};

type Row = {
  id: string;
  name: string;
  tipe: string;
  cause: string;
  confidence: number;
  modelAvailable: boolean;
  arusSmp: number | null;
  queueKend: number | null;
  los: string;
  rec: Recommendation | null;
};

type Filter = "all" | "perempatan" | "pertigaan";

/** Daftar simpang: peringkat antrean, penyebab dominan + keyakinan, arus, antrean, LOS. */
export const IntersectionList = ({
  intersections,
  bottleneck,
  items,
  recommendations,
  selectedId,
  onSelect,
}: {
  intersections: Intersection[];
  bottleneck: BottleneckPerIntersection[];
  items: SegmentItem[];
  recommendations: Recommendation[];
  selectedId: string;
  onSelect: (id: string) => void;
}) => {
  const [filter, setFilter] = useState<Filter>("all");

  const rows = useMemo<Row[]>(() => {
    const diag = new Map(bottleneck.map((b) => [b.intersection_id, b]));
    const ids = new Set<string>([
      ...intersections.map((ix) => ix.intersection_id),
      ...diag.keys(),
    ]);

    const all = [...ids].map((id) => {
      const live = intersections.find((ix) => ix.intersection_id === id);
      const d = diag.get(id);
      const sections = items.filter((s) => s.intersection_id === id);
      const arus = sections.reduce((sum, s) => sum + (s.kendaraan?.smp_ekivalen ?? 0), 0);
      const queue = sections.reduce((sum, s) => sum + (s.queue_length_veh ?? 0), 0);
      return {
        id,
        name: live?.intersection_name ?? d?.intersection_name ?? id,
        tipe: d?.tipe_persimpangan ?? sections[0]?.tipe_persimpangan ?? "—",
        cause: d?.dominant_cause ?? "normal",
        confidence: d?.confidence ?? 0,
        modelAvailable: d?.model_available !== false,
        arusSmp: sections.length ? arus : null,
        queueKend: sections.length ? queue : null,
        los: sections.length ? worstLos(sections) : "—",
        rec: recommendations.find((r) => r.intersection_id === id) ?? null,
      };
    });

    return all
      .filter((r) => filter === "all" || r.tipe === filter)
      .sort((a, b) => (b.queueKend ?? -1) - (a.queueKend ?? -1));
  }, [intersections, bottleneck, items, recommendations, filter]);

  const counts = {
    all: intersections.length,
    perempatan: bottleneck.filter((b) => b.tipe_persimpangan === "perempatan").length,
    pertigaan: bottleneck.filter((b) => b.tipe_persimpangan === "pertigaan").length,
  };

  const noData = !intersections.length && !bottleneck.length;

  return (
    <Card pad={false} className="flex flex-col">
      <PanelHead
        icon="map"
        title="Peringkat antrean simpang"
        sub={
          noData
            ? "menunggu telemetri simpang"
            : `${fmtInt(rows.length)} dari ${fmtInt(filter === "all" ? intersections.length || bottleneck.length : counts[filter])} simpang · diurut antrean`
        }
        right={<SeedBadge />}
      />

      {!noData && (
        <div className="flex flex-wrap gap-2 border-b border-line px-4 py-2.5">
          <Chip label="Semua" count={counts.all} active={filter === "all"} onClick={() => setFilter("all")} />
          <Chip
            label="Perempatan"
            count={counts.perempatan}
            active={filter === "perempatan"}
            onClick={() => setFilter("perempatan")}
          />
          <Chip
            label="Pertigaan"
            count={counts.pertigaan}
            active={filter === "pertigaan"}
            onClick={() => setFilter("pertigaan")}
          />
        </div>
      )}

      {noData ? (
        <PanelState kind="error" message="Endpoint /api/v1/intersections tidak merespons." />
      ) : (
        <div className="p-3">
          <div className="grid grid-cols-[1fr_auto] gap-3 px-1 pb-1.5">
            <span className="label-caps">Simpang · penyebab dominan</span>
            <span className="label-caps grid grid-cols-3 gap-3 text-right">
              <span>Arus smp/jam</span>
              <span>Antrean kend</span>
              <span>LOS</span>
            </span>
          </div>

          <ul className="space-y-2">
            {rows.map((row, index) => (
              <li key={row.id}>
                <button
                  type="button"
                  onClick={() => onSelect(row.id)}
                  aria-pressed={row.id === selectedId}
                  className={
                    "flex min-h-11 w-full items-start gap-3 rounded-control border px-3 py-2.5 text-left transition-colors duration-150 " +
                    (row.id === selectedId
                      ? "border-primary bg-primary-quiet"
                      : "border-line bg-raised hover:border-line-strong")
                  }
                >
                  <span className="num w-5 pt-0.5 text-micro text-ink-muted">{String(index + 1).padStart(2, "0")}</span>

                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-cell font-medium text-ink">{row.name}</span>
                      {row.rec && (
                        <StatusPill
                          tone={PRIORITY_TONE[row.rec.priority] ?? "idle"}
                          label={`prioritas ${row.rec.priority}`}
                        />
                      )}
                    </span>
                    <span className="mt-0.5 block text-micro text-ink-muted">
                      {row.id} · {row.tipe}
                    </span>
                    <span className="mt-1.5 block">
                      <CauseBadge
                        size="sm"
                        cause={row.cause}
                        confidence={row.modelAvailable && row.confidence > 0 ? row.confidence : undefined}
                      />
                    </span>
                  </span>

                  <span className="grid shrink-0 grid-cols-3 gap-3 text-right">
                    <span className="num text-cell text-ink">{fmtInt(row.arusSmp)}</span>
                    <span className="num text-cell text-ink">{fmtInt(row.queueKend)}</span>
                    <span className="pt-0.5">
                      {row.los === "—" ? (
                        <span className="text-micro text-ink-muted">—</span>
                      ) : (
                        <LosBadge los={row.los} />
                      )}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {rows.length === 0 && (
            <StateBlock
              state="empty"
              height={140}
              emptyText="Tidak ada simpang pada filter ini"
              hint="Pilih chip tipe lain"
            />
          )}
        </div>
      )}
    </Card>
  );
};
