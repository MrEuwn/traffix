import { useMemo, useState } from "react";
import { useSegments, useSegmentsSummary } from "../../hooks/useTraffixData";
import {
  Card,
  Field,
  LosBadge,
  PanelHead,
  SeedBadge,
  Segmented,
  StateBlock,
  TableWrap,
  Td,
  Th,
  VehicleMixBar,
} from "../ui";
import { Icon } from "../ui/icons";
import { causeMeta } from "../../lib/causes";
import { fmtInt, fmtNum } from "../../lib/format";
import { PanelState } from "./Panel";

type TypeFilter = "all" | "approach" | "corridor";
type LosFilter = "all" | "A" | "B" | "C" | "D" | "E" | "F";
type SortKey = "vc" | "volume" | "queue" | "nama";

const TYPE_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: "all", label: "Semua" },
  { value: "approach", label: "Pendekat" },
  { value: "corridor", label: "Koridor" },
];

const LOS_OPTIONS: { value: LosFilter; label: string }[] = [
  { value: "all", label: "Semua" },
  ...(["A", "B", "C", "D", "E", "F"] as const).map((g) => ({ value: g, label: g })),
];

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "vc", label: "V/C" },
  { value: "volume", label: "Volume" },
  { value: "queue", label: "Antrean" },
  { value: "nama", label: "Nama" },
];

const TipeCell = ({ value }: { value: string }) => (
  <span className="inline-flex items-center gap-1 rounded-bar border border-line bg-raised px-1.5 py-0.5 text-caps text-ink-soft">
    <Icon name={value === "corridor" ? "layers" : "pin"} size={12} />
    {value === "corridor" ? "Koridor" : "Pendekat"}
  </span>
);

/** Tabel 30 ruas: kapasitas, volume smp/jam, V/C, LOS, komposisi roda. */
export const SegmentTable = () => {
  const { data, isLoading, isError } = useSegments();
  const { data: summary } = useSegmentsSummary();
  const [q, setQ] = useState("");
  const [type, setType] = useState<TypeFilter>("all");
  const [los, setLos] = useState<LosFilter>("all");
  const [sort, setSort] = useState<SortKey>("vc");

  const items = useMemo(() => data?.items ?? [], [data]);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const filtered = items.filter(
      (s) =>
        (type === "all" || s.section_type === type) &&
        (los === "all" || s.los === los) &&
        (!needle ||
          s.nama_ruas.toLowerCase().includes(needle) ||
          s.section_id.toLowerCase().includes(needle)),
    );
    return [...filtered].sort((a, b) => {
      if (sort === "nama") return a.nama_ruas.localeCompare(b.nama_ruas);
      if (sort === "queue") return (b.queue_length_veh ?? 0) - (a.queue_length_veh ?? 0);
      if (sort === "volume") return (b.kendaraan?.smp_ekivalen ?? 0) - (a.kendaraan?.smp_ekivalen ?? 0);
      return (b.vc_ratio ?? 0) - (a.vc_ratio ?? 0);
    });
  }, [items, q, type, los, sort]);

  const stats = [
    {
      label: "Jumlah ruas",
      value: fmtInt(summary?.section_count ?? items.length),
      unit: "ruas",
    },
    {
      label: "Pendekat / koridor",
      value: summary ? `${fmtInt(summary.approach_count)} / ${fmtInt(summary.corridor_count)}` : "—",
      unit: "",
    },
    {
      label: "Kapasitas kend",
      value: fmtInt(summary?.total_capacity_vehicles ?? data?.total_capacity_vehicles),
      unit: "kend",
    },
    { label: "Kapasitas", value: fmtInt(summary?.total_capacity_smp_per_jam), unit: "smp/jam" },
    { label: "Rata-rata V/C", value: fmtNum(summary?.avg_vc_ratio, 2), unit: "" },
    { label: "Rata-rata kecepatan", value: fmtNum(summary?.avg_speed_kmh, 1), unit: "km/jam" },
  ];

  return (
    <Card pad={false}>
      <PanelHead
        icon="layers"
        title="Ruas jalan & komposisi kendaraan"
        sub={
          data
            ? `${fmtInt(data.count)} ruas · tick ${fmtInt(data.tick)} · kapasitas ${fmtInt(
                summary?.total_capacity_smp_per_jam ?? data.total_capacity_vehicles,
              )} smp/jam`
            : "30 ruas pendekat + koridor"
        }
        right={<SeedBadge />}
      />

      {isLoading || isError || !data ? (
        <PanelState
          kind={isLoading ? "loading" : "error"}
          message="Endpoint /api/v1/segments tidak merespons."
        />
      ) : (
        <div className="space-y-3 p-4">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            {stats.map((s) => (
              <div key={s.label} className="rounded-control border border-line bg-raised px-3 py-2">
                <p className="label-caps">{s.label}</p>
                <p className="num mt-1 text-cell font-semibold text-ink">
                  {s.value}
                  {s.unit && <span className="ml-1 text-micro font-normal text-ink-muted">{s.unit}</span>}
                </p>
              </div>
            ))}
          </div>

          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto_auto] md:items-end">
            <Field
              label="Cari ruas"
              placeholder="nama ruas atau section id"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Segmented label="Tipe" options={TYPE_OPTIONS} value={type} onChange={setType} />
            <Segmented label="LOS" options={LOS_OPTIONS} value={los} onChange={setLos} />
            <Segmented label="Urut" options={SORT_OPTIONS} value={sort} onChange={setSort} />
          </div>

          <TableWrap>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <Th>Ruas jalan</Th>
                  <Th align="right" className="hidden xl:table-cell">Panjang m</Th>
                  <Th align="right" className="hidden xl:table-cell">Lajur</Th>
                  <Th align="right">Kap. smp/jam</Th>
                  <Th align="right">Kap. kend</Th>
                  <Th align="right">Volume smp/jam</Th>
                  <Th align="right">V/C</Th>
                  <Th>LOS</Th>
                  <Th>Komposisi</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.section_id}>
                    <Td>
                      <span className="block text-ink">{s.nama_ruas}</span>
                      <span className="mt-0.5 block text-micro text-ink-muted">
                        {s.section_id} · {s.intersection_id}
                        {s.approach ? ` · Pendekat ${s.approach}` : ""}
                      </span>
                      <span className="mt-1 flex flex-wrap items-center gap-1.5">
                        <TipeCell value={s.section_type} />
                        <span
                          className="inline-flex items-center gap-1 text-micro"
                          style={{ color: causeMeta(s.penyebab_dominan || s.bottleneck_cause).color }}
                        >
                          <Icon
                            name={causeMeta(s.penyebab_dominan || s.bottleneck_cause).icon}
                            size={12}
                          />
                          {causeMeta(s.penyebab_dominan || s.bottleneck_cause).label}
                        </span>
                      </span>
                    </Td>
                    <Td align="right" className="hidden xl:table-cell">
                      <span className="num">{fmtInt(s.panjang_m)}</span>
                    </Td>
                    <Td align="right" className="hidden xl:table-cell">
                      <span className="num">{fmtInt(s.jumlah_lajur)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num">{fmtInt(s.kapasitas_smp_per_jam)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num">{fmtInt(s.kapasitas_kendaraan)}</span>
                    </Td>
                    <Td align="right">
                      <span className="num text-ink" title="ekuivalen volume kend/jam dalam smp/jam">
                        {fmtInt(s.kendaraan?.smp_ekivalen)}
                      </span>
                      <span className="mt-0.5 block text-micro text-ink-muted">
                        {fmtInt(s.volume_veh_per_hour)} kend/jam
                      </span>
                    </Td>
                    <Td align="right">
                      <span className="num text-ink">{fmtNum(s.vc_ratio, 2)}</span>
                    </Td>
                    <Td>
                      <LosBadge los={s.los} />
                    </Td>
                    <Td className="min-w-[220px]">
                      <VehicleMixBar
                        total={s.kendaraan?.total}
                        mix={{
                          roda_2: s.kendaraan?.roda_2 ?? 0,
                          roda_3: s.kendaraan?.roda_3 ?? 0,
                          roda_4: s.kendaraan?.roda_4 ?? 0,
                          roda_6plus: s.kendaraan?.roda_6plus ?? 0,
                        }}
                      />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>

          <div className="flex flex-wrap items-center gap-2 text-micro text-ink-muted">
            <span>
              <span className="num">{fmtInt(rows.length)}</span> dari{" "}
              <span className="num">{fmtInt(items.length)}</span> ruas tampil
            </span>
            {summary?.los_distribution &&
              Object.entries(summary.los_distribution).map(([grade, count]) => (
                <span key={grade} className="num">
                  LOS {grade} {fmtInt(count)}
                </span>
              ))}
          </div>

          {rows.length === 0 && (
            <StateBlock
              state="empty"
              height={140}
              emptyText="Tidak ada ruas pada filter ini"
              hint="Ubah tipe, LOS, atau kata kunci"
            />
          )}
        </div>
      )}
    </Card>
  );
};
