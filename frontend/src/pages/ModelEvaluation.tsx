import { useState } from "react";
import { Segmented } from "../components/ui";
import { ForecastEvaluation } from "../components/evaluation/ForecastEvaluation";
import { ClassifierEvaluation } from "../components/evaluation/ClassifierEvaluation";
import { DetectionEvaluation } from "../components/evaluation/DetectionEvaluation";

type Tab = "forecast" | "cause" | "detection";

const TABS: { value: Tab; label: string }[] = [
  { value: "forecast", label: "Peramalan volume · utama" },
  { value: "cause", label: "Penyebab bottleneck" },
  { value: "detection", label: "Deteksi YOLO" },
];

/** Bukti model. Tugas D2 utama (peramalan) didahulukan; dua model lain pendukung.
    Tiap tab membaca artefak evaluasinya sendiri; metrik antar tugas tidak dicampur. */
export const ModelEvaluation = () => {
  const [tab, setTab] = useState<Tab>("forecast");
  return (
    <div className="flex flex-col gap-3">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-title-sm font-semibold text-ink">Evaluasi model</h1>
          <p className="mt-0.5 text-micro text-ink-muted">
            Semua angka dari artefak <code>python backend/scripts/run_d2_evaluation.py</code> · data sintetis seed 42
          </p>
        </div>
        <Segmented options={TABS} value={tab} onChange={setTab} />
      </header>
      {tab === "forecast" && <ForecastEvaluation />}
      {tab === "cause" && <ClassifierEvaluation />}
      {tab === "detection" && <DetectionEvaluation />}
    </div>
  );
};
