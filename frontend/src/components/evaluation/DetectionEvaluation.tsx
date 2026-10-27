import { useDetectionEvidence } from "../../hooks/useTraffixData";
import { fmtInt, fmtNum } from "../../lib/format";
import { Card, PanelHead, StateBlock, StatusPill } from "../ui";
import { Icon } from "../ui/icons";

/** Model pendukung: YOLOv8. Metrik tercatat adalah VALIDASI dari notebook; tidak ada set uji. */
export const DetectionEvaluation = () => {
  const { data, isLoading, isError, refetch } = useDetectionEvidence();
  if (isLoading) return <StateBlock state="loading" height={300} />;
  if (isError || !data?.recorded_validation)
    return (
      <StateBlock
        state="error"
        height={300}
        hint="Bukti YOLO belum tersedia — jalankan python backend/scripts/run_d2_evaluation.py"
        onRetry={() => refetch()}
      />
    );
  const v = data.recorded_validation;
  const fi = data.frame_inference;
  const tiles = [
    ["mAP50", v.ultralytics.map50],
    ["mAP50-95", v.ultralytics.map50_95],
    ["Precision (Ultralytics)", v.ultralytics.precision],
    ["Recall (Ultralytics)", v.ultralytics.recall],
    ["F1 (IoU≥0,5, conf 0,25)", v.iou50_matching_conf025["F1-score"]],
  ] as const;

  return (
    <div className="flex flex-col gap-3">
      <Card pad={false}>
        <PanelHead
          title="Model YOLOv8 tim (best.pt) — metrik validasi tercatat"
          sub={`${v.dataset} · ${fmtInt(v.images.val)} gambar validasi · ${fmtInt(v.val_instances)} objek`}
          icon="car"
          right={<StatusPill tone="warn" label="Validasi · bukan uji" icon="info" />}
        />
        <div className="space-y-3 p-4">
          <div className="grid gap-2.5 sm:grid-cols-3 xl:grid-cols-5">
            {tiles.map(([k, val]) => (
              <div key={k} className="rounded-card border border-line bg-raised px-3 py-2.5">
                <p className="label-caps">{k}</p>
                <p className="num text-metric font-semibold text-ink">{fmtNum(val, 3)}</p>
              </div>
            ))}
          </div>
          <p className="text-micro text-ink-muted">
            Sumber: {v.source}. Tidak direproduksi pada run ini: {v.why_not_reproduced}
          </p>
          <ul className="space-y-1.5">
            {v.caveats.map((c) => (
              <li key={c} className="flex items-start gap-1.5 text-micro text-ink-soft">
                <Icon name="alert-triangle" size={12} className="mt-0.5 shrink-0 text-warn" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </Card>

      <Card pad={false}>
        <PanelHead
          title="Inferensi nyata pada rekaman CCTV"
          sub="Tanpa label acuan — angka adalah keluaran model, bukan akurasi"
          icon="activity"
          right={
            <StatusPill
              tone={data.live_inference_available ? "ok" : "idle"}
              label={data.live_inference_available ? "Inferensi langsung tersedia" : "Hanya hasil tersimpan"}
            />
          }
        />
        <div className="space-y-2 p-4">
          {fi?.summary ? (
            <>
              <p className="text-body text-ink-soft">
                Detektor demo: <b>{fi.model.description ?? fi.model.weights}</b> · kelas {fi.model.classes.join(", ")} ·{" "}
                {fi.model.imgsz} px · {fmtNum(fi.summary.mean_inference_ms, 0)} ms/frame di CPU.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-micro">
                  <thead>
                    <tr className="text-left text-ink-muted">
                      <th className="py-1 pr-3 font-normal">Rata-rata kotak per frame</th>
                      {Object.keys(fi.summary.by_period).map((p) => (
                        <th key={p} className="py-1 pr-3 text-right font-normal">
                          {p} ({fmtInt(fi.summary!.by_period[p].frames)})
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="num">
                    <tr>
                      <td className="py-1 pr-3 text-ink">YOLOv8m COCO (demo)</td>
                      {Object.values(fi.summary.by_period).map((s, i) => (
                        <td key={i} className="py-1 pr-3 text-right text-ink">{fmtNum(s.mean_vehicle_count, 2)}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="py-1 pr-3 text-ink-soft">Model tim best.pt</td>
                      {Object.values(fi.summary.by_period).map((s, i) => (
                        <td key={i} className="py-1 pr-3 text-right text-ink-soft">{fmtNum(s.mean_team_model_count, 2)}</td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-micro text-ink-muted">
                Model tim (1 kelas, dilatih pada 399 gambar Kaggle berisi mobil besar dari dekat) melewatkan sebagian besar
                kendaraan kecil di CCTV tol yang memotret dari ketinggian, sehingga demo memakai YOLOv8m pretrained COCO yang
                tidak dilatih ulang tim. Tanpa label acuan, angka di tabel adalah jumlah keluaran model — bukan akurasi. Hitungan
                kamera tidak dipakai sebagai input model peramalan.
              </p>
            </>
          ) : (
            <p className="text-micro text-ink-muted">Belum ada hasil inferensi frame.</p>
          )}
        </div>
      </Card>
    </div>
  );
};
