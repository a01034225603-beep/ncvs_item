/**
 * BACS 장비 헬스 상태 배지 컴포넌트
 *
 * 역할:
 *   online/offline/unknown 상태를 색상 점(dot)과 텍스트로 표시한다.
 *   DeviceGrid 에서 각 장비 행의 상태 컬럼에 사용된다.
 */
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
