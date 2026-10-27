import { useSignalsSummary } from "../../hooks/useTraffixData";
import { Card, PanelHead, SeedBadge, TableWrap, Td, Th } from "../ui";
import { PanelState } from "./Panel";
import { fmtInt, fmtNum } from "../../lib/format";

type Agg = {
  intersection_count: number;
  cycle_length_s: number;
  avg_green_s: number;
  avg_red_s: number;
  avg_wait_time_min: number;
};

const Tile = ({
  label,
  value,
  unit,
  tone = "text-ink",
  hint,
}: {
  label: string;
  value: string;
  unit: string;
  tone?: string;
  hint?: string;
}) => (
  <div className="rounded-control border border-line bg-raised px-3 py-2">
    <p className="label-caps">{label}</p>
    <p className={`num mt-1 text-title-sm font-semibold ${tone}`}>
      {value}
      <span className="ml-1 text-micro font-normal text-ink-muted">{unit}</span>
    </p>
    {hint && <p className="mt-0.5 text-micro text-ink-muted">{hint}</p>}
  </div>
);

const ScopeRow = ({ label, agg }: { label: string; agg: Agg | null }) => (
  <div className="grid grid-cols-[1fr_repeat(4,minmax(0,4.5rem))] items-baseline gap-2 rounded-control border border-line bg-raised px-3 py-2">
    <span className="text-micro text-ink-soft">
      {label}
      <span className="ml-1.5 text-ink-muted">
        {agg ? `${fmtInt(agg.intersection_count)} simpang` : "tidak ada data"}
      </span>
    </span>
    {[
      { v: fmtNum(agg?.cycle_length_s, 0), u: "dtk" },
      { v: fmtNum(agg?.avg_green_s, 1), u: "dtk" },
      { v: fmtNum(agg?.avg_red_s, 1), u: "dtk" },
      { v: fmtNum(agg?.avg_wait_time_min, 2), u: "mnt" },
    ].map((cell, i) => (
      <span key={i} className="num text-right text-cell text-ink">
        {cell.v}
        <span className="ml-1 text-micro text-ink-muted">{cell.u}</span>
      </span>
    ))}
  </div>
);

/** Kartu waktu lampu: siklus/hijau/merah (dtk) + rata-rata waktu tunggu (menit). */
export const SignalTimingCard = () => {
  const { data, isLoading, isError } = useSignalsSummary("all");

  const scopeAgg = (scope: "perempatan" | "pertigaan"): Agg | null => {
    const item = data?.items?.find((i) => i.scope === scope);
    if (item) return item;
    const rows = (data?.per_intersection ?? []).filter((p) => p.tipe_persimpangan === scope);
    if (!rows.length) return null;
    const mean = (pick: (r: (typeof rows)[number]) => number) =>
      rows.reduce((sum, r) => sum + pick(r), 0) / rows.length;
    return {
      intersection_count: rows.length,
      cycle_length_s: mean((r) => r.cycle_length_s),
      avg_green_s: mean((r) => r.avg_green_s),
      avg_red_s: mean((r) => r.avg_red_s),
      avg_wait_time_min: mean((r) => r.avg_wait_time_min),
    };
  };

  const empat = scopeAgg("perempatan");
  const tiga = scopeAgg("pertigaan");
  /* Rata-rata semua simpang = rata-rata agregat perempatan + pertigaan. */
  const waitAll =
    empat && tiga
      ? (empat.avg_wait_time_min + tiga.avg_wait_time_min) / 2
      : (data?.avg_wait_time_min ?? null);

  return (
    <Card pad={false}>
      <PanelHead
        icon="clock"
        title="Rata-rata waktu lampu"
        sub={
          data
            ? `${fmtInt(data.intersection_count)} simpang · ${fmtInt(data.section_count)} pendekat ber-lampu`
            : "agregat siklus sinyal"
        }
        right={<SeedBadge />}
      />

      {isLoading || isError || !data ? (
        <PanelState
          kind={isLoading ? "loading" : "error"}
          message="Endpoint /api/v1/signals/summary tidak merespons."
        />
      ) : (
        <div className="space-y-3 p-4">
          <div className="grid grid-cols-2 gap-2">
            <Tile label="Siklus" value={fmtNum(data.cycle_length_s, 0)} unit="dtk" />
            <Tile label="Hijau" value={fmtNum(data.avg_green_s, 1)} unit="dtk" tone="text-ok" />
            <Tile label="Merah" value={fmtNum(data.avg_red_s, 1)} unit="dtk" tone="text-crit" />
            <Tile
              label="Waktu tunggu"
              value={fmtNum(waitAll, 2)}
              unit="menit"
              tone="text-warn"
              hint="rerata perempatan + pertigaan"
            />
          </div>

          <div className="space-y-1.5">
            <p className="label-caps">Agregat per tipe simpang · siklus / hijau / merah / tunggu</p>
            <ScopeRow label="Perempatan (4 lengan)" agg={empat} />
            <ScopeRow label="Pertigaan (3 lengan)" agg={tiga} />
          </div>

          <TableWrap>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <Th>Simpang</Th>
                  <Th align="right">Siklus dtk</Th>
                  <Th align="right">Hijau dtk</Th>
                  <Th align="right">Merah dtk</Th>
                  <Th align="right">Tunggu menit</Th>
                  <Th align="right">Antrean kend</Th>
                  <Th align="right">Tundaan dtk</Th>
                </tr>
              </thead>
              <tbody>
                {(data.per_intersection ?? []).map((p) => (
                  <tr key={p.intersection_id}>
                    <Td>
                      <span className="text-ink">{p.intersection_name}</span>
                      <span className="mt-0.5 block text-micro text-ink-muted">
                        {p.intersection_id} · {p.tipe_persimpangan} · {fmtInt(p.jumlah_lengan)} lengan
                      </span>
                    </Td>
                    <Td align="right">
                      <span className="num">{fmtNum(p.cycle_length_s, 0)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num text-ok">{fmtNum(p.avg_green_s, 1)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num text-crit">{fmtNum(p.avg_red_s, 1)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num text-warn">{fmtNum(p.avg_wait_time_min, 2)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num">{fmtNum(p.avg_queue_veh, 1)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num">{fmtNum(p.avg_delay_s, 1)}</span>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </div>
      )}
    </Card>
  );
};
