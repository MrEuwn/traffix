import { useMemo, useState } from "react";
import { useSegments, useSegmentsSummary } from "../../hooks/useTraffixData";
import {
  CARD,
  CAUSE_COLOR,
  causeLabel,
  fmtInt,
  fmtNum,
  fmtPct,
  losStyle,
} from "../../lib/format";
import { PanelHeader, PanelState } from "./Panel";
import type { SegmentItem, SegmentVehicleMix } from "../../types";

const VEH = [
  { key: "roda_2" as const, label: "R2", color: "var(--blue)" },
  { key: "roda_3" as const, label: "R3", color: "#a3e635" },
  { key: "roda_4" as const, label: "R4", color: "var(--yellow)" },
  { key: "roda_6plus" as const, label: "R6+", color: "var(--orange)" },
];

const shares = (mix: SegmentVehicleMix) => {
  const total = mix.total || 0;
  return VEH.map((v) => ({
    ...v,
    count: mix[v.key] ?? 0,
    share: mix.persen?.[v.key] ?? (total ? (mix[v.key] ?? 0) / total : 0),
  }));
};

const StackedBar = ({ mix, height = 6 }: { mix: SegmentVehicleMix; height?: number }) => (
  <div
    style={{
      display: "flex",
      height,
      borderRadius: 3,
      overflow: "hidden",
      background: "var(--border)",
      width: "100%",
    }}
  >
    {shares(mix).map((v) => (
      <div
        key={v.key}
        title={`${v.label}: ${fmtInt(v.count)} (${fmtPct(v.share)})`}
        style={{ width: `${Math.max(v.share, 0) * 100}%`, background: v.color }}
      />
    ))}
  </div>
);

const MixCell = ({ mix }: { mix: SegmentVehicleMix }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 168 }}>
    <StackedBar mix={mix} />
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 3 }}>
      {shares(mix).map((v) => (
        <div key={v.key}>
          <p style={{ fontSize: 9, color: v.color, fontWeight: 600 }}>{v.label}</p>
          <p style={{ fontSize: 10, color: "var(--text-secondary)" }}>{fmtInt(v.count)}</p>
          <p style={{ fontSize: 9, color: "var(--text-dim)" }}>{fmtPct(v.share)}</p>
        </div>
      ))}
    </div>
  </div>
);

type SortKey = keyof Pick<
  SegmentItem,
  | "nama_ruas"
  | "panjang_m"
  | "jumlah_lajur"
  | "kapasitas_kendaraan"
  | "kapasitas_smp_per_jam"
  | "volume_veh_per_hour"
  | "vc_ratio"
  | "los"
  | "avg_speed_kmh"
  | "queue_length_veh"
>;

const COLS: { key: SortKey; label: string; align?: "right" }[] = [
  { key: "nama_ruas", label: "Ruas" },
  { key: "panjang_m", label: "Panjang" },
  { key: "jumlah_lajur", label: "Lajur" },
  { key: "kapasitas_kendaraan", label: "Kapasitas (kend)" },
  { key: "kapasitas_smp_per_jam", label: "Kapasitas (smp/jam)" },
  { key: "volume_veh_per_hour", label: "Volume" },
  { key: "vc_ratio", label: "V/C" },
  { key: "los", label: "LOS" },
  { key: "avg_speed_kmh", label: "Kec." },
  { key: "queue_length_veh", label: "Antrean" },
];

export const SegmentTable = () => {
  const { data, isLoading, isError } = useSegments();
  const { data: summary } = useSegmentsSummary();
  const [q, setQ] = useState("");
  const [type, setType] = useState("all");
  const [los, setLos] = useState("all");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "vc_ratio", dir: -1 });

  const items = useMemo(() => data?.items ?? [], [data]);

  const rows = useMemo(() => {
    const t = q.trim().toLowerCase();
    const filtered = items.filter(
      (s) =>
        (type === "all" || s.section_type === type) &&
        (los === "all" || s.los === los) &&
        (!t ||
          s.nama_ruas.toLowerCase().includes(t) ||
          s.section_id.toLowerCase().includes(t)),
    );
    return [...filtered].sort((a, b) => {
      const x = a[sort.key];
      const y = b[sort.key];
      if (typeof x === "string" && typeof y === "string") return sort.dir * x.localeCompare(y);
      return sort.dir * ((x as number) - (y as number));
    });
  }, [items, q, type, los, sort]);

  const toggle = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: -1 }));

  const fleet = summary?.total_kendaraan;

  return (
    <div style={CARD}>
      <PanelHeader
        icon="🛣"
        title="Ruas Jalan & Komposisi Kendaraan"
        sub={
          data
            ? `${fmtInt(data.count)} ruas · tick ${fmtInt(data.tick)}`
            : "30 ruas pendekat + koridor"
        }
      />

      {(isLoading || isError || !data) && <PanelState kind={isLoading ? "loading" : "error"} />}

      {data && (
        <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
          {/* summary strip */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 8 }}>
            {[
              { l: "Jumlah ruas", v: fmtInt(summary?.section_count ?? data.count) },
              {
                l: "Pendekat / koridor",
                v: summary ? `${fmtInt(summary.approach_count)} / ${fmtInt(summary.corridor_count)}` : "—",
              },
              { l: "Kapasitas kendaraan", v: fmtInt(summary?.total_capacity_vehicles ?? data.total_capacity_vehicles) },
              { l: "Kapasitas smp/jam", v: fmtInt(summary?.total_capacity_smp_per_jam) },
              { l: "Rata-rata V/C", v: fmtNum(summary?.avg_vc_ratio, 2) },
              { l: "Rata-rata kecepatan", v: `${fmtNum(summary?.avg_speed_kmh, 1)} km/h` },
            ].map((s) => (
              <div key={s.l} style={{ background: "var(--bg-elevated)", borderRadius: 8, padding: "8px 10px" }}>
                <p style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: ".06em" }}>
                  {s.l}
                </p>
                <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>{s.v}</p>
              </div>
            ))}
          </div>

          {/* komposisi armada total */}
          {fleet && (
            <div style={{ background: "var(--bg-elevated)", borderRadius: 8, padding: 10 }}>
              <p style={{ fontSize: 9, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 7 }}>
                Komposisi armada · {fmtInt(fleet.total)} kendaraan · {fmtNum(fleet.smp_ekivalen, 0)} smp
              </p>
              <StackedBar mix={fleet} height={7} />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 6, marginTop: 7 }}>
                {shares(fleet).map((v) => (
                  <div key={v.key}>
                    <p style={{ fontSize: 10, color: v.color, fontWeight: 600 }}>
                      {v.label} <span style={{ color: "var(--text-dim)" }}>· {fmtPct(v.share)}</span>
                    </p>
                    <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>{fmtInt(v.count)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* kontrol filter */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Cari ruas / section id…"
              style={{
                flex: 1,
                minWidth: 170,
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 7,
                padding: "6px 9px",
                fontSize: 11,
                color: "var(--text-secondary)",
                outline: "none",
              }}
            />
            {[
              { v: type, set: setType, opts: ["all", "approach", "corridor"], labels: ["Semua tipe", "Pendekat", "Koridor"] },
              { v: los, set: setLos, opts: ["all", "A", "B", "C", "D", "E", "F"], labels: ["Semua LOS", "LOS A", "LOS B", "LOS C", "LOS D", "LOS E", "LOS F"] },
            ].map((sel, i) => (
              <select
                key={i}
                value={sel.v}
                onChange={(e) => sel.set(e.target.value)}
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  borderRadius: 7,
                  padding: "6px 9px",
                  fontSize: 11,
                  color: "var(--text-secondary)",
                }}
              >
                {sel.opts.map((o, j) => (
                  <option key={o} value={o}>
                    {sel.labels[j]}
                  </option>
                ))}
              </select>
            ))}
            <span style={{ fontSize: 10, color: "var(--text-dim)" }}>
              {fmtInt(rows.length)} dari {fmtInt(items.length)} ruas
            </span>
          </div>

          {/* tabel */}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr>
                  {COLS.map((c) => (
                    <th
                      key={c.key}
                      onClick={() => toggle(c.key)}
                      style={{
                        textAlign: "left",
                        padding: "6px 8px",
                        fontSize: 9,
                        textTransform: "uppercase",
                        letterSpacing: ".06em",
                        color: sort.key === c.key ? "var(--text-secondary)" : "var(--text-dim)",
                        cursor: "pointer",
                        whiteSpace: "nowrap",
                        borderBottom: "1px solid var(--border)",
                      }}
                    >
                      {c.label}
                      {sort.key === c.key ? (sort.dir === -1 ? " ▼" : " ▲") : ""}
                    </th>
                  ))}
                  <th
                    style={{
                      textAlign: "left",
                      padding: "6px 8px",
                      fontSize: 9,
                      textTransform: "uppercase",
                      letterSpacing: ".06em",
                      color: "var(--text-dim)",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    Komposisi roda
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => {
                  const ls = losStyle(s.los);
                  return (
                    <tr key={s.section_id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "7px 8px", verticalAlign: "top" }}>
                        <p style={{ color: "var(--text-secondary)" }}>{s.nama_ruas}</p>
                        <p style={{ fontSize: 9, color: "var(--text-dim)" }}>
                          {s.section_id} · {s.section_type}
                          {s.approach ? ` · ${s.approach}` : ""} · {s.intersection_id}
                        </p>
                        <p style={{ fontSize: 9, color: CAUSE_COLOR[s.bottleneck_cause] ?? "var(--text-dim)" }}>
                          {causeLabel(s.penyebab_dominan || s.bottleneck_cause)}
                        </p>
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-muted)", verticalAlign: "top" }}>
                        {fmtInt(s.panjang_m)} m
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-muted)", verticalAlign: "top" }}>
                        {fmtInt(s.jumlah_lajur)}
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-primary)", verticalAlign: "top" }}>
                        {fmtInt(s.kapasitas_kendaraan)}
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-muted)", verticalAlign: "top" }}>
                        {fmtInt(s.kapasitas_smp_per_jam)}
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-secondary)", verticalAlign: "top" }}>
                        {fmtInt(s.volume_veh_per_hour)}
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", verticalAlign: "top" }}>
                        <span style={{ color: s.vc_ratio >= 1 ? "var(--red)" : s.vc_ratio >= 0.85 ? "var(--orange)" : "var(--text-secondary)" }}>
                          {fmtNum(s.vc_ratio, 2)}
                        </span>
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", verticalAlign: "top" }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "1px 6px",
                            borderRadius: 4,
                            color: ls.color,
                            background: ls.bg,
                            border: `1px solid ${ls.border}`,
                          }}
                        >
                          {s.los}
                        </span>
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-muted)", verticalAlign: "top" }}>
                        {fmtNum(s.avg_speed_kmh, 1)}
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-muted)", verticalAlign: "top" }}>
                        {fmtInt(s.queue_length_veh)}
                      </td>
                      <td style={{ padding: "7px 8px", verticalAlign: "top" }}>
                        <MixCell mix={s.kendaraan} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* sebaran LOS */}
          {summary?.los_distribution && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {Object.entries(summary.los_distribution).map(([k, v]) => {
                const ls = losStyle(k);
                return (
                  <span
                    key={k}
                    style={{
                      fontSize: 10,
                      padding: "2px 8px",
                      borderRadius: 20,
                      color: ls.color,
                      background: ls.bg,
                      border: `1px solid ${ls.border}`,
                    }}
                  >
                    LOS {k}: {fmtInt(v)} ruas
                  </span>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
