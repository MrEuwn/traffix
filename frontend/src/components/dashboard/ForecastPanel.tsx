import { usePredictions } from "../../hooks/useTraffixData";
import { Card, PanelHead, StateBlock, StatusPill, cn } from "../ui";
import { fmtInt, fmtPct } from "../../lib/format";
import type { ForecasterStatus, Prediction } from "../../types";

const HORIZON_LABEL: Record<string, string> = { "15m": "15 menit", "2h": "2 jam", "4h": "4 jam" };

const hm = (raw: string | null) => (raw ? raw.slice(11, 16) : "—");

/** Prakiraan volume simpang dari model D2 (LSTM) pada menit replay saat ini.
    Semua angka dari GET /api/v1/predictions; galat tipikal dari artefak evaluasi. */
export const ForecastPanel = ({
  intersectionId,
  name,
  forecaster,
}: {
  intersectionId: string;
  name: string;
  forecaster?: ForecasterStatus;
}) => {
  const { data, isLoading, isError, refetch } = usePredictions(intersectionId);
  const predictions: Prediction[] = data?.predictions ?? [];
  const source = predictions[0]?.source;
  const current = predictions[0]?.current_volume ?? null;
  const issue = predictions[0]?.issue_time_wib ?? null;
  const split = predictions[0]?.replay_split ?? null;

  if (isLoading) return <StateBlock state="loading" height={176} />;
  if (isError || !predictions.length)
    return (
      <StateBlock
        state="error"
        height={176}
        hint="Endpoint /api/v1/predictions tidak merespons."
        onRetry={() => refetch()}
      />
    );

  return (
    <Card pad={false}>
      <PanelHead
        title="Prakiraan volume simpang"
        sub={`${name} · diterbitkan ${hm(issue)} WIB (waktu replay)`}
        icon="trending-up"
        right={
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {source === "lstm" ? (
              <StatusPill tone="ok" label="LSTM" icon="chart" />
            ) : (
              <StatusPill tone="warn" label="Heuristik" icon="chart" />
            )}
            {split && (
              <StatusPill
                tone={split === "uji" ? "info" : "warn"}
                label={
                  split === "uji"
                    ? "Hari uji · tak terlihat saat latih"
                    : split === "latih"
                      ? "Hari latih · in-sample"
                      : "Hari validasi · dipakai seleksi"
                }
              />
            )}
          </div>
        }
      />
      <div className="space-y-3 p-4">
        <div className="flex items-baseline justify-between gap-3 text-micro text-ink-muted">
          <span>Volume saat ini</span>
          <span className="num text-body font-semibold text-ink">
            {fmtInt(current)} <span className="text-micro font-normal text-ink-muted">kend/jam</span>
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {predictions.map((p) => {
            const delta =
              current && current > 0 ? ((p.predicted_vehicle_count - current) / current) * 100 : null;
            return (
              <div key={p.horizon} className="rounded-card border border-line bg-raised px-2.5 py-2">
                <p className="label-caps">{HORIZON_LABEL[p.horizon] ?? p.horizon}</p>
                <p className="num mt-0.5 text-title-sm font-semibold text-ink">
                  {fmtInt(p.predicted_vehicle_count)}
                </p>
                <p className="text-micro text-ink-muted">kend/jam · {hm(p.target_time_wib)}</p>
                {p.expected_mae != null && (
                  <p className="num mt-0.5 text-micro text-ink-muted" title="MAE LSTM pada replay v4 hari 7">
                    ±{fmtInt(p.expected_mae)} galat tipikal
                  </p>
                )}
                {delta != null && (
                  <p className={cn("num text-micro", delta >= 0 ? "text-warn" : "text-ok")}>
                    {delta >= 0 ? "+" : ""}
                    {fmtPct(delta / 100, 0)} vs kini
                  </p>
                )}
              </div>
            );
          })}
        </div>
        <p className="text-micro text-ink-muted">
          {source === "lstm"
            ? "Masukan: 41 fitur dari jendela riwayat replay sintetis v4. Galat tipikal = MAE uji transfer pada replay v4, bukan selang keyakinan."
            : "Rata-rata volume 15 menit terakhir."}
          {forecaster && source === "lstm" && (
            <>
              {" "}
              {forecaster.matches_evaluation
                ? "File model yang melayani identik (sha256) dengan yang dievaluasi."
                : "Peringatan: file model berbeda dari yang dievaluasi."}
            </>
          )}
        </p>
      </div>
    </Card>
  );
};
