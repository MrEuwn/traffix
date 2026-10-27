import { useEffect, useRef, useState } from "react";
import { Btn } from "../ui";
import { Icon } from "../ui/icons";

/** Menu akun ringkas: inisial, peran, tombol keluar (target sentuh >=44px). */
export const UserMenu = ({
  initials,
  role,
  onLogout,
}: {
  initials: string;
  role: string;
  onLogout: () => void;
}) => {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={box}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex min-h-11 items-center gap-2 rounded-control border border-line px-2 hover:border-line-strong"
      >
        <span className="flex h-6 w-6 items-center justify-center rounded-full border border-line bg-raised text-micro font-semibold text-ink">
          {initials}
        </span>
        <span className="hidden text-micro text-ink-soft lg:inline">{role}</span>
        <Icon name="chevron-down" size={13} className="text-ink-muted" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-12 z-50 w-56 animate-fade-in rounded-card border border-line bg-raised p-2"
        >
          <div className="px-2 py-1.5">
            <div className="text-micro font-semibold text-ink">{role}</div>
            <div className="text-micro text-ink-muted">Sesi demo · data sintetis</div>
          </div>
          <div className="my-1 h-px bg-line" />
          <Btn
            variant="ghost"
            icon="logout"
            className="w-full justify-start border-transparent bg-transparent hover:border-line"
            onClick={onLogout}
          >
            Keluar
          </Btn>
        </div>
      )}
    </div>
  );
};
