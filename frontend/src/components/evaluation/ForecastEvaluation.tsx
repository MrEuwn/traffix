import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useForecastEvaluation, useForecastSeries } from "../../hooks/useTraffixData";
import { fmtInt, fmtNum } from "../../lib/format";
import { Card, PanelHead, Segmented, StateBlock, StatusPill, TableWrap, Td, Th, cn } from "../ui";
import { Icon } from "../ui/icons";
import type { ForecastEvaluationResponse, ForecastHorizonResult } from "../../types";

/* Semua angka di berkas ini dibaca dari GET /api/v1/model/evaluation/forecast
   (backend/ml/forecast/artifacts/forecast_evaluation.json) dan dari CSV prediksi per sampel.
   Tidak ada angka yang ditulis manual. */

type Horizon = "15m" | "2h" | "4h";
const HORIZONS: { value: Horizon; label: string }[] = [
  { value: "15m", label: "15 menit" },
  { value: "2h", label: "2 jam" },
  { value: "4h", label: "4 jam" },
];

const signedPct = (v: number | null | undefined, d = 1) =>
  v == null ? "—" : `${v >= 0 ? "+" : "−"}${fmtNum(Math.abs(v), d)}%`;

const Improvement = ({ value }: { value: number | null }) =>
  value == null ? (
    <span className="text-micro text-ink-muted">model</span>
  ) : (
    <span
      className={cn("num inline-flex items-center gap-1 text-micro", value >= 0 ? "text-ok" : "text-crit")}
      title="(MAE pembanding − MAE LSTM) / MAE pembanding"
    >
      <Icon name={value >= 0 ? "arrow-down" : "arrow-up"} size={11} />
      {signedPct(value)}
    </span>
  );

const RuntimeBlock = ({ data }: { data: ForecastEvaluationResponse }) => {
  const rt = data.runtime;
  const tone = rt.mode === "lstm" ? (rt.matches_evaluation ? "ok" : "warn") : rt.mode === "heuristic_fallback" ? "warn" : "idle";
  return (
    <div className="space-y-1.5 rounded-card border border-line bg-raised px-3 py-2.5">
      <p className="label-caps">Model yang sedang melayani</p>
      <StatusPill
        tone={tone}
        label={rt.mode === "lstm" ? "LSTM dimuat" : rt.mode === "heuristic_fallback" ? "Fallback heuristik" : "ML mati"}
        icon={rt.mode === "lstm" ? "check-circle" : "alert-triangle"}
      />
      <p className="text-micro text-ink-soft">{rt.label}</p>
      <p className="text-micro text-ink-muted">
        {rt.matches_evaluation
          ? "sha256 file model = file yang dievaluasi di halaman ini."
          : rt.mode === "lstm"
            ? "File model yang dimuat BERBEDA dari yang dievaluasi — jalankan ulang evaluasi."
            : "Angka evaluasi di bawah tetap berasal dari artefak, bukan dari runtime."}
      </p>
    </div>
  );
};

const SeriesChart = ({ horizon, result }: { horizon: Horizon; result: ForecastHorizonResult }) => {
  const [intersection, setIntersection] = useState<string | null>(null);
  const { data, isLoading, isError } = useForecastSeries(horizon, intersection);
  if (isLoading) return <StateBlock state="loading" height={280} />;
  if (isError || !data?.points.length)
    return <StateBlock state="error" height={280} hint="Prediksi per sampel tidak tersedia — jalankan ulang evaluasi." />;
  const points = data.points.map((p) => ({ ...p, t: p.t.slice(11, 16) }));
  return (
    <div className="space-y-1.5">
      {data.intersections.length > 1 && (
        <Segmented
          label="Simpang"
          options={data.intersections.map((id) => ({ value: id, label: id.replace("INT-", "") }))}
          value={data.intersection ?? data.intersections[0]}
          onChange={setIntersection}
        />
      )}
      <div className="h-[280px] w-full">
        <ResponsiveContainer>
          <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="rgb(var(--c-line))" strokeDasharray="3 3" />
            <XAxis dataKey="t" tick={{ fontSize: 11, fill: "rgb(var(--c-ink-muted))" }} minTickGap={40} />
            <YAxis
              tick={{ fontSize: 11, fill: "rgb(var(--c-ink-muted))" }}
              width={52}
              tickFormatter={(v: number) => fmtInt(v)}
            />
            <Tooltip
              contentStyle={{
                background: "rgb(var(--c-surface))",
                border: "1px solid rgb(var(--c-line))",
                fontSize: 12,
              }}
              formatter={(v) => `${fmtInt(Number(v))} kend/jam`}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line dataKey="actual" name="Aktual" stroke="rgb(var(--c-ink-muted))" strokeWidth={1} dot={false} />
            <Line dataKey="lstm" name="LSTM" stroke="rgb(var(--c-primary))" strokeWidth={2} dot={false} />
            <Line
              dataKey="baseline"
              name={`Baseline: ${result.comparison.find((r) => r.model === data.baseline)?.label ?? data.baseline}`}
              stroke="rgb(var(--c-warn))"
              strokeWidth={1.5}
              strokeDasharray="5 4"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-micro text-ink-muted">
        {data.intersection} · hari uji 7 Mei 2026 (sintetis) · sumbu X = waktu target · tiap {data.step_minutes} menit;
        n uji total {fmtInt(data.n_total)} (semua simpang) · sumber <code>{data.source_csv}</code>
      </p>
    </div>
  );
};

/** Bukti D2 tugas utama: peramalan volume simpang 15 menit / 2 jam / 4 jam. */
export const ForecastEvaluation = () => {
  const { data, isLoading, isError, refetch } = useForecastEvaluation();
  const [horizon, setHorizon] = useState<Horizon>("15m");

  if (isLoading) return <StateBlock state="loading" height={360} />;
  if (isError || !data)
    return <StateBlock state="error" height={360} hint="Evaluasi peramalan tidak dapat dimuat." onRetry={() => refetch()} />;
  if (!data.available || !data.horizons)
    return (
      <StateBlock
        state="error"
        height={360}
        hint={`${data.reason ?? "Artefak evaluasi belum ada"} — jalankan: ${data.command ?? "python backend/scripts/run_d2_evaluation.py"}`}
        onRetry={() => refetch()}
      />
    );

  const result = data.horizons[horizon];
  const lstm = result.comparison.find((r) => r.model === "lstm")!;
  const strongest = result.comparison.find((r) => r.model === result.strongest_baseline.model)!;
  const vs = result.lstm_vs_strongest_baseline;
  const lstmIsBest = result.best_on_test.model === "lstm";
  const bestLabel = result.comparison.find((r) => r.model === result.best_on_test.model)?.label;

  return (
    <div className="flex flex-col gap-3">
      {/* ── 1. pertanyaan, data, model ── */}
      <Card pad={false}>
        <PanelHead
          title="Tugas utama D2 — peramalan volume simpang"
          sub={`${data.model?.name} · dievaluasi ${data.generated_at?.slice(0, 10)}`}
          icon="trending-up"
          right={<StatusPill tone="warn" label="Data sintetis" icon="info" />}
        />
        <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <div className="space-y-3">
            <p className="text-body text-ink">{data.question}</p>
            <dl className="grid gap-1.5 text-micro sm:grid-cols-2">
              {[
                ["Target", `${data.target?.definition} (${data.target?.unit})`],
                ["Data", `${data.dataset?.name} — ${data.dataset?.provenance_detail}`],
                ["Mengapa data ini", data.dataset?.why_this_dataset],
                ["Latih", data.split?.train],
                ["Validasi", data.split?.validation],
                ["Uji", `${data.split?.test} — dinilai sekali setelah model dipilih`],
                ["Split", data.split?.protocol],
              ].map(([k, v]) => (
                <div key={k} className="rounded-control border border-line/70 px-2.5 py-1.5">
                  <dt className="label-caps">{k}</dt>
                  <dd className="text-ink-soft">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <RuntimeBlock data={data} />
        </div>
      </Card>

      {/* ── 2. hasil per horizon ── */}
      <Card pad={false}>
        <PanelHead
          title="Model vs baseline pada hari uji"
          sub={`n uji ${fmtInt(result.n.test)} · latih ${fmtInt(result.n.train)} · validasi ${fmtInt(result.n.validation)} · satuan galat kend/jam`}
          icon="chart"
          right={<Segmented options={HORIZONS} value={horizon} onChange={setHorizon} />}
        />
        <div className="space-y-4 p-4">
          <div className="grid gap-2.5 sm:grid-cols-3">
            <div className="rounded-card border border-line bg-raised px-3 py-2.5">
              <p className="label-caps">MAE LSTM</p>
              <p className="num text-hero font-semibold text-ink">{fmtInt(lstm.test.mae)}</p>
              <p className="text-micro text-ink-muted">WAPE {fmtNum(lstm.test.wape_pct, 1)}% · RMSE {fmtInt(lstm.test.rmse)}</p>
            </div>
            <div className="rounded-card border border-line bg-raised px-3 py-2.5">
              <p className="label-caps">Baseline terkuat</p>
              <p className="num text-metric font-semibold text-ink">{fmtInt(strongest.test.mae)}</p>
              <p className="text-micro text-ink-muted">{strongest.label} · dipilih dari MAE validasi</p>
            </div>
            <div className="rounded-card border border-line bg-raised px-3 py-2.5">
              <p className="label-caps">Perbaikan MAE</p>
              <p
                className={cn(
                  "num text-metric font-semibold",
                  !vs.significant ? "text-ink" : vs.mae_improvement_pct >= 0 ? "text-ok" : "text-crit",
                )}
              >
                {signedPct(vs.mae_improvement_pct)}
              </p>
              <p className="num text-micro text-ink-muted">
                selisih {fmtNum(vs.bootstrap.mae_diff, 1)} · CI95 [{fmtNum(vs.bootstrap.ci95_low, 1)}, {fmtNum(vs.bootstrap.ci95_high, 1)}]
                {vs.significant ? " · signifikan" : " · tidak signifikan"}
              </p>
            </div>
          </div>

          {!lstmIsBest && (
            <p className="flex items-start gap-2 rounded-card border border-warn/40 bg-warn/10 px-3 py-2 text-micro text-ink">
              <Icon name="alert-triangle" size={14} className="mt-0.5 shrink-0 text-warn" />
              <span>
                Pada horizon ini MAE uji terendah dicapai <b>{bestLabel}</b> ({fmtInt(result.best_on_test.mae)}), bukan LSTM.
                Angka dilaporkan apa adanya; model tidak disetel ulang terhadap hari uji.
              </span>
            </p>
          )}

          <TableWrap>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <Th>Model</Th>
                  <Th align="right">MAE</Th>
                  <Th align="right">RMSE</Th>
                  <Th align="right">WAPE %</Th>
                  <Th align="right">sMAPE %</Th>
                  <Th align="right">MAPE %</Th>
                  <Th align="right">R²</Th>
                  <Th align="right">LSTM vs ini</Th>
                </tr>
              </thead>
              <tbody>
                {result.comparison.map((r) => (
                  <tr key={r.model} className={r.model === "lstm" ? "bg-primary-quiet" : undefined}>
                    <Td className={r.model === "lstm" ? "font-semibold text-ink" : undefined}>
                      {r.label} <span className="text-ink-muted">· {r.role}</span>
                      {r.model === result.best_on_test.model && (
                        <span className="ml-1 text-micro text-ok">· MAE terendah</span>
                      )}
                    </Td>
                    <Td align="right"><span className="num">{fmtInt(r.test.mae)}</span></Td>
                    <Td align="right"><span className="num">{fmtInt(r.test.rmse)}</span></Td>
                    <Td align="right"><span className="num">{fmtNum(r.test.wape_pct, 1)}</span></Td>
                    <Td align="right"><span className="num">{fmtNum(r.test.smape_pct, 1)}</span></Td>
                    <Td align="right"><span className="num">{fmtNum(r.test.mape_pct, 1)}</span></Td>
                    <Td align="right"><span className="num">{fmtNum(r.test.r2, 3)}</span></Td>
                    <Td align="right"><Improvement value={r.lstm_mae_improvement_pct} /></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
          <p className="text-micro text-ink-muted">
            Perbaikan = (MAE pembanding − MAE LSTM) / MAE pembanding; positif berarti LSTM lebih baik. MAPE melewati{" "}
            {fmtInt(lstm.test.mape_zero_targets_skipped)} target bernilai 0 — WAPE dan sMAPE tetap terdefinisi untuk semua sampel.
            CI dari moving-block bootstrap ({vs.bootstrap.block_minutes} menit, {fmtInt(vs.bootstrap.reps)} ulangan).
          </p>

          <SeriesChart horizon={horizon} result={result} />
        </div>
      </Card>

      {/* ── 3. analisis galat ── */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card pad={false}>
          <PanelHead title="Galat per jam target" sub="MAE LSTM vs baseline terkuat, hari uji" icon="clock" />
          <div className="p-4">
            <TableWrap>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <Th>Jam</Th>
                    <Th align="right">n</Th>
                    <Th align="right">MAE LSTM</Th>
                    <Th align="right">MAE baseline</Th>
                  </tr>
                </thead>
                <tbody>
                  {[...result.error_by_target_hour]
                    .sort((a, b) => b.lstm_mae - a.lstm_mae)
                    .slice(0, 6)
                    .map((h) => (
                      <tr key={h.hour}>
                        <Td><span className="num">{String(h.hour).padStart(2, "0")}:00</span></Td>
                        <Td align="right"><span className="num">{fmtInt(h.n)}</span></Td>
                        <Td align="right"><span className="num font-semibold text-ink">{fmtInt(h.lstm_mae)}</span></Td>
                        <Td align="right"><span className="num">{fmtInt(h.baseline_mae)}</span></Td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </TableWrap>
            <p className="mt-2 text-micro text-ink-muted">Enam jam dengan galat LSTM terbesar.</p>
          </div>
        </Card>
        <Card pad={false}>
          <PanelHead title="Kasus terburuk" sub="5 sampel uji dengan galat absolut LSTM terbesar" icon="alert-triangle" />
          <div className="p-4">
            <TableWrap>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <Th>Target</Th>
                    <Th align="right">Aktual</Th>
                    <Th align="right">LSTM</Th>
                    <Th align="right">|galat|</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.worst_cases.map((w) => (
                    <tr key={`${w.intersection_id}-${w.target_time_wib}`}>
                      <Td>
                        <span className="num">{w.intersection_id} · {w.target_time_wib.slice(11)}</span>
                      </Td>
                      <Td align="right"><span className="num">{fmtInt(w.actual)}</span></Td>
                      <Td align="right"><span className="num">{fmtInt(w.lstm)}</span></Td>
                      <Td align="right"><span className="num font-semibold text-ink">{fmtInt(w.abs_error)}</span></Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
            <p className="mt-2 text-micro text-ink-muted">
              Target berupa volume 1 menit (jumlah kendaraan × 60) yang sangat berderau; lonjakan sesaat tidak bisa diramalkan model mana pun.
            </p>
          </div>
        </Card>
      </div>

      {/* ── 4a. eksperimen kedua: data notebook asli ── */}
      {data.secondary_experiment && (
        <Card pad={false}>
          <PanelHead
            title={`Eksperimen kedua — ${data.secondary_experiment.title}`}
            sub={`${data.secondary_experiment.dataset} · protokol identik · model tidak dipakai aplikasi`}
            icon="layers"
          />
          <div className="p-4">
            <TableWrap>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <Th>Horizon</Th>
                    <Th align="right">n uji</Th>
                    <Th align="right">MAE LSTM</Th>
                    <Th>Baseline terkuat</Th>
                    <Th align="right">MAE baseline</Th>
                    <Th align="right">Perbaikan</Th>
                    <Th>MAE terendah</Th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.secondary_experiment.horizons).map(([h, d]) => {
                    const l = d.comparison.find((r) => r.model === "lstm");
                    const b = d.comparison.find((r) => r.model === d.strongest_baseline.model);
                    return (
                      <tr key={h}>
                        <Td>{h}</Td>
                        <Td align="right"><span className="num">{fmtInt(d.n.test)}</span></Td>
                        <Td align="right"><span className="num">{fmtInt(l?.test.mae)}</span></Td>
                        <Td>{b?.label}</Td>
                        <Td align="right"><span className="num">{fmtInt(b?.test.mae)}</span></Td>
                        <Td align="right"><Improvement value={d.lstm_vs_strongest_baseline.mae_improvement_pct} /></Td>
                        <Td>{d.comparison.find((r) => r.model === d.best_on_test.model)?.label}</Td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableWrap>
          </div>
        </Card>
      )}

      {/* ── 4b. uji transfer antarsimulator ── */}
      {data.transfer_v4 && (
        <Card pad={false}>
          <PanelHead
            title="Uji transfer — LSTM hybrid diterapkan ke replay v4 tanpa latih ulang"
            sub={`${data.transfer_v4.dataset} · ${data.transfer_v4.split} · alasan model aplikasi dilatih pada replay v4`}
            icon="layers"
          />
          <div className="p-4">
            <TableWrap>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <Th>Horizon</Th>
                    <Th align="right">n</Th>
                    <Th align="right">MAE LSTM</Th>
                    <Th align="right">MAE persistence</Th>
                    <Th align="right">Perbaikan</Th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.transfer_v4.horizons).map(([h, v]) => (
                    <tr key={h}>
                      <Td>{h}</Td>
                      <Td align="right"><span className="num">{fmtInt(v.lstm.n)}</span></Td>
                      <Td align="right"><span className="num">{fmtInt(v.lstm.mae)}</span></Td>
                      <Td align="right"><span className="num">{fmtInt(v.persistence.mae)}</span></Td>
                      <Td align="right"><Improvement value={v.mae_improvement_pct_vs_persistence} /></Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
            <p className="mt-2 text-micro text-ink-muted">
              Mengukur pergeseran distribusi antarsimulator. Ini tetap data sintetis, bukan validasi lapangan.
            </p>
          </div>
        </Card>
      )}

      {/* ── 5. reproduksi & kebocoran ── */}
      <div className="grid gap-3 lg:grid-cols-2">
        {data.legacy_reproduction && (
          <Card pad={false}>
            <PanelHead
              title="Reproduksi angka notebook lama"
              sub={`n ${fmtInt(data.legacy_reproduction.n_test)} · ${data.legacy_reproduction.protocol}`}
              icon="refresh"
            />
            <div className="space-y-3 p-4">
              <TableWrap>
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      <Th>Horizon</Th>
                      <Th align="right">MAPE dihitung ulang</Th>
                      <Th align="right">Tersimpan</Th>
                      <Th align="right">Persistence MAE</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.legacy_reproduction.horizons).map(([h, v]) => (
                      <tr key={h}>
                        <Td>{h}</Td>
                        <Td align="right">
                          <span className="num">{fmtNum(v.recomputed.mape_pct, 2)}%</span>{" "}
                          <span className={cn("text-micro", v.mape_matches_stored ? "text-ok" : "text-crit")}>
                            {v.mape_matches_stored ? "cocok" : "beda"}
                          </span>
                        </Td>
                        <Td align="right"><span className="num">{fmtNum(v.stored_mape_pct, 2)}%</span></Td>
                        <Td align="right"><span className="num">{fmtInt(v.persistence_last_observation.mae)}</span></Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
              <ul className="space-y-1.5">
                {data.legacy_reproduction.issues_found.map((i) => (
                  <li key={i} className="flex items-start gap-1.5 text-micro text-ink-soft">
                    <Icon name="alert-triangle" size={12} className="mt-0.5 shrink-0 text-warn" />
                    <span>{i}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Card>
        )}
        <Card pad={false}>
          <PanelHead title="Penjaga kebocoran" sub="Dijalankan oleh pipeline; gagal = exit non-nol" icon="check-circle" />
          <div className="p-4">
            <ul className="space-y-2">
              {(data.leakage_guard ?? []).map((l) => (
                <li key={l} className="flex items-start gap-2 text-micro text-ink-soft">
                  <Icon name="check-circle" size={13} className="mt-0.5 shrink-0 text-ok" />
                  <span>{l}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </div>

      {/* ── 6. batasan ── */}
      <Card pad={false} className="border-l-4 border-l-warn">
        <PanelHead title="Batasan dan klaim yang tidak dibuat" sub="Wajib dibaca sebelum mengutip angka" icon="alert-triangle" />
        <div className="grid gap-3 p-4 md:grid-cols-2">
          {[...(data.limitations ?? []), ...(data.not_claims ?? [])].map((l) => (
            <div key={l} className="flex items-start gap-2.5 rounded-card border border-line bg-raised px-3 py-2.5">
              <Icon name="alert-triangle" size={16} className="mt-0.5 shrink-0 text-warn" />
              <span className="text-body text-ink-soft">{l}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-micro text-ink-muted">
          Sumber: <code>forecast_evaluation.json</code> · commit {data.git_commit?.slice(0, 10) ?? "—"}
          {data.git_dirty ? " (working tree berubah)" : ""} · seed {data.seed} · reproduksi:{" "}
          <code>{data.reproduce}</code>
        </p>
      </Card>
    </div>
  );
};
