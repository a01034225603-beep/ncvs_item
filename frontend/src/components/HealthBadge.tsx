import { HealthStatus } from "@/lib/types";

const CFG: Record<HealthStatus, { dot: string; text: string; label: string }> = {
  online:  { dot: "var(--color-ok)",   text: "var(--color-ok)",   label: "ONLINE" },
  offline: { dot: "var(--color-fail)", text: "var(--color-fail)", label: "OFFLINE" },
  unknown: { dot: "var(--color-fog)",  text: "var(--color-fog)",  label: "UNKNOWN" },
};

export function HealthBadge({ status }: { status: HealthStatus }) {
  const cfg = CFG[status];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        letterSpacing: "0.08em",
        color: cfg.text,
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: cfg.dot,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      {cfg.label}
    </span>
  );
}
