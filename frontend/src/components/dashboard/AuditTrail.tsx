import { Card, PanelHead, SeedBadge, StateBlock } from "../ui";
import { Icon } from "../ui/icons";

export interface AuditEntry {
  id: string;
  /** jam WIB saat entri dicatat */
  time: string;
  action: string;
  operator: string;
  detail: string;
}

/* Jejak audit intervensi operator: waktu + aksi + operator. */
export const AuditTrail = ({ entries }: { entries: AuditEntry[] }) => (
  <Card pad={false}>
    <PanelHead
      icon="undo"
      title="Jejak audit"
      sub={`${entries.length} entri sesi ini`}
      right={<SeedBadge />}
    />

    {entries.length === 0 ? (
      <div className="p-3">
        <StateBlock
          state="empty"
          height={140}
          emptyText="Belum ada intervensi"
          hint="Setujui rekomendasi fase untuk mencatat entri"
        />
      </div>
    ) : (
      <ol className="divide-y divide-line">
        {entries.map((e) => (
          <li key={e.id} className="flex items-start gap-2.5 px-4 py-3">
            <Icon name="clock" size={14} className="mt-0.5 text-ink-muted" />
            <div className="min-w-0">
              <p className="num text-micro text-ink-soft">{e.time}</p>
              <p className="text-micro text-ink">{e.action}</p>
              <p className="mt-0.5 text-micro text-ink-muted">
                {e.operator} · {e.detail}
              </p>
            </div>
          </li>
        ))}
      </ol>
    )}
  </Card>
);
