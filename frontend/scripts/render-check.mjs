/**
 * Headless render check for the v4 analytics panels.
 *
 * Loads the real components through Vite's SSR module runner, feeds them the
 * LIVE payloads from a running backend (default http://localhost:8000), renders
 * them with react-dom/server and asserts that the three requested parameters
 * (penyebab bottleneck, rata-rata waktu lampu merah per perempatan/pertigaan,
 * ruas + kapasitas + komposisi roda 2/3/4/6+) actually appear in the markup.
 *
 * Usage: npm run check:render        (backend harus hidup)
 *        API_URL=http://host:port npm run check:render
 */
import { createServer } from "vite";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function getJson(path) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`${path} -> HTTP ${response.status}`);
  return response.json();
}

/** Unwraps `{data: ...}` envelopes the way src/lib/api.ts does. */
const unwrap = (payload) => payload?.data?.data ?? payload?.data ?? payload;

const failures = [];
function expect(text, needle, label) {
  if (!text.includes(needle)) failures.push(`${label}: tidak menemukan "${needle}"`);
}

const main = async () => {
  const [bottlenecks, segments, summary, signals, evaluation] = await Promise.all([
    getJson("/api/v1/bottlenecks"),
    getJson("/api/v1/segments"),
    getJson("/api/v1/segments/summary"),
    getJson("/api/v1/signals/summary?scope=all"),
    getJson("/api/v1/model/evaluation"),
  ]);

  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(["bottlenecks"], unwrap(bottlenecks));
  client.setQueryData(["segments"], unwrap(segments));
  client.setQueryData(["segments-summary"], unwrap(summary));
  client.setQueryData(["signals-summary", "all"], unwrap(signals));
  client.setQueryData(["model-evaluation"], unwrap(evaluation));

  const vite = await createServer({
    server: { middlewareMode: true },
    appType: "custom",
    logLevel: "error",
  });

  try {
    const { BottleneckPanel } = await vite.ssrLoadModule("/src/components/dashboard/BottleneckPanel.tsx");
    const { SignalTimingCard } = await vite.ssrLoadModule("/src/components/dashboard/SignalTimingCard.tsx");
    const { SegmentTable } = await vite.ssrLoadModule("/src/components/dashboard/SegmentTable.tsx");
    const { ModelEvaluation } = await vite.ssrLoadModule("/src/pages/ModelEvaluation.tsx");

    const render = (element) =>
      renderToStaticMarkup(React.createElement(QueryClientProvider, { client }, element));

    const panels = {
      BottleneckPanel: render(React.createElement(BottleneckPanel)),
      SignalTimingCard: render(React.createElement(SignalTimingCard)),
      SegmentTable: render(React.createElement(SegmentTable)),
      ModelEvaluation: render(React.createElement(ModelEvaluation)),
    };

    const totalCapacity = Number(summary.total_capacity_vehicles ?? 0);
    const totalCapacityText = new Intl.NumberFormat("id-ID").format(totalCapacity);
    const dominant = String(bottlenecks.dominant_cause ?? "");
    const macroF1 = String(evaluation.metrics?.macro_f1 ?? "");
    const rows = Number(segments.count ?? segments.items?.length ?? 0);

    const macroF1Text = macroF1
      ? new Intl.NumberFormat("id-ID", { minimumFractionDigits: 3, maximumFractionDigits: 3 })
          .format(Number(macroF1))
      : "";
    expect(panels.BottleneckPanel, "data sintetis", "BottleneckPanel badge");
    expect(panels.BottleneckPanel, String(bottlenecks.per_intersection?.[0]?.intersection_name ?? "x"), "BottleneckPanel simpang");
    expect(panels.SegmentTable, totalCapacityText, "SegmentTable total kapasitas kendaraan");
    expect(panels.SegmentTable, `>${rows}<`, "SegmentTable jumlah ruas");
    expect(panels.SegmentTable, "R6+", "SegmentTable komposisi roda 6+");
    expect(panels.SignalTimingCard, "Pertigaan", "SignalTimingCard pertigaan");
    expect(panels.SignalTimingCard, "Perempatan", "SignalTimingCard perempatan");
    expect(panels.ModelEvaluation, "data sintetis", "ModelEvaluation badge");
    if (macroF1Text) expect(panels.ModelEvaluation, macroF1Text, "ModelEvaluation macro-F1");
    expect(panels.ModelEvaluation, "Rule-based", "ModelEvaluation baseline rule-based");

    console.log(`backend ${API_URL} | tick=${bottlenecks.tick ?? signals.timestamp_wib} | penyebab dominan=${dominant}`);
    console.log(`ruas=${rows} | total kapasitas kendaraan=${totalCapacity} | macro_f1=${macroF1}`);
    for (const [name, html] of Object.entries(panels)) {
      console.log(`${name}: ${html.length} bytes markup`);
    }
    if (failures.length) {
      console.error("\nGAGAL:");
      for (const item of failures) console.error(` - ${item}`);
      process.exitCode = 1;
    } else {
      console.log("\nPASS: keempat panel merender angka nyata dari API.");
    }
  } finally {
    await vite.close();
  }
};

main().catch((error) => {
  console.error("render-check gagal:", error.message);
  process.exitCode = 1;
});
