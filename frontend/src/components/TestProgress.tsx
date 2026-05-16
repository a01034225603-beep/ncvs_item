import { Session } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-slate-100 text-slate-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-emerald-100 text-emerald-700",
  cancelled: "bg-amber-100 text-amber-700",
  failed: "bg-red-100 text-red-700",
};

export function TestProgress({ s }: { s: Session }) {
  const pct = s.total_pairs === 0 ? 0 : Math.round((s.done_pairs / s.total_pairs) * 100);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">Status</span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[s.status] ?? "bg-slate-100 text-slate-700"}`}
        >
          {s.status}
        </span>
      </div>
      <div className="mt-4 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-blue-500 transition-[width] duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-slate-600">
          {s.done_pairs} / {s.total_pairs} pairs
        </span>
        <span className="text-slate-500">
          <span className="text-emerald-600">ok {s.ok_pairs}</span>
          <span className="mx-2">·</span>
          <span className="text-red-600">fail {s.fail_pairs}</span>
        </span>
      </div>
    </div>
  );
}
