import { Session } from "@/lib/types";

export function TestProgress({ s }: { s: Session }) {
  const pct = s.total_pairs === 0 ? 0 : Math.round((s.done_pairs / s.total_pairs) * 100);
  return (
    <div>
      <p>Status: <strong>{s.status}</strong></p>
      <div style={{ background: "#eee", height: 16, borderRadius: 4 }}>
        <div
          style={{
            background: "#3498db",
            height: "100%",
            width: `${pct}%`,
            borderRadius: 4,
          }}
        />
      </div>
      <p>
        {s.done_pairs} / {s.total_pairs} (ok: {s.ok_pairs}, fail: {s.fail_pairs})
      </p>
    </div>
  );
}
