import { HealthStatus } from "@/lib/types";

const STYLES: Record<HealthStatus, string> = {
  ok: "bg-emerald-100 text-emerald-700 ring-emerald-600/20",
  fail: "bg-red-100 text-red-700 ring-red-600/20",
  unknown: "bg-slate-100 text-slate-600 ring-slate-500/20",
};

export function HealthBadge({ status }: { status: HealthStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}
