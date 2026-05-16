import { HealthStatus } from "@/lib/types";

const COLOR: Record<HealthStatus, string> = {
  ok: "#2ecc71",
  fail: "#e74c3c",
  unknown: "#95a5a6",
};

export function HealthBadge({ status }: { status: HealthStatus }) {
  return (
    <span
      style={{
        background: COLOR[status],
        color: "white",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
      }}
    >
      {status}
    </span>
  );
}
