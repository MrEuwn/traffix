import { useEffect, useState } from "react";
import { useSystemStatus } from "../../hooks/useTraffixData";
import { useAuth } from "../../lib/AuthContext";
import { useTheme } from "../../lib/ThemeContext";
import { Btn, Segmented, SeedBadge, StatusPill } from "../ui";
import { Icon } from "../ui/icons";
import { UserMenu } from "./UserMenu";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: "gauge" },
  { id: "map", label: "Live Map", icon: "map" },
  { id: "model", label: "Evaluasi Model", icon: "chart" },
  { id: "settings", label: "Settings", icon: "sliders" },
];

/** Bilah atas 56px: merek, tab modul, status live, jam WIB, tema, akun. */
export const Topbar = ({
  page,
  onNavigate,
}: {
  page: string;
  onNavigate: (p: string) => void;
}) => {
  const { data: status } = useSystemStatus();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const [clock, setClock] = useState(() => new Date());

  useEffect(() => {
    const id = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const wib = new Intl.DateTimeFormat("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "Asia/Jakarta",
  }).format(clock);

  const live = !!status?.simulation_active;

  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-4 border-b border-line bg-surface px-4">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-control border border-line bg-primary-quiet text-primary">
          <Icon name="activity" size={16} />
        </span>
        <span className="text-title-sm font-semibold tracking-tight text-ink">
          Traffix
        </span>
      </div>

      <nav className="flex h-14 items-stretch overflow-x-auto" aria-label="Modul">
        {TABS.map((t) => {
          const active = page === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onNavigate(t.id)}
              aria-current={active ? "page" : undefined}
              className={
                "flex min-h-11 items-center gap-1.5 whitespace-nowrap border-b-2 px-3 text-micro font-medium transition-colors duration-150 " +
                (active
                  ? "border-primary bg-primary-quiet text-ink"
                  : "border-transparent text-ink-muted hover:text-ink-soft")
              }
            >
              <Icon name={t.icon} size={14} />
              {t.label}
            </button>
          );
        })}
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <span className="hidden lg:inline-flex">
          <StatusPill
            tone={live ? "ok" : "idle"}
            label={live ? "Operasional" : "Idle"}
            icon={live ? "check-circle" : "pause"}
          />
        </span>
        <span className="num hidden text-micro text-ink-soft md:inline" title="Waktu WIB">
          {wib} WIB
        </span>
        <span className="hidden xl:inline">
          <SeedBadge />
        </span>
        <Segmented
          options={[
            { value: "dark", label: "Gelap" },
            { value: "light", label: "Terang" },
          ]}
          value={theme}
          onChange={(v) => {
            if (v !== theme) toggleTheme();
          }}
        />
        <UserMenu initials={user?.avatar ?? "AT"} role={user?.role ?? "Operator"} onLogout={logout} />
      </div>
    </header>
  );
};

export const TopbarFallbackBtn = Btn;
