import { useBottlenecks } from "../../hooks/useTraffixData";
import { Card, CauseBadge, PanelHead, SeedBadge } from "../ui";
import { Icon } from "../ui/icons";
import { causeMeta } from "../../lib/causes";
import { fmtInt, fmtNum } from "../../lib/format";
import { PanelState } from "./Panel";

/** Agregat jaringan: sebaran 9 kelas penyebab pada 30 ruas + diagnosis per simpang. */
export const BottleneckPanel = () => {
  const { data, isLoading, isError } = useBottlenecks();

  const causes = [...(data?.causes ?? [])].sort((a, b) => (b.share ?? 0) - (a.share ?? 0));
  const worstShare = causes[0]?.share ?? 1;

  return (
    <Card pad={false}>
      <PanelHead
        icon="layers"
        title="Penyebab bottleneck jaringan"
        sub={
          data
            ? `tick ${fmtInt(data.tick)} · ${fmtInt(data.affected_section_count)} dari ${fmtInt(
                data.section_count,
              )} ruas terdampak`
            : "klasifikasi 9 kelas penyebab"
        }
        right={<SeedBadge />}
      />

      {isLoading || isError || !data ? (
        <PanelState
          kind={isLoading ? "loading" : "error"}
          message="Endpoint /api/v1/bottlenecks tidak merespons."
        />
      ) : (
        <div className="space-y-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="label-caps">Penyebab dominan jaringan</span>
            <CauseBadge cause={data.dominant_cause} />
            <span className="text-micro text-ink-muted">
              {fmtInt(causes.length)} kelas dihitung · {fmtInt(data.section_count)} ruas
            </span>
          </div>

          <ul className="space-y-1.5">
            {causes.map((c) => {
              const meta = causeMeta(c.cause);
              return (
                <li key={c.cause} className="grid grid-cols-[10rem_minmax(0,1fr)_auto] items-center gap-2">
                  <span className="flex items-center gap-1.5 text-micro text-ink-soft">
                    <Icon name={meta.icon} size={12} style={{ color: meta.color }} />
                    {meta.label}
                  </span>
                  <span className="h-1.5 overflow-hidden rounded-bar bg-raised">
                    <span
                      className="block h-full rounded-bar"
                      style={{
                        width: `${((c.share ?? 0) / (worstShare || 1)) * 100}%`,
                        background: meta.color,
                      }}
                    />
                  </span>
                  <span className="num whitespace-nowrap text-micro text-ink-muted">
                    {fmtInt(c.sections)} ruas · {fmtNum((c.share ?? 0) * 100, 1)} % · V/C{" "}
                    {fmtNum(c.avg_vc_ratio, 2)} · {fmtNum(c.avg_queue_veh, 1)} kend ·{" "}
                    {fmtNum(c.avg_wait_time_min, 2)} menit
                  </span>
                </li>
              );
            })}
          </ul>

          <div className="space-y-2 border-t border-line pt-3">
            <p className="label-caps">Diagnosis per simpang</p>
            {(data.per_intersection ?? []).map((ix) => (
              <div
                key={ix.intersection_id}
                className="flex flex-wrap items-center gap-2 rounded-control border border-line bg-raised px-3 py-2"
              >
                <span className="min-w-0 text-cell text-ink">{ix.intersection_name}</span>
                <span className="text-micro text-ink-muted">
                  {ix.intersection_id} · {ix.tipe_persimpangan}
                </span>
                <CauseBadge
                  size="sm"
                  cause={ix.dominant_cause}
                  confidence={ix.model_available !== false && ix.confidence > 0 ? ix.confidence : undefined}
                />
                <span className="num ml-auto text-micro text-ink-muted">
                  {(ix.top3 ?? [])
                    .slice(0, 3)
                    .map((t) => `${causeMeta(t.cause).label} ${fmtNum(t.probability * 100, 1)} %`)
                    .join(" · ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};
