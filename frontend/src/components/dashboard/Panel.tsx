import type { ReactNode } from "react";

/* Kerangka panel bersama untuk kartu analitik v4. */

export const PanelState = ({
  kind,
  message,
}: {
  kind: "loading" | "error";
  message?: string;
}) => (
  <div
    style={{
      padding: "22px 16px",
      textAlign: "center",
      color: "var(--text-muted)",
      fontSize: 11,
      animation: kind === "loading" ? "pulse 1.5s infinite" : "none",
      lineHeight: 1.6,
    }}
  >
    <p style={{ fontSize: 18, marginBottom: 6 }}>{kind === "loading" ? "⏳" : "⚠️"}</p>
    {kind === "loading" ? "Memuat data…" : message ?? "Gagal memuat data — backend tidak merespons"}
  </div>
);

export const PanelHeader = ({
  icon,
  title,
  sub,
  right,
}: {
  icon: string;
  title: string;
  sub?: string;
  right?: ReactNode;
}) => (
  <div
    style={{
      padding: "11px 14px",
      borderBottom: "1px solid var(--border)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 10,
    }}
  >
    <span style={{ display: "flex", alignItems: "center", gap: 7, minWidth: 0 }}>
      <span style={{ fontSize: 13 }}>{icon}</span>
      <span style={{ minWidth: 0 }}>
        <span
          style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}
        >
          {title}
        </span>
        {sub && (
          <span style={{ display: "block", fontSize: 10, color: "var(--text-dim)" }}>{sub}</span>
        )}
      </span>
    </span>
    {right}
  </div>
);
