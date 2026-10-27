/* Primitif UI bersama hasil rombak Stitch. Tanpa library baru, Tailwind + SVG inline.
   Aturan: 1 aksen interaksi, 2 warna teks per panel, semua state setinggi sama,
   target sentuh >=44px, fokus ring terlihat. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Icon } from "./icons";
import { VEHICLE_CLASSES, causeMeta, losMeta } from "../../lib/causes";

export const cn = (...parts: (string | false | null | undefined)[]) =>
  parts.filter(Boolean).join(" ");

/* ────────────────────────── kartu & panel ────────────────────────── */

export const Card = ({
  children,
  className = "",
  pad = true,
}: {
  children: ReactNode;
  className?: string;
  pad?: boolean;
}) => (
  <section
    className={cn(
      "rounded-card border border-line bg-surface",
      pad && "p-4",
      className,
    )}
  >
    {children}
  </section>
);

export const PanelHead = ({
  title,
  sub,
  right,
  icon,
}: {
  title: string;
  sub?: string;
  right?: ReactNode;
  icon?: string;
}) => (
  <header className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
    <div className="min-w-0">
      <h2 className="label-caps flex items-center gap-1.5 text-ink-soft">
        {icon && <Icon name={icon} size={13} />}
        {title}
      </h2>
      {sub && <p className="mt-0.5 truncate text-micro text-ink-muted">{sub}</p>}
    </div>
    {right}
  </header>
);

export type PanelState = "ready" | "loading" | "empty" | "error";

/** Loading / kosong / galat — tinggi wajib sama supaya tata letak tidak bergeser. */
export const StateBlock = ({
  state,
  height = 140,
  emptyText = "Belum ada data",
  hint,
  onRetry,
}: {
  state: PanelState;
  height?: number;
  emptyText?: string;
  hint?: string;
  onRetry?: () => void;
}) => {
  if (state === "ready") return null;
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-card border text-center",
        state === "error" ? "border-crit/40 bg-surface" : "border-line bg-surface",
      )}
      style={{ height }}
      role={state === "error" ? "alert" : "status"}
      aria-live="polite"
    >
      {state === "loading" && (
        <div className="w-2/3 space-y-2" aria-hidden="true">
          {[0.75, 1, 0.5].map((w, i) => (
            <div
              key={i}
              className="h-2 animate-skeleton rounded-bar bg-hover"
              style={{ width: `${w * 100}%` }}
            />
          ))}
        </div>
      )}
      {state === "loading" && <span className="text-micro text-ink-muted">Memuat telemetri…</span>}
      {state === "empty" && (
        <>
          <Icon name="inbox" size={22} className="text-ink-muted" />
          <span className="text-micro font-semibold text-ink">{emptyText}</span>
          <span className="text-micro text-ink-muted">{hint ?? "Tidak ada insiden tercatat"}</span>
        </>
      )}
      {state === "error" && (
        <>
          <Icon name="alert-triangle" size={22} className="text-crit" />
          <span className="text-micro font-semibold text-ink">Gagal memuat data</span>
          {hint && <span className="text-micro text-ink-muted">{hint}</span>}
          <Btn variant="ghost" icon="refresh" onClick={onRetry}>
            Coba lagi
          </Btn>
        </>
      )}
    </div>
  );
};

/* ────────────────────────── badge & status ────────────────────────── */

export const CauseBadge = ({
  cause,
  confidence,
  size = "md",
}: {
  cause: string;
  confidence?: number | null;
  size?: "sm" | "md";
}) => {
  const meta = causeMeta(cause);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium",
        size === "sm" ? "px-2 py-0.5 text-micro" : "px-2.5 py-1 text-micro",
      )}
      style={{ borderColor: `${meta.color}4D`, background: `${meta.color}1A`, color: meta.color }}
    >
      <Icon name={meta.icon} size={13} />
      <span>{meta.label}</span>
      {confidence != null && <Confidence value={confidence} />}
    </span>
  );
};

/** Persentase wajib berlabel "Keyakinan model" (butir 1 audit). */
export const Confidence = ({ value }: { value: number }) => (
  <span className="num text-micro text-ink-soft">
    · Keyakinan model{" "}
    {new Intl.NumberFormat("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(
      value * 100,
    )}{" "}
    %
  </span>
);

export const StatusPill = ({
  tone,
  label,
  icon,
}: {
  tone: "ok" | "info" | "warn" | "high" | "crit" | "idle";
  label: string;
  icon?: string;
}) => {
  const map: Record<string, string> = {
    ok: "text-ok border-ok/30 bg-ok/10",
    info: "text-info border-info/30 bg-info/10",
    warn: "text-warn border-warn/30 bg-warn/10",
    high: "text-high border-high/30 bg-high/10",
    crit: "text-crit border-crit/30 bg-crit/10",
    idle: "text-ink-muted border-line bg-raised",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-caps font-semibold uppercase",
        map[tone],
      )}
    >
      {icon ? <Icon name={icon} size={13} /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {label}
    </span>
  );
};

export const LosBadge = ({ los }: { los: string }) => {
  const meta = losMeta(los);
  return (
    <span
      className="inline-flex items-center gap-1 rounded-control border px-1.5 py-0.5 text-caps font-semibold"
      style={{ borderColor: `${meta.color}4D`, background: `${meta.color}1A`, color: meta.color }}
      title={`LOS ${los} · ${meta.label}`}
    >
      <span className="num">{los}</span>
      <span className="font-normal normal-case tracking-normal">· {meta.label}</span>
    </span>
  );
};

export const SeedBadge = () => (
  <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-raised px-2 py-0.5 text-micro text-ink-muted">
    <Icon name="info" size={12} />
    data sintetis · seed 42
  </span>
);

/* ────────────────────────── tombol & kontrol ────────────────────────── */

export const Btn = ({
  children,
  variant = "primary",
  icon,
  className = "",
  ...rest
}: {
  children?: ReactNode;
  variant?: "primary" | "ghost" | "danger";
  icon?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) => {
  const styles: Record<string, string> = {
    primary: "bg-primary text-white border border-primary hover:bg-primary-hover",
    ghost: "bg-raised text-ink border border-line hover:border-line-strong",
    danger: "bg-transparent text-crit border border-crit/60 hover:border-crit",
  };
  return (
    <button
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-1.5 rounded-control px-3 text-micro font-semibold transition-colors duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-45",
        styles[variant],
        className,
      )}
      {...rest}
    >
      {icon && <Icon name={icon} size={14} />}
      {children}
    </button>
  );
};

export const Chip = ({
  active,
  dot,
  icon,
  label,
  count,
  onClick,
}: {
  active?: boolean;
  dot?: string;
  icon?: string;
  label: string;
  count?: number;
  onClick?: () => void;
}) => (
  <button
    type="button"
    onClick={onClick}
    aria-pressed={active}
    className={cn(
      "inline-flex min-h-11 items-center gap-1.5 rounded-full border px-2.5 text-micro transition-colors duration-150",
      active
        ? "border-primary bg-primary-quiet text-ink"
        : "border-line bg-surface text-ink-soft hover:border-line-strong",
    )}
  >
    {icon && <Icon name={icon} size={13} />}
    {dot && <span className="h-2 w-2 rounded-full" style={{ background: dot }} aria-hidden="true" />}
    {label}
    {count != null && <span className="num text-ink-muted">({count})</span>}
  </button>
);

export const Segmented = <T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label?: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) => (
  <div className="flex items-center gap-2">
    {label && <span className="label-caps">{label}</span>}
    <div className="inline-flex rounded-control border border-line bg-surface p-0.5" role="group">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={cn(
            "min-h-11 rounded-[4px] px-2.5 text-micro transition-colors duration-150",
            value === o.value ? "bg-primary-quiet text-ink" : "text-ink-muted hover:text-ink-soft",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  </div>
);

export const Field = ({
  label,
  hint,
  error,
  className = "",
  ...rest
}: { label: string; hint?: string; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) => (
  <label className="block">
    <span className="label-caps mb-1.5 block">{label}</span>
    <input
      className={cn(
        "h-11 w-full rounded-control border bg-surface px-3 text-body text-ink outline-none transition-colors",
        error ? "border-crit" : "border-line focus:border-primary",
        className,
      )}
      aria-invalid={!!error}
      {...rest}
    />
    {error ? (
      <span className="mt-1 flex items-center gap-1.5 text-micro text-crit">
        <Icon name="alert-triangle" size={13} />
        {error}
      </span>
    ) : (
      hint && <span className="mt-1 block text-micro text-ink-muted">{hint}</span>
    )}
  </label>
);

/* ────────────────────────── grafik kecil ────────────────────────── */

export const Sparkline = ({
  data,
  tone = "var(--c-primary)",
  height = 24,
  width = 72,
}: {
  data: number[];
  tone?: string;
  height?: number;
  width?: number;
}) => {
  const path = useMemo(() => {
    if (data.length < 2) return "";
    const min = Math.min(...data);
    const max = Math.max(...data);
    const span = max - min || 1;
    return data
      .map((v, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((v - min) / span) * (height - 2) - 1;
        return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");
  }, [data, height, width]);
  if (!path) return <div className="h-6" />;
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path d={path} fill="none" stroke={tone} strokeWidth="1.5" />
    </svg>
  );
};

export const KpiCard = ({
  label,
  value,
  unit,
  context,
  tone = "idle",
  series,
}: {
  label: string;
  value: string | number;
  unit?: string;
  context?: string;
  tone?: "idle" | "ok" | "warn" | "crit";
  series?: number[];
}) => {
  const toneText: Record<string, string> = {
    idle: "text-ink",
    ok: "text-ok",
    warn: "text-warn",
    crit: "text-crit",
  };
  return (
    <Card className="flex flex-col justify-between gap-2">
      <div className="flex items-start justify-between gap-2">
        <span className="label-caps">{label}</span>
        <span className={cn("h-2 w-2 rounded-full", tone === "idle" ? "bg-ink-muted" : "bg-current", toneText[tone])} />
      </div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className={cn("num text-metric font-semibold", toneText[tone])}>
            {value}
            {unit && <span className="ml-1 text-micro font-normal text-ink-muted">{unit}</span>}
          </div>
          {context && <div className="mt-0.5 text-micro text-ink-muted">{context}</div>}
        </div>
        {series && <Sparkline data={series} tone={`rgb(${tone === "idle" ? "--c-primary" : `--c-${tone}`})`} />}
      </div>
    </Card>
  );
};

/** 9 segmen probabilitas; hanya tiga teratas diberi label (aturan design system). */
export const ProbabilityBar = ({ probabilities }: { probabilities: Record<string, number> }) => {
  const top3 = Object.entries(probabilities)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  return (
    <div className="space-y-1.5">
      <div className="flex h-2 overflow-hidden rounded-bar bg-raised" role="img" aria-label="Sebaran probabilitas penyebab">
        {Object.entries(probabilities).map(([cause, p]) => (
          <span
            key={cause}
            style={{ width: `${Math.max(p * 100, 0.5)}%`, background: causeMeta(cause).color }}
            title={`${causeMeta(cause).label} ${(p * 100).toFixed(1)} %`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {top3.map(([cause, p]) => (
          <span key={cause} className="flex items-center gap-1.5 text-micro text-ink-muted">
            <Icon name={causeMeta(cause).icon} size={12} style={{ color: causeMeta(cause).color }} />
            {causeMeta(cause).label}
            <span className="num text-ink-soft">{(p * 100).toFixed(1)} %</span>
          </span>
        ))}
      </div>
    </div>
  );
};

export const VehicleMixBar = ({
  mix,
  total,
}: {
  mix: Record<string, number>;
  total?: number;
}) => {
  const sum = total ?? (VEHICLE_CLASSES.reduce((acc, c) => acc + (mix[c.key] ?? 0), 0) || 1);
  return (
    <div className="space-y-2">
      <div className="flex h-5 overflow-hidden rounded-bar border border-line">
        {VEHICLE_CLASSES.map((c) => {
          const n = mix[c.key] ?? 0;
          if (!n) return null;
          return (
            <span
              key={c.key}
              className={c.pattern}
              style={{ width: `${(n / sum) * 100}%` }}
              title={`${c.label} · ${c.desc}: ${n}`}
            />
          );
        })}
      </div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-1">
        {VEHICLE_CLASSES.map((c) => (
          <li key={c.key} className="flex items-center gap-1.5 text-micro text-ink-muted">
            <span className={cn("h-3 w-3 rounded-bar border border-line", c.pattern)} aria-hidden="true" />
            <span className="text-ink-soft">{c.label}</span>
            <span className="num text-ink">{new Intl.NumberFormat("id-ID").format(mix[c.key] ?? 0)}</span>
            <span>kend</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

/** Heat strip 24 jam + penanda "Sekarang" + scrub (butir 9 audit). */
export const HeatStrip = ({
  rows,
  playhead,
  onScrub,
}: {
  rows: { label: string; cells: (string | null)[] }[];
  playhead: number;
  onScrub?: (index: number) => void;
}) => {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div className="space-y-1.5">
      <div className="relative" ref={ref}>
        <div
          className="pointer-events-none absolute -top-1 bottom-5 z-10 w-px bg-primary"
          style={{ left: `${playhead}%` }}
        >
          <span className="num absolute -top-4 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-bar bg-primary px-1.5 py-0.5 text-micro font-semibold text-white">
            Sekarang {String(Math.round((playhead / 100) * 24)).padStart(2, "0")}:21 WIB
          </span>
        </div>
        <div className="space-y-1">
          {rows.map((row) => (
            <div key={row.label} className="flex items-center gap-2">
              <span className="w-20 shrink-0 truncate text-micro text-ink-muted">{row.label}</span>
              <div className="flex h-4 flex-1 gap-px">
                {row.cells.map((cause, i) => (
                  <span
                    key={i}
                    className="flex-1 rounded-[2px]"
                    style={{
                      background: cause ? causeMeta(cause).color : "rgb(var(--c-raised))",
                      opacity: cause ? 0.85 : 0.5,
                    }}
                    title={cause ? `${String(i).padStart(2, "0")}:00 · ${causeMeta(cause).label}` : `${String(i).padStart(2, "0")}:00`}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={playhead}
        onChange={(e) => onScrub?.(Number(e.target.value))}
        aria-label="Geser riwayat 24 jam"
        aria-valuetext={`${String(Math.round((playhead / 100) * 24)).padStart(2, "0")}:21 WIB`}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-raised accent-[rgb(var(--c-primary))]"
      />
    </div>
  );
};

/* ────────────────────────── tabel ────────────────────────── */

export const TableWrap = ({ children }: { children: ReactNode }) => (
  <div className="overflow-x-auto rounded-card border border-line">{children}</div>
);

export const Th = ({
  children,
  align = "left",
  className = "",
}: {
  children?: ReactNode;
  align?: "left" | "right";
  className?: string;
}) => (
  <th
    scope="col"
    className={cn(
      "label-caps sticky top-0 z-[1] whitespace-nowrap border-b border-line bg-raised px-3 py-2",
      align === "right" ? "text-right" : "text-left",
      className,
    )}
  >
    {children}
  </th>
);

export const Td = ({
  children,
  align = "left",
  className = "",
}: {
  children?: ReactNode;
  align?: "left" | "right";
  className?: string;
}) => (
  <td
    className={cn(
      "border-b border-line/60 px-3 py-2 text-cell text-ink-soft",
      align === "right" ? "text-right" : "text-left",
      className,
    )}
  >
    {children}
  </td>
);

/* ────────────────────────── modal & toast ────────────────────────── */

export const Modal = ({
  open,
  title,
  sub,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  sub?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) => {
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && box.current) {
        const nodes = box.current.querySelectorAll<HTMLElement>(
          'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])',
        );
        if (!nodes.length) return;
        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    box.current?.querySelector<HTMLElement>("button,input,select,textarea")?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-base/80 p-4">
      <div
        ref={box}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-2xl animate-fade-in rounded-shell border border-line bg-surface"
      >
        <header className="flex items-start justify-between gap-3 border-b border-line px-4 py-3">
          <div>
            <h3 className="text-title-sm font-semibold text-ink">{title}</h3>
            {sub && <p className="text-micro text-ink-muted">{sub}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="inline-flex h-11 w-11 items-center justify-center rounded-control border border-line text-ink-muted hover:border-line-strong hover:text-ink"
          >
            <Icon name="close" size={16} />
          </button>
        </header>
        <div className="max-h-[60vh] overflow-auto px-4 py-3">{children}</div>
        {footer && (
          <footer className="flex items-center justify-end gap-2 border-t border-line px-4 py-3">{footer}</footer>
        )}
      </div>
    </div>
  );
};

interface Toast {
  id: number;
  message: string;
  action?: { label: string; run: () => void };
}

const ToastCtx = createContext<{ push: (t: Omit<Toast, "id">) => void }>({ push: () => {} });
export const useToast = () => useContext(ToastCtx);

export const ToastProvider = ({ children }: { children: ReactNode }) => {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { ...t, id }]);
    window.setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== id)), 8000);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 left-1/2 z-[60] flex -translate-x-1/2 flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            role="status"
            aria-live="polite"
            className="pointer-events-auto flex animate-fade-in items-center gap-3 rounded-card border border-line bg-raised px-3 py-2 text-micro text-ink"
          >
            <Icon name="check-circle" size={14} className="text-ok" />
            <span>{t.message}</span>
            {t.action && (
              <button
                type="button"
                className="inline-flex min-h-11 items-center gap-1 rounded-control border border-line px-2 font-semibold text-ink hover:border-line-strong"
                onClick={() => {
                  t.action?.run();
                  setItems((prev) => prev.filter((i) => i.id !== t.id));
                }}
              >
                <Icon name="undo" size={13} />
                {t.action.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
};
