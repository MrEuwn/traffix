import { useModelEvaluation } from "../hooks/useTraffixData";
import type { ReactNode } from "react";
import {
  BADGE_SINTETIS,
  CARD,
  CAUSE_COLOR,
  causeLabel,
  fmtInt,
  fmtNum,
} from "../lib/format";
import { PanelState } from "../components/dashboard/Panel";
import type { ModelBaselineScore } from "../types";

const METRICS: { key: "macro_f1" | "balanced_accuracy" | "accuracy"; label: string }[] = [
  { key: "macro_f1", label: "Macro F1" },
  { key: "balanced_accuracy", label: "Balanced accuracy" },
  { key: "accuracy", label: "Accuracy" },
];

const Section = ({
  title,
  sub,
  children,
}: {
  title: string;
  sub?: string;
  children: ReactNode;
}) => (
  <div style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 10, padding: 12 }}>
    <p style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em", color: "var(--text-dim)" }}>
      {title}
    </p>
    {sub && <p style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{sub}</p>}
    <div style={{ marginTop: 9 }}>{children}</div>
  </div>
);

/** Sel heat: intensitas biru dari nilai relatif; diagonal (prediksi benar) hijau. */
const HeatCell = ({ v, max, diag }: { v: number; max: number; diag: boolean }) => {
  const r = max > 0 ? v / max : 0;
  const bg = diag ? `rgba(52,211,153,${0.12 + 0.78 * r})` : `rgba(96,165,250,${0.06 + 0.72 * r})`;
  return (
    <td
      style={{
        background: bg,
        color: r > 0.55 ? "#fff" : "var(--text-secondary)",
        fontSize: 10,
        fontWeight: diag ? 700 : 400,
        textAlign: "center",
        padding: "5px 4px",
        border: "1px solid var(--bg-elevated)",
        minWidth: 34,
      }}
    >
      {v === 0 ? "·" : fmtInt(v)}
    </td>
  );
};

export const ModelEvaluation = () => {
  const { data, isLoading, isError } = useModelEvaluation();
  const available = data?.available === true;
  const baselines: [string, ModelBaselineScore][] = data?.baselines
    ? [
        ["Majority class", data.baselines.majority_class],
        ["Rule-based", data.baselines.rule_based],
      ]
    : [];

  const cm = data?.confusion_matrix;
  const cmMax = cm ? Math.max(...cm.matrix.flat(), 0) : 0;
  const topFeatures = (data?.feature_importance ?? []).slice(0, 15);
  const featMax = Math.max(...topFeatures.map((f) => f.importance), 0);

  return (
    <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
      {/* header */}
      <div style={{ ...CARD, padding: 14, display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
            Evaluasi Model Klasifikasi Penyebab
          </p>
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>
            {data
              ? `${data.model_name}${data.trained_at ? ` · dilatih ${data.trained_at}` : ""}`
              : "artefak bottleneck_classifier"}
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
          <span style={BADGE_SINTETIS}>data sintetis · seed 42</span>
          <span
            style={{
              fontSize: 9,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 20,
              color: available ? "var(--green)" : "var(--orange)",
              background: available ? "var(--green-bg)" : "var(--orange-bg)",
              border: `1px solid ${available ? "var(--green-border)" : "var(--orange-border)"}`,
            }}
          >
            {available ? "ARTEFAK TERSEDIA" : "ARTEFAK BELUM ADA"}
          </span>
        </div>
      </div>

      {(isLoading || isError || !data) && (
        <div style={CARD}>
          <PanelState kind={isLoading ? "loading" : "error"} />
        </div>
      )}

      {data && (
        <>
          {!available && (
            <div
              style={{
                ...CARD,
                border: "1px solid var(--orange-border)",
                background: "var(--orange-bg)",
                padding: 12,
                fontSize: 11,
                color: "var(--text-secondary)",
                lineHeight: 1.6,
              }}
            >
              Artefak model belum tersedia — halaman menampilkan struktur evaluasi tanpa angka.
              Jalankan <code style={{ color: "var(--orange)" }}>backend/ml/bottleneck/train_bottleneck.py</code>{" "}
              untuk menghasilkan <code>bottleneck_classifier.joblib</code> dan <code>metrics.json</code>.
            </div>
          )}

          {/* model vs baseline */}
          <Section
            title="Klaim D2 — model vs baseline"
            sub="Diuji pada hari ke-7 (split temporal, tanpa pengacakan). Metrik pada label penyebab 9 kelas."
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                <thead>
                  <tr style={{ color: "var(--text-dim)", fontSize: 9, textTransform: "uppercase", letterSpacing: ".06em" }}>
                    <th style={{ textAlign: "left", padding: "6px 8px" }}>Kandidat</th>
                    {METRICS.map((m) => (
                      <th key={m.key} style={{ textAlign: "right", padding: "6px 8px" }}>
                        {m.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderTop: "1px solid var(--border)" }}>
                    <td style={{ padding: "7px 8px", color: "var(--blue)", fontWeight: 600 }}>
                      {data.model_name}
                      <span style={{ color: "var(--text-dim)", fontWeight: 400 }}> · model</span>
                    </td>
                    {METRICS.map((m) => (
                      <td key={m.key} style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-primary)", fontWeight: 600 }}>
                        {fmtNum(data.metrics?.[m.key], 3)}
                      </td>
                    ))}
                  </tr>
                  {baselines.map(([label, b]) => (
                    <tr key={label} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ padding: "7px 8px", color: "var(--text-muted)" }}>
                        {label}
                        <span style={{ color: "var(--text-dim)" }}> · {b.model}</span>
                      </td>
                      {METRICS.map((m) => {
                        const base = b[m.key];
                        const own = data.metrics?.[m.key];
                        const delta = own != null ? own - base : null;
                        return (
                          <td key={m.key} style={{ padding: "7px 8px", textAlign: "right", color: "var(--text-secondary)" }}>
                            {fmtNum(base, 3)}
                            {delta != null && (
                              <span
                                style={{
                                  marginLeft: 6,
                                  fontSize: 9,
                                  fontWeight: 600,
                                  color: delta >= 0 ? "var(--green)" : "var(--red)",
                                }}
                              >
                                {delta >= 0 ? "▲" : "▼"} {fmtNum(Math.abs(delta), 3)}
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, alignItems: "start" }}>
            {/* per kelas */}
            <Section title="Metrik per kelas" sub={`${fmtInt(data.per_class?.length ?? 0)} kelas · support = jumlah label uji`}>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                  <thead>
                    <tr style={{ color: "var(--text-dim)", fontSize: 9, textTransform: "uppercase", letterSpacing: ".06em" }}>
                      <th style={{ textAlign: "left", padding: "5px 8px" }}>Kelas</th>
                      <th style={{ textAlign: "right", padding: "5px 8px" }}>Precision</th>
                      <th style={{ textAlign: "right", padding: "5px 8px" }}>Recall</th>
                      <th style={{ textAlign: "right", padding: "5px 8px" }}>F1</th>
                      <th style={{ textAlign: "right", padding: "5px 8px" }}>Support</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.per_class ?? []).map((p) => (
                      <tr key={p.cause} style={{ borderTop: "1px solid var(--border)" }}>
                        <td style={{ padding: "6px 8px" }}>
                          <span
                            style={{
                              display: "inline-block",
                              width: 6,
                              height: 6,
                              borderRadius: "50%",
                              marginRight: 6,
                              background: CAUSE_COLOR[p.cause] ?? "var(--text-dim)",
                            }}
                          />
                          {causeLabel(p.cause)}
                        </td>
                        <td style={{ padding: "6px 8px", textAlign: "right", color: "var(--text-secondary)" }}>{fmtNum(p.precision, 3)}</td>
                        <td style={{ padding: "6px 8px", textAlign: "right", color: "var(--text-secondary)" }}>{fmtNum(p.recall, 3)}</td>
                        <td style={{ padding: "6px 8px", textAlign: "right", color: "var(--text-primary)", fontWeight: 600 }}>{fmtNum(p.f1, 3)}</td>
                        <td style={{ padding: "6px 8px", textAlign: "right", color: "var(--text-dim)" }}>{fmtInt(p.support)}</td>
                      </tr>
                    ))}
                    {!data.per_class?.length && (
                      <tr>
                        <td colSpan={5} style={{ padding: 10, color: "var(--text-dim)", fontSize: 11 }}>
                          Metrik per kelas belum tersedia.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Section>

            {/* feature importance */}
            <Section title="Fitur paling berpengaruh" sub="Top 15 · urutan menurun">
              {topFeatures.length ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                  {topFeatures.map((f) => (
                    <div key={f.feature} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ width: 138, fontSize: 10, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {f.feature}
                      </span>
                      <div style={{ flex: 1, height: 5, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                        <div
                          style={{
                            height: "100%",
                            width: `${featMax > 0 ? (f.importance / featMax) * 100 : 0}%`,
                            background: "var(--blue)",
                          }}
                        />
                      </div>
                      <span style={{ width: 54, fontSize: 10, textAlign: "right", color: "var(--text-dim)" }}>
                        {fmtNum(f.importance, 4)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: 11, color: "var(--text-dim)" }}>Belum ada data feature importance.</p>
              )}
            </Section>
          </div>

          {/* confusion matrix */}
          <Section
            title="Confusion matrix"
            sub={`Baris = label aktual, kolom = prediksi · diagonal = benar${cm ? ` · maks sel ${fmtInt(cmMax)}` : ""}`}
          >
            {cm?.labels?.length ? (
              <div style={{ overflowX: "auto" }}>
                <table style={{ borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th />
                      {cm.labels.map((l) => (
                        <th
                          key={l}
                          style={{
                            fontSize: 9,
                            color: "var(--text-dim)",
                            fontWeight: 500,
                            padding: "3px 2px",
                            writingMode: "vertical-rl",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {causeLabel(l)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {cm.matrix.map((row, i) => (
                      <tr key={cm.labels[i]}>
                        <td style={{ fontSize: 9, color: "var(--text-muted)", padding: "2px 8px 2px 0", whiteSpace: "nowrap" }}>
                          {causeLabel(cm.labels[i])}
                        </td>
                        {row.map((v, j) => (
                          <HeatCell key={j} v={v} max={cmMax} diag={i === j} />
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ fontSize: 11, color: "var(--text-dim)" }}>Confusion matrix belum tersedia.</p>
            )}
          </Section>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, alignItems: "start" }}>
            {/* protokol split */}
            <Section title="Protokol split">
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {[
                  { l: "Latih", v: data.split?.train },
                  { l: "Validasi", v: data.split?.validation },
                  { l: "Uji", v: data.split?.test },
                ].map((r) => (
                  <div key={r.l} style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
                    <span style={{ color: "var(--text-muted)" }}>{r.l}</span>
                    <span style={{ color: "var(--text-primary)" }}>{r.v ?? "—"}</span>
                  </div>
                ))}
                <p style={{ fontSize: 10, color: "var(--text-dim)", borderTop: "1px solid var(--border)", paddingTop: 7, lineHeight: 1.5 }}>
                  {data.split?.protocol ?? "temporal, tanpa pengacakan"}
                </p>
                <p style={{ fontSize: 10, color: "var(--text-dim)" }}>
                  Kelas: {fmtInt(data.classes?.length ?? 0)} · {data.classes?.map(causeLabel).join(", ") ?? "—"}
                </p>
              </div>
            </Section>

            {/* leakage guard */}
            <Section title="Penjagaan kebocoran label" sub={`${fmtInt(data.leakage_guard?.length ?? 0)} aturan aktif`}>
              {data.leakage_guard?.length ? (
                <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 5 }}>
                  {data.leakage_guard.map((l) => (
                    <li key={l} style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                      <span style={{ color: "var(--green)", marginRight: 5 }}>🛡</span>
                      {l}
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: 11, color: "var(--text-dim)" }}>Daftar belum tersedia.</p>
              )}
            </Section>

            {/* limitations */}
            <Section title="Keterbatasan" sub="Wajib dibaca sebelum mengutip metrik">
              {data.limitations?.length ? (
                <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 5 }}>
                  {data.limitations.map((l) => (
                    <li key={l} style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                      <span style={{ color: "var(--orange)", marginRight: 5 }}>•</span>
                      {l}
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ fontSize: 11, color: "var(--text-dim)" }}>Daftar belum tersedia.</p>
              )}
            </Section>
          </div>

          {/* artefak */}
          <div style={{ fontSize: 10, color: "var(--text-dim)" }}>
            Artefak: {data.artifacts?.model ?? "—"} · {data.artifacts?.metrics ?? "—"}
          </div>
        </>
      )}
    </div>
  );
};
