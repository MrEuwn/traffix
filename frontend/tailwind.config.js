/** Token warna/tipe konsol Traffix + layer "Editorial Control Room".
 *  Semua warna menunjuk CSS var (di-set ThemeProvider) supaya mode gelap/terang tetap jalan. */
const v = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        base: v("--c-base"),
        surface: v("--c-surface"),
        raised: v("--c-raised"),
        hover: v("--c-hover"),
        line: v("--c-line"),
        "line-strong": v("--c-line-strong"),
        ink: v("--c-ink"),
        "ink-soft": v("--c-ink-soft"),
        "ink-muted": v("--c-ink-muted"),
        primary: {
          DEFAULT: v("--c-primary"),
          hover: v("--c-primary-hover"),
          quiet: v("--c-primary-quiet"),
        },
        ok: v("--c-ok"),
        info: v("--c-info"),
        warn: v("--c-warn"),
        high: v("--c-high"),
        crit: v("--c-crit"),
      },
      fontFamily: {
        sans: ["Inter", "Inter Fallback", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Consolas", "monospace"],
      },
      /* Skala tipografi beku: dasar 11px, angka metrik 26px tabular. */
      fontSize: {
        caps: ["11px", { lineHeight: "16px", letterSpacing: "0.08em" }],
        micro: ["11px", { lineHeight: "16px" }],
        body: ["13px", { lineHeight: "20px" }],
        cell: ["12px", { lineHeight: "16px" }],
        label: ["10px", { lineHeight: "14px" }],
        "title-sm": ["15px", { lineHeight: "20px" }],
        "title-md": ["22px", { lineHeight: "28px", letterSpacing: "-0.01em" }],
        "title-lg": ["28px", { lineHeight: "34px", letterSpacing: "-0.015em" }],
        hero: ["64px", { lineHeight: "68px", letterSpacing: "-0.02em" }],
        metric: ["26px", { lineHeight: "30px", letterSpacing: "-0.01em" }],
      },
      borderRadius: { bar: "4px", control: "6px", card: "10px", shell: "14px" },
      spacing: { rail: "56px", dock: "360px" },
      maxWidth: { canvas: "1600px" },
      transitionTimingFunction: { out: "cubic-bezier(0, 0, 0.2, 1)" },
      keyframes: {
        "live-pulse": { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.25" } },
        "skeleton-pulse": { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.45" } },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "live-pulse": "live-pulse 2s ease-in-out infinite",
        skeleton: "skeleton-pulse 1.6s ease-in-out infinite",
        "fade-in": "fade-in 200ms cubic-bezier(0, 0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};
