import { useSignalsSummary } from "../../hooks/useTraffixData";
import { CARD, fmtInt, fmtNum } from "../../lib/format";
import { PanelHeader, PanelState } from "./Panel";
import type { SignalPerIntersection } from "../../types";

/** Agregat per scope: pakai `items` bila ada, jika tidak hitung dari per_intersection. */
const groupAvg = (rows: SignalPerIntersection[]) => {
  if (!rows.length) return null;
  const mean = (pick: (r: SignalPerIntersection) => number) =>
    rows.reduce((s, r) => s + (pick(r) || 0), 0) / rows.length;
  return {
    intersection_count: rows.length,
    cycle_length_s: mean((r) => r.cycle_length_s),
    avg_green_s: mean((r) => r.avg_green_s),
    avg_red_s: mean((r) => r.avg_red_s),
    avg_wait_time_min: mean((r) => r.avg_wait_time_min),
    avg_queue_veh: mean((r) => r.avg_queue_veh),
    avg_delay_s: mean((r) => r.avg_delay_s),
  };
};

type Agg = {
  intersection_count: number;
  cycle_length_s: number;
  avg_green_s: number;
  avg_red_s: number;
  avg_wait_time_min: number;
  avg_queue_veh: number;
  avg_delay_s: number;
};

const StatRow = ({ label, agg, accent }: { label: string; agg: Agg; accent?: string }) => (
  <div
    style={{
      background: "var(--bg-elevated)",
      borderRadius: 8,
      padding: "9px 10px",
      display: "flex",
      flexDirection: "column",
      gap: 6,
    }}
  >
    <p style={{ fontSize: 10, fontWeight: 600, color: accent ?? "var(--text-muted)" }}>
      {label}
      <span style={{ fontWeight: 400, color: "var(--text-dim)" }}>
        {" "}
        · {fmtInt(agg.intersection_count)} simpang
      </span>
    </p>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 6 }}>
      {[
        { l: "Siklus", v: `${fmtNum(agg.cycle_length_s, 0)} s`, c: "var(--text-primary)" },
        { l: "Hijau", v: `${fmtNum(agg.avg_green_s, 1)} s`, c: "var(--green)" },
        { l: "Merah", v: `${fmtNum(agg.avg_red_s, 1)} s`, c: "var(--red)" },
        { l: "Tunggu", v: `${fmtNum(agg.avg_wait_time_min, 2)} mnt`, c: "var(--yellow)" },
        { l: "Antrean", v: `${fmtNum(agg.avg_queue_veh, 1)} kend`, c: "var(--orange)" },
        { l: "Tundaan", v: `${fmtNum(agg.avg_delay_s, 1)} s`, c: "var(--blue)" },
      ].map((m) => (
        <div key={m.l}>
          <p style={{ fontSize: 9, color: "var(--text-dim)" }}>{m.l}</p>
          <p style={{ fontSize: 13, fontWeight: 600, color: m.c }}>{m.v}</p>
        </div>
      ))}
    </div>
  </div>
);

export const SignalTimingCard = () => {
  const { data, isLoading, isError } = useSignalsSummary("all");

  const per = data?.per_intersection ?? [];
  const items = data?.items ?? [];
  const agg = (scope: "perempatan" | "pertigaan"): Agg | null =>
    items.find((i) => i.scope === scope) ??
    groupAvg(per.filter((p) => p.tipe_persimpangan === scope));

  const empat = agg("perempatan");
  const tiga = agg("pertigaan");

  return (
    <div style={CARD}>
      <PanelHeader
        icon="🚦"
        title="Rata-rata Waktu Lampu"
        sub={data ? `${fmtInt(data.section_count)} pendekat ber-lampu · ${data.timestamp_wib}` : "agregat siklus sinyal"}
      />

      {(isLoading || isError || !data) && <PanelState kind={isLoading ? "loading" : "error"} />}

      {data && (
        <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
          {/* gabungan semua simpang */}
          <StatRow
            label="Semua simpang ber-lampu"
            accent="var(--blue)"
            agg={{
              intersection_count: data.intersection_count,
              cycle_length_s: data.cycle_length_s,
              avg_green_s: data.avg_green_s,
              avg_red_s: data.avg_red_s,
              avg_wait_time_min: data.avg_wait_time_min,
              avg_queue_veh: data.avg_queue_veh,
              avg_delay_s: data.avg_delay_s,
            }}
          />

          {/* perbandingan perempatan vs pertigaan */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 9 }}>
            {empat && <StatRow label="Perempatan (4 lengan)" accent="var(--purple)" agg={empat} />}
            {tiga && <StatRow label="Pertigaan (3 lengan)" accent="var(--blue)" agg={tiga} />}
          </div>

          {/* rincian per simpang */}
          {!!per.length && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                <thead>
                  <tr style={{ color: "var(--text-dim)", textAlign: "right" }}>
                    <th style={{ textAlign: "left", padding: "5px 6px", fontWeight: 500 }}>Simpang</th>
                    <th style={{ padding: "5px 6px", fontWeight: 500 }}>Siklus</th>
                    <th style={{ padding: "5px 6px", fontWeight: 500 }}>Hijau</th>
                    <th style={{ padding: "5px 6px", fontWeight: 500 }}>Merah</th>
                    <th style={{ padding: "5px 6px", fontWeight: 500 }}>Tunggu</th>
                    <th style={{ padding: "5px 6px", fontWeight: 500 }}>Antrean</th>
                    <th style={{ padding: "5px 6px", fontWeight: 500 }}>Tundaan</th>
                  </tr>
                </thead>
                <tbody>
                  {per.map((p) => (
                    <tr key={p.intersection_id} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "6px", color: "var(--text-secondary)" }}>
                        {p.intersection_name}
                        <span style={{ color: "var(--text-dim)" }}>
                          {" "}
                          · {p.tipe_persimpangan} · {fmtInt(p.jumlah_lengan)} lengan
                        </span>
                      </td>
                      <td style={{ padding: "6px", textAlign: "right", color: "var(--text-muted)" }}>
                        {fmtNum(p.cycle_length_s, 0)} s
                      </td>
                      <td style={{ padding: "6px", textAlign: "right", color: "var(--green)" }}>
                        {fmtNum(p.avg_green_s, 1)} s
                      </td>
                      <td style={{ padding: "6px", textAlign: "right", color: "var(--red)" }}>
                        {fmtNum(p.avg_red_s, 1)} s
                      </td>
                      <td style={{ padding: "6px", textAlign: "right", color: "var(--yellow)" }}>
                        {fmtNum(p.avg_wait_time_min, 2)} mnt
                      </td>
                      <td style={{ padding: "6px", textAlign: "right", color: "var(--orange)" }}>
                        {fmtNum(p.avg_queue_veh, 1)}
                      </td>
                      <td style={{ padding: "6px", textAlign: "right", color: "var(--blue)" }}>
                        {fmtNum(p.avg_delay_s, 1)} s
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
