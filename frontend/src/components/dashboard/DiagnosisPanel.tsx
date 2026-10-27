import { useMemo, useState } from "react";
import {
  useBottlenecks,
  useBottlenecksByIntersection,
  useRecommendations,
} from "../../hooks/useTraffixData";
import {
  Btn,
  Card,
  CauseBadge,
  Modal,
  PanelHead,
  ProbabilityBar,
  SeedBadge,
  StatusPill,
  TableWrap,
  Td,
  Th,
} from "../ui";
import { PanelState } from "./Panel";
import { Icon } from "../ui/icons";
import { causeMeta } from "../../lib/causes";
import { fmtInt, fmtNum } from "../../lib/format";
import { approachLabel } from "./format";
import type { Recommendation } from "../../types";

type PanelTone = "ok" | "info" | "warn" | "high" | "crit" | "idle";

const PRIORITY_TONE: Record<string, PanelTone> = {
  LOW: "ok",
  MEDIUM: "warn",
  HIGH: "high",
  CRITICAL: "crit",
};

const actionable = (rec: Recommendation | null) =>
  !!rec && rec.priority !== "LOW" && rec.delta_seconds > 0;

type ApplyPayload = { action: string; detail: string };

/**
 * Panel diagnosis hero: penyebab dominan + keyakinan model + probabilitas 9 kelas
 * + sinyal terkuat model, plus aksi "Setujui Rekomendasi" lewat Modal konfirmasi fase.
 */
export const DiagnosisPanel = ({
  intersectionId,
  onApply,
}: {
  intersectionId?: string;
  onApply: (payload: ApplyPayload) => void;
}) => {
  const { data, isLoading, isError } = useBottlenecks();
  const { data: recommendations = [] } = useRecommendations();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");

  const hero = useMemo(() => {
    const list = data?.per_intersection ?? [];
    if (!list.length) return null;
    return (
      list.find((ix) => ix.intersection_id === intersectionId) ??
      list.find((ix) => ix.model_available !== false && ix.dominant_cause !== "normal") ??
      list[0]
    );
  }, [data, intersectionId]);

  const rec =
    recommendations.find((r) => r.intersection_id === hero?.intersection_id) ?? null;

  const { data: detail } = useBottlenecksByIntersection(hero?.intersection_id ?? "");
  const phaseSections = useMemo(
    () => (detail?.sections ?? []).filter((s) => s.approach),
    [detail],
  );
  /* Fase bottleneck = pendekat dengan rasio V/C tertinggi pada simpang ini. */
  const phase = useMemo(
    () =>
      phaseSections.reduce<(typeof phaseSections)[number] | null>(
        (best, s) => (best === null || (s.vc_ratio ?? 0) > (best.vc_ratio ?? 0) ? s : best),
        null,
      ),
    [phaseSections],
  );

  const canApply = actionable(rec);
  const delta = rec?.delta_seconds ?? 0;
  const otherPhases = Math.max(phaseSections.length - 1, 0);

  const confirm = () => {
    if (!hero || !rec) return;
    onApply({
      action: `Setujui rekomendasi fase · ${hero.intersection_name} · Pendekat ${
        approachLabel(phase?.approach)
      } ${fmtInt(rec.current_green_seconds)}→${fmtInt(rec.recommended_green_seconds)} dtk`,
      detail: note.trim() || "Tanpa catatan operator",
    });
    setOpen(false);
    setNote("");
  };

  return (
    <Card pad={false} className="flex flex-col">
      <PanelHead
        icon="chart"
        title="Diagnosis penyebab bottleneck"
        sub={
          hero
            ? `${hero.intersection_name} · ${hero.intersection_id} · ${hero.tipe_persimpangan}`
            : "klasifikasi 9 kelas penyebab"
        }
        right={<SeedBadge />}
      />

      {(isLoading || isError || !data) && (
        <PanelState kind={isLoading ? "loading" : "error"} message="Endpoint /api/v1/bottlenecks tidak merespons." />
      )}

      {data && hero && (
        <div className="flex flex-1 flex-col gap-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <CauseBadge
              cause={hero.dominant_cause}
              confidence={hero.confidence > 0 ? hero.confidence : undefined}
            />
            {hero.model_available === false && (
              <StatusPill tone="idle" label="fallback aturan" icon="info" />
            )}
            <span className="text-micro text-ink-muted">
              {fmtInt(data.affected_section_count)} dari {fmtInt(data.section_count)} ruas
              terdampak · dominan jaringan{" "}
              <span className="text-ink-soft">{causeMeta(data.dominant_cause).label}</span>
            </span>
          </div>

          <div>
            <p className="label-caps mb-1.5">Distribusi probabilitas model · 9 kelas</p>
            <ProbabilityBar probabilities={hero.probabilities} />
          </div>

          <div>
            <p className="label-caps mb-1.5">Sinyal terkuat model</p>
            {hero.drivers.length ? (
              <ol className="grid gap-1.5 sm:grid-cols-3">
                {hero.drivers.slice(0, 3).map((driver, index) => (
                  <li
                    key={driver}
                    className="flex items-start gap-2 rounded-control border border-line bg-raised px-2.5 py-2 text-micro text-ink-soft"
                  >
                    <span className="num text-ink-muted">{index + 1}</span>
                    <span>{driver}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-micro text-ink-muted">
                Model tidak mengirim daftar sinyal untuk tick ini.
              </p>
            )}
          </div>

          <div className="mt-auto rounded-control border border-line bg-raised p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="label-caps">Rekomendasi fase hijau</span>
              {rec && <StatusPill tone={PRIORITY_TONE[rec.priority] ?? "idle"} label={rec.priority} />}
            </div>

            {rec ? (
              <>
                <p className="mt-2 text-micro text-ink-soft">{rec.reason}</p>
                <dl className="mt-2 grid grid-cols-3 gap-2">
                  {[
                    { label: "Hijau saat ini", value: fmtInt(rec.current_green_seconds), unit: "dtk" },
                    { label: "Hijau usulan", value: fmtInt(rec.recommended_green_seconds), unit: "dtk" },
                    {
                      label: "Selisih",
                      value: `${rec.delta_seconds >= 0 ? "+" : "−"}${fmtInt(Math.abs(rec.delta_seconds))}`,
                      unit: "dtk",
                    },
                  ].map((m) => (
                    <div key={m.label}>
                      <dt className="label-caps">{m.label}</dt>
                      <dd className="num text-title-sm font-semibold text-ink">
                        {m.value}
                        <span className="ml-1 text-micro font-normal text-ink-muted">{m.unit}</span>
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="mt-2 text-micro text-ink-muted">
                  Risiko kemacetan {fmtNum(rec.congestion_risk_percent, 1)} % · simpang{" "}
                  {rec.intersection_id}
                </p>
              </>
            ) : (
              <p className="mt-2 text-micro text-ink-muted">
                Tidak ada rekomendasi aktif untuk simpang ini.
              </p>
            )}

            <Btn
              className="mt-3 w-full"
              icon="check-circle"
              disabled={!canApply}
              onClick={() => setOpen(true)}
            >
              Setujui Rekomendasi
            </Btn>
            <p className="mt-1.5 text-micro text-ink-muted">
              {canApply
                ? "Perubahan hanya disimulasikan di console ini."
                : "Butuh rekomendasi berprioritas di atas LOW dengan penambahan hijau."}
            </p>
          </div>
        </div>
      )}

      <Modal
        open={open}
        title="Konfirmasi perubahan fase"
        sub={
          hero
            ? `${hero.intersection_name} [${hero.intersection_id}] · ${hero.tipe_persimpangan}`
            : undefined
        }
        onClose={() => setOpen(false)}
        footer={
          <>
            <Btn variant="ghost" onClick={() => setOpen(false)}>
              Batal
            </Btn>
            <Btn icon="check-circle" onClick={confirm}>
              Terapkan
            </Btn>
          </>
        }
      >
        <div className="space-y-3">
          <TableWrap>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <Th>Pendekat</Th>
                  <Th align="right">Hijau saat ini</Th>
                  <Th align="right">Hijau usulan</Th>
                  <Th align="right">Selisih</Th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <Td>
                    <span className="text-ink">
                      Pendekat {approachLabel(phase?.approach)} · fase bottleneck
                    </span>
                    <span className="mt-0.5 block text-micro text-ink-muted">
                      {phase?.nama_ruas ?? "—"} · V/C {fmtNum(phase?.vc_ratio, 2)} · LOS{" "}
                      {phase?.los ?? "—"}
                    </span>
                  </Td>
                  <Td align="right">
                    <span className="num text-ink">{fmtInt(rec?.current_green_seconds)}</span> dtk
                  </Td>
                  <Td align="right">
                    <span className="num text-ink">{fmtInt(rec?.recommended_green_seconds)}</span> dtk
                  </Td>
                  <Td align="right">
                    <span className="num text-ok">+{fmtInt(delta)}</span> dtk
                  </Td>
                </tr>
                <tr>
                  <Td>
                    <span className="text-ink">Fase lain · {fmtInt(otherPhases)} pendekat</span>
                    <span className="mt-0.5 block text-micro text-ink-muted">
                      hijau per fase tidak dipecah API — risiko hanya bisa dihitung pada fase
                      bottleneck
                    </span>
                  </Td>
                  <Td align="right">—</Td>
                  <Td align="right">—</Td>
                  <Td align="right">
                    <span className="num text-warn">−{fmtInt(delta)}</span> dtk
                  </Td>
                </tr>
              </tbody>
            </table>
          </TableWrap>

          {delta > 0 && otherPhases > 0 && (
            <div className="flex items-start gap-2 rounded-control border border-warn/40 bg-warn/10 px-3 py-2 text-micro text-ink-soft">
              <Icon name="alert-triangle" size={14} className="mt-0.5 text-warn" />
              <span>
                Fase yang kehilangan waktu: {fmtInt(otherPhases)} pendekat lain kehilangan total{" "}
                <span className="num">{fmtInt(delta)}</span> dtk hijau supaya pendekat{" "}
                {approachLabel(phase?.approach)} mendapat tambahan yang sama.
              </span>
            </div>
          )}

          <label className="block">
            <span className="label-caps mb-1.5 block">Catatan operator</span>
            <textarea
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="mis. tambahan hijau untuk mengurai antrean pendekat timur"
              className="min-h-11 w-full rounded-control border border-line bg-surface px-3 py-2 text-body text-ink outline-none transition-colors focus:border-primary"
            />
          </label>

          <div className="flex items-start gap-2 rounded-control border border-line bg-raised px-3 py-2 text-micro text-ink-soft">
            <Icon name="alert-triangle" size={14} className="mt-0.5 text-warn" />
            <span>Simulasi pada data sintetis — tidak mengubah lampu nyata</span>
          </div>
        </div>
      </Modal>
    </Card>
  );
};
