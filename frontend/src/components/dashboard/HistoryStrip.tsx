import { useMemo, useState } from "react";
import { useBottlenecksByIntersection } from "../../hooks/useTraffixData";
import { Card, CauseBadge, HeatStrip, PanelHead, SeedBadge } from "../ui";
import { PanelState } from "./Panel";
import { fmtInt } from "../../lib/format";
import { wibHm } from "./format";
import type { BottleneckPerIntersection } from "../../types";

const BUCKETS = 24;

type Point = NonNullable<BottleneckPerIntersection["history"]>[number];

/* Riwayat penyebab per bucket + scrub. Jendela riwayat datang dari API
   (60 tick terakhir), dipetakan ke 24 bucket untuk heat strip. */
export const HistoryStrip = ({
  intersectionId,
  name,
}: {
  intersectionId: string;
  name: string;
}) => {
  const { data, isLoading, isError } = useBottlenecksByIntersection(intersectionId);
  const [playhead, setPlayhead] = useState(100);

  const { cells, buckets, range } = useMemo(() => {
    const history = data?.history ?? [];
    if (!history.length) return { cells: [] as (string | null)[], buckets: [] as Bucket[], range: "—" };

    const grouped: Point[][] = Array.from({ length: BUCKETS }, () => []);
    history.forEach((point, index) => {
      const slot = Math.min(BUCKETS - 1, Math.floor((index * BUCKETS) / history.length));
      grouped[slot].push(point);
    });

    const built: Bucket[] = grouped.map((group) => {
      if (!group.length) return null;
      const hottest = group.reduce((best, p) => (p.confidence > best.confidence ? p : best), group[0]);
      return {
        cause: hottest.dominant_cause,
        confidence: hottest.confidence,
        from: group[0].timestamp_wib,
        to: group[group.length - 1].timestamp_wib,
        ticks: group.length,
      };
    });

    return {
      cells: built.map((b) => b?.cause ?? null),
      buckets: built,
      range: `${wibHm(history[0].timestamp_wib)}–${wibHm(history[history.length - 1].timestamp_wib)} WIB`,
    };
  }, [data]);

  const index = Math.min(BUCKETS - 1, Math.round((playhead / 100) * (BUCKETS - 1)));
  const bucket = buckets[index] ?? null;

  return (
    <Card pad={false}>
      <PanelHead
        icon="clock"
        title="Riwayat penyebab 24 jam"
        sub={data ? `${name} · ${fmtInt((data.history ?? []).length)} tick replay · ${range}` : name}
        right={<SeedBadge />}
      />

      {isLoading || isError || !data ? (
        <PanelState
          kind={isLoading ? "loading" : "error"}
          message="Endpoint /api/v1/bottlenecks/{id} tidak merespons."
        />
      ) : (
        <div className="p-4">
          <HeatStrip rows={[{ label: name, cells }]} playhead={playhead} onScrub={setPlayhead} />

          <div className="mt-3 flex flex-wrap items-center gap-2 text-micro text-ink-muted">
            <span className="num">
              bucket {fmtInt(index + 1)}/{fmtInt(BUCKETS)}
            </span>
            {bucket ? (
              <>
                <span className="num">
                  {wibHm(bucket.from)}–{wibHm(bucket.to)} WIB · {fmtInt(bucket.ticks)} tick
                </span>
                <CauseBadge
                  size="sm"
                  cause={bucket.cause}
                  confidence={bucket.confidence > 0 ? bucket.confidence : undefined}
                />
              </>
            ) : (
              <span>Tidak ada tick pada bucket ini.</span>
            )}
          </div>

          <p className="mt-2 text-micro text-ink-muted">
            API riwayat hanya menyimpan tick replay terakhir, jadi 24 bucket di atas memetakan jendela
            yang tersedia — bukan 24 jam penuh.
          </p>
        </div>
      )}
    </Card>
  );
};

type Bucket = {
  cause: string;
  confidence: number;
  from: string | null;
  to: string | null;
  ticks: number;
} | null;
