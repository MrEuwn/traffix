import { useModelEvaluation } from "../hooks/useTraffixData";
import {
  Card,
  PanelHead,
  SeedBadge,
  StateBlock,
  StatusPill,
  TableWrap,
  Td,
  Th,
  cn,
} from "../components/ui";
import { Icon } from "../components/ui/icons";
import { causeMeta } from "../lib/causes";
import { causeLabel, fmtInt, fmtNum } from "../lib/format";
import type { ModelPerClassScore } from "../types";

/* Semua nilai halaman ini dibaca dari GET /api/v1/model/evaluation (metrics.json).
   Tidak ada angka yang ditulis manual di berkas ini. */
const METRICS = [
  { key: "macro_f1", label: "Macro F1", hero: true },
  { key: "balanced_accuracy", label: "Balanced accuracy", hero: false },
  { key: "accuracy", label: "Akurasi", hero: false },
] as const;

const CANDIDATES = [
  { key: "rule_based", label: "Rule-based" },
  { key: "majority_class", label: "Majority class" },
] as const;

const SPLIT_ROWS = [
  { key: "train", label: "Latih" },
  { key: "validation", label: "Validasi" },
  { key: "test", label: "Uji" },
] as const;

/** Bar proporsi (0..1) — dipakai untuk macro-F1, F1 per kelas, dan feature importance. */
const MiniBar = ({ pct, className = "" }: { pct: number; className?: string }) => (
  <div className={cn("h-1.5 w-full overflow-hidden rounded-bar bg-raised", className)}>
    <div
      className="h-full rounded-bar bg-primary"
      style={{ width: `${Math.min(Math.max(pct, 0), 1) * 100}%` }}
    />
  </div>
);

/** Selisih vs baseline; arah dibawa ikon + tanda angka, bukan warna saja. */
const Delta = ({ value }: { value: number | null }) =>
  value == null ? (
    <span className="text-micro text-ink-muted">—</span>
  ) : (
    <span className="num inline-flex items-center gap-1 text-micro text-ink">
      <Icon name={value >= 0 ? "arrow-up" : "arrow-down"} size={11} />
      {fmtNum(value, 3)}
    </span>
  );

const trainedLabel = (raw?: string) => {
  if (!raw) return "—";
  const d = new Date(raw);
  return Number.isNaN(d.getTime())
    ? raw
    : d.toLocaleDateString("id-ID", { day: "2-digit", month: "long", year: "numeric" });
};

export const ModelEvaluation = () => {
  const { data, isLoading, isError, refetch } = useModelEvaluation();

  if (isLoading) return <StateBlock state="loading" height={360} />;
  if (isError || !data)
    return (
      <StateBlock
        state="error"
        height={360}
        hint="Evaluasi model tidak dapat dimuat dari API."
        onRetry={() => refetch()}
      />
    );
  if (!data.available)
    return (
      <StateBlock
        state="error"
        height={360}
        hint="Artefak model belum tersedia — jalankan backend/ml/bottleneck/train_bottleneck.py untuk menghasilkan metrics.json."
        onRetry={() => refetch()}
      />
    );

  const metrics = data.metrics;
  const perClass = data.per_class ?? [];
  const lowest: ModelPerClassScore | undefined = perClass.length
    ? perClass.reduce((min, p) => (p.f1 < min.f1 ? p : min))
    : undefined;
  const allFeatures = data.feature_importance ?? [];
  const features = allFeatures.slice(0, 15);
  const featMax = Math.max(...features.map((f) => f.importance), 0);
  const cm = data.confusion_matrix;
  const trained = trainedLabel(data.trained_at);

  return (
    <div className="flex flex-col gap-3">
      {/* ── 1. hero: model vs baseline ── */}
      <Card pad={false}>
        <PanelHead
          title="Klaim bukti D2 — model vs baseline"
          sub={`${data.model_name} · dilatih ${trained}`}
          icon="chart"
          right={
            <div className="flex flex-wrap items-center justify-end gap-2">
              <SeedBadge />
              <StatusPill tone="ok" label="Artefak tersedia" icon="check-circle" />
            </div>
          }
        />
        <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <div className="grid gap-2.5">
            {METRICS.map((m) => (
              <div key={m.key} className="rounded-card border border-line bg-raised px-3 py-2.5">
                <p className="label-caps">{m.label}</p>
                <p className={cn("num font-semibold text-ink", m.hero ? "text-hero" : "text-metric")}>
                  {fmtNum(metrics?.[m.key], 3)}
                </p>
                <p className="mt-0.5 text-micro text-ink-muted">
                  {m.hero ? "label penyebab · 9 kelas" : `model · ${data.model_name}`}
                </p>
              </div>
            ))}
          </div>

          <div className="min-w-0">
            <p className="mb-2 text-micro text-ink-muted">
              Diuji pada {data.split?.test ?? "sampel uji"} · angka kecil di bawah nilai baseline
              adalah selisih vs baseline pada baris itu (model dikurangi baseline).
            </p>
            <TableWrap>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <Th>Kandidat</Th>
                    {METRICS.map((m) => (
                      <Th key={m.key} align="right">
                        {m.label}
                      </Th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <Td className="font-semibold text-ink">
                      {data.model_name} <span className="font-normal text-ink-muted">· model</span>
                    </Td>
                    {METRICS.map((m) => (
                      <Td key={m.key} align="right">
                        <span className="num font-semibold text-ink">
                          {fmtNum(metrics?.[m.key], 3)}
                        </span>
                        {m.key === "macro_f1" && (
                          <div className="mt-1.5">
                            <MiniBar pct={metrics?.macro_f1 ?? 0} />
                          </div>
                        )}
                      </Td>
                    ))}
                  </tr>
                  {CANDIDATES.map((c) => {
                    const score = data.baselines?.[c.key];
                    return (
                      <tr key={c.key}>
                        <Td>
                          {c.label} <span className="text-ink-muted">· baseline</span>
                        </Td>
                        {METRICS.map((m) => {
                          const own = metrics?.[m.key];
                          const base = score?.[m.key];
                          return (
                            <Td key={m.key} align="right">
                              <span className="num text-ink-soft">{fmtNum(base, 3)}</span>
                              <div className="mt-1">
                                <Delta value={own != null && base != null ? own - base : null} />
                              </div>
                              {m.key === "macro_f1" && (
                                <div className="mt-1.5">
                                  <MiniBar pct={base ?? 0} />
                                </div>
                              )}
                            </Td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableWrap>
          </div>
        </div>
      </Card>

      {/* ── 2. metrik per kelas ── */}
      <Card pad={false}>
        <PanelHead
          title="Metrik per kelas"
          sub={`${fmtInt(perClass.length)} kelas · dukungan = jumlah label pada split uji`}
          icon="layers"
        />
        <div className="p-4">
          {perClass.length ? (
            <>
              <TableWrap>
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      <Th>Kelas</Th>
                      <Th align="right">Presisi</Th>
                      <Th align="right">Recall</Th>
                      <Th align="right">F1</Th>
                      <Th align="right">Dukungan (uji)</Th>
                      <Th>Proporsi F1</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {perClass.map((p) => {
                      const meta = causeMeta(p.cause);
                      const isLow = lowest?.cause === p.cause;
                      return (
                        <tr key={p.cause} className={isLow ? "bg-warn/10" : undefined}>
                          <Td className={isLow ? "text-ink" : undefined}>
                            <span className="flex items-center gap-2">
                              <span
                                className="h-2 w-2 shrink-0 rounded-full"
                                style={{ background: meta.color }}
                                aria-hidden="true"
                              />
                              {causeLabel(p.cause)}
                              {isLow && (
                                <span className="inline-flex items-center gap-1 text-micro text-warn">
                                  <Icon name="alert-triangle" size={12} />
                                  F1 terendah
                                </span>
                              )}
                            </span>
                          </Td>
                          <Td align="right">
                            <span className="num">{fmtNum(p.precision, 3)}</span>
                          </Td>
                          <Td align="right">
                            <span className="num">{fmtNum(p.recall, 3)}</span>
                          </Td>
                          <Td align="right">
                            <span className="num font-semibold text-ink">{fmtNum(p.f1, 3)}</span>
                          </Td>
                          <Td align="right">
                            <span className="num">{fmtInt(p.support)}</span>
                          </Td>
                          <Td className="w-[26%] min-w-[120px]">
                            <MiniBar pct={p.f1} />
                          </Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </TableWrap>
              {lowest && (
                <p className="mt-2 flex items-start gap-1.5 text-micro text-ink-muted">
                  <Icon name="alert-triangle" size={12} className="mt-0.5 shrink-0 text-warn" />
                  <span>
                    {causeLabel(lowest.cause)} punya F1 terendah pada split ini; kekeliruan antar
                    kelas yang melatarinya dijelaskan pada blok "Batasan dan kondisi gagal" di
                    bawah — angka di tabel ini tidak boleh dikutip tanpa konteks batasan tersebut.
                  </span>
                </p>
              )}
            </>
          ) : (
            <p className="text-micro text-ink-muted">Metrik per kelas belum tersedia dari API.</p>
          )}
        </div>
      </Card>

      {/* ── 3. matriks konfusi ── */}
      <Card pad={false}>
        <PanelHead
          title="Matriks konfusi"
          sub="Baris = label aktual, kolom = prediksi · sel diagonal (prediksi benar) ditebalkan"
          icon="activity"
        />
        <div className="p-4">
          {cm?.labels?.length ? (
            <TableWrap>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <Th className="w-32">Aktual \ Prediksi</Th>
                    {cm.labels.map((l) => (
                      <Th key={l} className="h-28 [writing-mode:vertical-rl]">
                        {causeLabel(l)}
                      </Th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cm.matrix.map((row, i) => (
                    <tr key={cm.labels[i] ?? i}>
                      <Td className="whitespace-nowrap">{causeLabel(cm.labels[i] ?? "")}</Td>
                      {row.map((v, j) => (
                        <Td
                          key={j}
                          align="right"
                          className={cn(
                            "num",
                            i === j && "bg-primary-quiet font-semibold text-ink",
                            i !== j && v === 0 && "text-ink-muted",
                          )}
                        >
                          {v === 0 ? "·" : fmtInt(v)}
                        </Td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          ) : (
            <p className="text-micro text-ink-muted">Matriks konfusi belum tersedia dari API.</p>
          )}
        </div>
      </Card>

      {/* ── 4. protokol split + penjaga kebocoran ── */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card pad={false}>
          <PanelHead title="Protokol split" sub="Split temporal, tanpa pengacakan" icon="layers" />
          <div className="space-y-2 p-4">
            {SPLIT_ROWS.map((r) => (
              <div
                key={r.key}
                className="flex items-center justify-between gap-3 border-b border-line/60 pb-1.5 text-cell last:border-0"
              >
                <span className="text-ink-muted">{r.label}</span>
                <span className="num text-ink">{data.split?.[r.key] ?? "—"}</span>
              </div>
            ))}
            <p className="pt-1 text-micro text-ink-muted">
              {data.split?.protocol ?? "Protokol split belum dikirim API."}
            </p>
            {data.classes?.length ? (
              <p className="text-micro text-ink-muted">
                {fmtInt(data.classes.length)} kelas: {data.classes.map(causeLabel).join(" · ")}
              </p>
            ) : null}
          </div>
        </Card>

        <Card pad={false}>
          <PanelHead
            title="Penjaga kebocoran label"
            sub={`${fmtInt(data.leakage_guard?.length ?? 0)} aturan aktif · dievaluasi global, bukan per split`}
            icon="check-circle"
          />
          <div className="p-4">
            {data.leakage_guard?.length ? (
              <ul className="space-y-2">
                {data.leakage_guard.map((l) => (
                  <li key={l} className="flex items-start gap-2 text-micro text-ink-soft">
                    <Icon name="check-circle" size={13} className="mt-0.5 shrink-0 text-ok" />
                    <span>{l}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-micro text-ink-muted">Daftar aturan belum tersedia dari API.</p>
            )}
          </div>
        </Card>
      </div>

      {/* ── 5. fitur paling berpengaruh ── */}
      <Card pad={false}>
        <PanelHead
          title="Fitur paling berpengaruh"
          sub={`${fmtInt(features.length)} teratas dari ${fmtInt(allFeatures.length)} fitur · urut menurun`}
          icon="sliders"
        />
        <div className="p-4">
          {features.length ? (
            <TableWrap>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    <Th>Fitur</Th>
                    <Th align="right">Kepentingan</Th>
                    <Th>Proporsi</Th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((f) => (
                    <tr key={f.feature}>
                      <Td className="text-ink">{f.feature}</Td>
                      <Td align="right">
                        <span className="num">{fmtNum(f.importance, 4)}</span>
                      </Td>
                      <Td className="w-[38%] min-w-[140px]">
                        <MiniBar pct={featMax > 0 ? f.importance / featMax : 0} />
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          ) : (
            <p className="text-micro text-ink-muted">Feature importance belum tersedia dari API.</p>
          )}
        </div>
      </Card>

      {/* ── 6. batasan — bobot visual setara hero ── */}
      <Card pad={false} className="border-l-4 border-l-warn">
        <PanelHead
          title="Batasan dan kondisi gagal"
          sub="Wajib dibaca sebelum mengutip angka mana pun di halaman ini"
          icon="alert-triangle"
        />
        <div className="p-4">
          {data.limitations?.length ? (
            <ul className="grid gap-3 md:grid-cols-2">
              {data.limitations.map((l) => (
                <li
                  key={l}
                  className="flex items-start gap-2.5 rounded-card border border-line bg-raised px-3 py-2.5"
                >
                  <Icon name="alert-triangle" size={16} className="mt-0.5 shrink-0 text-warn" />
                  <span className="text-body text-ink-soft">{l}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-micro text-ink-muted">Daftar batasan belum tersedia dari API.</p>
          )}
        </div>
      </Card>

      {/* ── 7. catatan sumber angka ── */}
      <Card className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-micro text-ink-muted">
          Nilai dibaca langsung dari {data.artifacts?.metrics ?? "metrics.json"} — tidak ada angka
          yang ditulis manual. Model dilatih {trained}
          {data.artifacts?.model ? ` · artefak ${data.artifacts.model}` : ""}.
        </p>
        <SeedBadge />
      </Card>
    </div>
  );
};
