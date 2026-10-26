import { useBottlenecks } from "../../hooks/useTraffixData";
import {
  BADGE_SINTETIS,
  CARD,
  CAUSE_COLOR,
  causeLabel,
  fmtInt,
  fmtNum,
  fmtPct,
} from "../../lib/format";
import { PanelHeader, PanelState } from "./Panel";
import type { BottleneckPerIntersection } from "../../types";

/** Bar probabilitas 9 kelas (terurut menurun). */
const ProbBar = ({ probs, cm = 6 }: { probs: Record<string, number>; cm?: number }) => {
  const entries = Object.entries(probs).sort((a, b) => b[1] - a[1]);
  if (!entries.length)
    return <div style={{ height: cm, background: "var(--border)", borderRadius: 3 }} />;
  return (
    <div
      style={{
        display: "flex",
        height: cm,
        borderRadius: 3,
        overflow: "hidden",
        background: "var(--border)",
      }}
    >
      {entries.map(([c, p]) => (
        <div
          key={c}
          title={`${causeLabel(c)} · ${fmtPct(p)}`}
          style={{
            width: `${Math.max(p, 0) * 100}%`,
            background: CAUSE_COLOR[c] ?? "var(--text-dim)",
          }}
        />
      ))}
    </div>
  );
};

const IntersectionRow = ({ ix }: { ix: BottleneckPerIntersection }) => {
  const probs =
    ix.probabilities && Object.keys(ix.probabilities).length
      ? ix.probabilities
      : Object.fromEntries((ix.top3 ?? []).map((t) => [t.cause, t.probability]));
  const color = CAUSE_COLOR[ix.dominant_cause] ?? "var(--text-dim)";
  const fallback = ix.model_available === false || !ix.confidence;

  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        borderRadius: 9,
        padding: 11,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
            {ix.intersection_name}
          </p>
          <p style={{ fontSize: 10, color: "var(--text-dim)" }}>
            {ix.intersection_id} · {ix.tipe_persimpangan}
            {fallback ? " · fallback aturan" : ""}
          </p>
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <span
            style={{
              fontSize: 9,
              fontWeight: 600,
              padding: "2px 7px",
              borderRadius: 4,
              color,
              background: "var(--bg-card)",
              border: `1px solid ${color}`,
            }}
          >
            {causeLabel(ix.dominant_cause)}
          </span>
          <p style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4 }}>
            keyakinan {fmtPct(ix.confidence)}
          </p>
        </div>
      </div>

      <ProbBar probs={probs} />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {(ix.top3 ?? []).slice(0, 3).map((t) => (
          <span
            key={t.cause}
            style={{
              fontSize: 9,
              color: "var(--text-muted)",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 20,
              padding: "1px 7px",
            }}
          >
            {causeLabel(t.cause)} {fmtPct(t.probability, 1)}
          </span>
        ))}
      </div>

      {!!(ix.drivers ?? []).length && (
        <ul
          style={{
            listStyle: "none",
            display: "flex",
            flexDirection: "column",
            gap: 3,
            borderTop: "1px solid var(--border)",
            paddingTop: 7,
          }}
        >
          {ix.drivers.map((d) => (
            <li key={d} style={{ fontSize: 10, color: "var(--text-dim)", lineHeight: 1.45 }}>
              • {d}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export const BottleneckPanel = () => {
  const { data, isLoading, isError } = useBottlenecks();

  return (
    <div style={CARD}>
      <PanelHeader
        icon="🧩"
        title="Penyebab Bottleneck"
        sub={data ? `tick ${fmtInt(data.tick)} · ${data.timestamp_wib}` : "klasifikasi 9 kelas penyebab"}
        right={<span style={BADGE_SINTETIS}>data sintetis · seed 42</span>}
      />

      {(isLoading || isError || !data) && (
        <PanelState kind={isLoading ? "loading" : "error"} />
      )}

      {data && (
        <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 11 }}>
          {/* ringkasan global */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit,minmax(120px,1fr))",
              gap: 8,
            }}
          >
            {[
              { label: "Penyebab dominan", val: causeLabel(data.dominant_cause) },
              { label: "Ruas terdampak", val: `${fmtInt(data.affected_section_count)} / ${fmtInt(data.section_count)}` },
              { label: "Kelas dihitung", val: fmtInt(data.causes?.length ?? 0) },
            ].map((s) => (
              <div
                key={s.label}
                style={{ background: "var(--bg-elevated)", borderRadius: 8, padding: "8px 10px" }}
              >
                <p style={{ fontSize: 9, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: ".06em" }}>
                  {s.label}
                </p>
                <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>{s.val}</p>
              </div>
            ))}
          </div>

          {/* sebaran kelas penyebab pada 30 ruas */}
          {!!data.causes?.length && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <p style={{ fontSize: 9, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: ".08em" }}>
                Sebaran kelas pada {fmtInt(data.section_count)} ruas
              </p>
              {data.causes.slice(0, 6).map((c) => (
                <div key={c.cause} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ width: 118, fontSize: 10, color: "var(--text-muted)" }}>
                    {causeLabel(c.cause)}
                  </span>
                  <div style={{ flex: 1, height: 5, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${(c.share ?? 0) * 100}%`,
                        background: CAUSE_COLOR[c.cause] ?? "var(--text-dim)",
                      }}
                    />
                  </div>
                  <span style={{ width: 132, fontSize: 10, color: "var(--text-dim)", textAlign: "right" }}>
                    {fmtInt(c.sections)} ruas · {fmtPct(c.share, 1)} · VC {fmtNum(c.avg_vc_ratio, 2)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* per simpang */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(290px,1fr))", gap: 9 }}>
            {(data.per_intersection ?? []).map((ix) => (
              <IntersectionRow key={ix.intersection_id} ix={ix} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
