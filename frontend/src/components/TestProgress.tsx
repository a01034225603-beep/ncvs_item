import { Session } from "@/lib/types";

const STATUS_CFG: Record<string, { color: string; bg: string; border: string }> = {
  queued:    { color: "var(--color-haze)",   bg: "rgba(150,163,187,0.08)", border: "var(--color-wire)" },
  running:   { color: "var(--color-accent)", bg: "rgba(93,155,148,0.1)",   border: "var(--color-accent)" },
  completed: { color: "var(--color-ok)",     bg: "rgba(44,201,128,0.08)",  border: "var(--color-ok)" },
  cancelled: { color: "var(--color-warn)",   bg: "rgba(217,119,6,0.08)",   border: "var(--color-warn)" },
  failed:    { color: "var(--color-fail)",   bg: "rgba(229,72,77,0.08)",   border: "var(--color-fail)" },
};

const STATUS_LABEL: Record<string, string> = {
  queued:    "대기 중",
  running:   "실행 중",
  completed: "완료",
  cancelled: "취소됨",
  failed:    "실패",
};

export function TestProgress({ s }: { s: Session }) {
  const pct = s.total_pairs === 0 ? 0 : Math.round((s.done_pairs / s.total_pairs) * 100);
  const isRunning = s.status === "running";
  const cfg = STATUS_CFG[s.status] ?? STATUS_CFG.queued;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* 상태 + 메타 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.06em",
            color: "var(--color-fog)",
          }}
        >
          {s.device_ids?.length ?? "?"}개 장비 ·{" "}
          {s.started_at
            ? new Date(s.started_at).toLocaleString("ko-KR", {
                hour12: false,
                month: "2-digit", day: "2-digit",
                hour: "2-digit", minute: "2-digit", second: "2-digit",
              })
            : "시작 전"}
        </div>

        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            padding: "5px 12px",
            fontFamily: "var(--font-mono)",
            fontSize: 11, fontWeight: 600,
            letterSpacing: "0.06em",
            color: cfg.color,
            background: cfg.bg,
            border: `1px solid ${cfg.border}`,
          }}
        >
          {isRunning && (
            <span
              style={{
                width: 5, height: 5,
                borderRadius: "50%",
                background: "var(--color-accent)",
                display: "inline-block",
                animation: "pulse 1.5s ease-in-out infinite",
              }}
            />
          )}
          {STATUS_LABEL[s.status] ?? s.status}
        </span>
      </div>

      {/* KPI 타일 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 1,
          background: "var(--color-edge)",
          border: "1px solid var(--color-edge)",
        }}
      >
        {[
          { label: "완료",  value: s.done_pairs,  color: "var(--color-snow)" },
          { label: "성공",  value: s.ok_pairs,    color: "var(--color-ok)" },
          { label: "실패",  value: s.fail_pairs,  color: s.fail_pairs > 0 ? "var(--color-fail)" : "var(--color-fog)" },
          { label: "전체",  value: s.total_pairs, color: "var(--color-haze)" },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            style={{
              background: "var(--color-bg2)",
              padding: "14px 18px",
              display: "flex",
              flexDirection: "column",
              gap: 5,
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 9,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--color-fog)",
              }}
            >
              {label}
            </span>
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 28, fontWeight: 700,
                color, lineHeight: 1,
              }}
            >
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* 진행률 바 */}
      <div>
        <div
          style={{
            position: "relative",
            height: 6,
            background: "var(--color-bg)",
            border: "1px solid var(--color-edge)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${pct}%`,
              background: isRunning
                ? "linear-gradient(90deg, var(--color-accent), var(--color-ok))"
                : pct === 100
                  ? "var(--color-ok)"
                  : "var(--color-haze)",
              position: "relative",
              transition: "width 0.6s ease",
              overflow: "hidden",
            }}
          >
            {isRunning && <div className="stripe-running" style={{ position: "absolute", inset: 0 }} />}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 5,
            fontFamily: "var(--font-mono)",
            fontSize: 10, letterSpacing: "0.04em",
            color: "var(--color-fog)",
          }}
        >
          <span>0</span>
          <span>{s.done_pairs} / {s.total_pairs} 페어 ({pct}%)</span>
          <span>{s.total_pairs}</span>
        </div>
      </div>
    </div>
  );
}
