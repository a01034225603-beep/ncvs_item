"use client";
import { useMemo, useRef, useState } from "react";
import { Device, MatrixCell } from "@/lib/types";

type Props = { devices: Device[]; cells: MatrixCell[] };

const CELL_SIZES = [5, 8, 12, 16, 22, 28] as const;
type ZoomIdx = 0 | 1 | 2 | 3 | 4 | 5;

function autoZoom(n: number): ZoomIdx {
  if (n > 128) return 0;
  if (n > 64)  return 1;
  if (n > 32)  return 2;
  if (n > 20)  return 3;
  if (n > 10)  return 4;
  return 5;
}

function abbr(name: string, maxLen: number): string {
  return name.length <= maxLen ? name : name.slice(0, maxLen - 1) + "…";
}

type Tip = {
  x: number; y: number;
  src: string; dst: string;
  status: "ok" | "fail" | "no data";
  tested_at?: string;
  error?: string | null;
};

export function Matrix({ devices, cells }: Props) {
  const [zoomIdx, setZoomIdx] = useState<ZoomIdx>(() => autoZoom(devices.length));
  const [failOnly, setFailOnly] = useState(false);
  const [tip, setTip] = useState<Tip | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const cellPx   = CELL_SIZES[zoomIdx];
  const showLabels   = cellPx >= 14;
  const labelW       = showLabels ? Math.min(96, Math.max(52, cellPx * 4)) : 0;
  const labelMaxChars = Math.max(4, Math.floor(labelW / 7));

  const lookup = useMemo(() => {
    const m = new Map<string, MatrixCell>();
    for (const c of cells) m.set(`${c.src_bacs_id}:${c.dst_bacs_id}`, c);
    return m;
  }, [cells]);

  const stats = useMemo(() => {
    let ok = 0, fail = 0, untested = 0;
    for (const src of devices) {
      for (const dst of devices) {
        if (src.id === dst.id) continue;
        const c = lookup.get(`${src.id}:${dst.id}`);
        if (!c) untested++;
        else if (c.status === "ok") ok++;
        else fail++;
      }
    }
    return { ok, fail, untested };
  }, [devices, lookup]);

  function getCellBg(cell: MatrixCell | undefined): string {
    if (!cell) return failOnly ? "transparent" : "var(--color-edge)";
    if (cell.status === "ok") return failOnly ? "rgba(44,201,128,0.1)" : "var(--color-ok)";
    return "var(--color-fail)";
  }

  function showTip(e: React.MouseEvent, src: Device, dst: Device, cell: MatrixCell | undefined) {
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    const wrap = wrapRef.current?.getBoundingClientRect();
    if (!wrap) return;
    setTip({
      x: rect.left - wrap.left + rect.width / 2,
      y: rect.top  - wrap.top,
      src: src.name, dst: dst.name,
      status: cell ? (cell.status as "ok" | "fail") : "no data",
      tested_at: cell?.tested_at,
      error: cell?.error_message,
    });
  }

  const STATUS_KO: Record<string, string> = { ok: "정상", fail: "실패", "no data": "미테스트" };
  const GAP = 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      {/* ── 컨트롤 ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        {/* 통계 */}
        <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
          {[
            { label: "정상",   value: stats.ok,       color: "var(--color-ok)" },
            { label: "실패",   value: stats.fail,     color: "var(--color-fail)" },
            { label: "미테스트", value: stats.untested, color: "var(--color-fog)" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 18,
                  fontWeight: 700,
                  color,
                  lineHeight: 1,
                }}
              >
                {value}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  letterSpacing: "0.06em",
                  color: "var(--color-fog)",
                }}
              >
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* 컨트롤 */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* 실패만 */}
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              cursor: "pointer",
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              letterSpacing: "0.06em",
              color: failOnly ? "var(--color-fail)" : "var(--color-fog)",
              userSelect: "none",
            }}
            onClick={() => setFailOnly((v) => !v)}
          >
            <span
              style={{
                width: 12, height: 12,
                border: `1px solid ${failOnly ? "var(--color-fail)" : "var(--color-wire)"}`,
                background: failOnly ? "rgba(229,72,77,0.18)" : "transparent",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 8,
                color: "var(--color-fail)",
                flexShrink: 0,
              }}
            >
              {failOnly && "✓"}
            </span>
            실패만 표시
          </label>

          {/* 줌 */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              border: "1px solid var(--color-edge)",
            }}
          >
            <button
              onClick={() => setZoomIdx((z) => Math.max(z - 1, 0) as ZoomIdx)}
              disabled={zoomIdx === 0}
              style={{
                width: 28, height: 28,
                background: "none", border: "none",
                borderRight: "1px solid var(--color-edge)",
                fontFamily: "var(--font-mono)", fontSize: 16, lineHeight: 1,
                color: zoomIdx === 0 ? "var(--color-edge)" : "var(--color-haze)",
                cursor: zoomIdx === 0 ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              −
            </button>
            <span
              style={{
                padding: "0 10px",
                fontFamily: "var(--font-mono)", fontSize: 10,
                letterSpacing: "0.04em", color: "var(--color-fog)",
                userSelect: "none", minWidth: 44, textAlign: "center",
              }}
            >
              {cellPx}px
            </span>
            <button
              onClick={() => setZoomIdx((z) => Math.min(z + 1, 5) as ZoomIdx)}
              disabled={zoomIdx === 5}
              style={{
                width: 28, height: 28,
                background: "none", border: "none",
                borderLeft: "1px solid var(--color-edge)",
                fontFamily: "var(--font-mono)", fontSize: 16, lineHeight: 1,
                color: zoomIdx === 5 ? "var(--color-edge)" : "var(--color-haze)",
                cursor: zoomIdx === 5 ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* 장비 수 경고 */}
      {devices.length > 64 && (
        <div
          style={{
            borderLeft: "2px solid var(--color-warn)",
            paddingLeft: 10,
            fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.04em",
            color: "var(--color-warn)", lineHeight: 1.6,
          }}
        >
          {devices.length}개 장비 · {devices.length * (devices.length - 1)}개 페어.
          가독성을 위해 사이드바에서 장비를 좁혀보세요.
        </div>
      )}

      {/* ── 매트릭스 그리드 ── */}
      <div
        ref={wrapRef}
        style={{ position: "relative", overflowX: "auto", overflowY: "auto", maxHeight: "68vh" }}
        onMouseLeave={() => setTip(null)}
      >
        <div style={{ display: "inline-block" }}>

          {/* 열 헤더 */}
          {showLabels && (
            <div style={{ display: "flex", paddingLeft: labelW + GAP, marginBottom: GAP }}>
              {devices.map((d) => (
                <div
                  key={d.id}
                  title={`${d.name} (${d.ip_address})`}
                  style={{
                    width: cellPx, marginRight: GAP, flexShrink: 0,
                    writingMode: "vertical-rl", transform: "rotate(180deg)",
                    fontFamily: "var(--font-mono)", fontSize: Math.min(10, cellPx - 3),
                    color: "var(--color-fog)", overflow: "hidden",
                    whiteSpace: "nowrap", textOverflow: "clip",
                    maxHeight: 72, cursor: "default",
                  }}
                >
                  {abbr(d.name, labelMaxChars)}
                </div>
              ))}
            </div>
          )}

          {/* 행 */}
          {devices.map((src) => (
            <div key={src.id} style={{ display: "flex", alignItems: "center", marginBottom: GAP }}>
              {showLabels && (
                <div
                  title={`${src.name} (${src.ip_address})`}
                  style={{
                    width: labelW, paddingRight: 6, marginRight: GAP,
                    fontFamily: "var(--font-mono)", fontSize: Math.min(11, cellPx - 1),
                    color: "var(--color-fog)", textAlign: "right", flexShrink: 0,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    cursor: "default",
                  }}
                >
                  {abbr(src.name, labelMaxChars)}
                </div>
              )}

              {devices.map((dst) => {
                if (src.id === dst.id) {
                  return (
                    <div
                      key={dst.id}
                      style={{
                        width: cellPx, height: cellPx, marginRight: GAP,
                        background: "var(--color-bg2)",
                        border: "1px solid var(--color-edge)",
                        flexShrink: 0,
                      }}
                    />
                  );
                }

                const cell    = lookup.get(`${src.id}:${dst.id}`);
                const isFail  = cell?.status === "fail";
                const dimmed  = failOnly && !isFail;

                return (
                  <div
                    key={dst.id}
                    style={{
                      width: cellPx, height: cellPx, marginRight: GAP,
                      background: getCellBg(cell),
                      flexShrink: 0, cursor: "crosshair",
                      opacity: dimmed ? 0.1 : 1,
                      transition: "opacity 0.15s",
                    }}
                    onMouseEnter={(e) => showTip(e, src, dst, cell)}
                    onMouseLeave={() => setTip(null)}
                  />
                );
              })}
            </div>
          ))}
        </div>

        {/* 툴팁 */}
        {tip && (
          <div
            style={{
              position: "absolute",
              left: tip.x, top: tip.y - 6,
              transform: "translate(-50%, -100%)",
              background: "var(--color-panel2)",
              border: "1px solid var(--color-wire)",
              padding: "10px 14px",
              fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.03em",
              color: "var(--color-snow)",
              pointerEvents: "none", zIndex: 200,
              whiteSpace: "nowrap",
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
              minWidth: 160,
            }}
          >
            <div style={{ color: "var(--color-haze)", marginBottom: 6, fontSize: 12 }}>
              <span style={{ color: "var(--color-snow)" }}>{tip.src}</span>
              <span style={{ color: "var(--color-fog)", margin: "0 6px" }}>→</span>
              <span style={{ color: "var(--color-snow)" }}>{tip.dst}</span>
            </div>

            <div
              style={{
                color: tip.status === "ok" ? "var(--color-ok)"
                     : tip.status === "fail" ? "var(--color-fail)"
                     : "var(--color-fog)",
                fontWeight: 600,
              }}
            >
              {STATUS_KO[tip.status] ?? tip.status}
            </div>

            {tip.tested_at && (
              <div style={{ color: "var(--color-fog)", fontSize: 10, marginTop: 5 }}>
                {new Date(tip.tested_at).toLocaleString("ko-KR", {
                  hour12: false, month: "2-digit", day: "2-digit",
                  hour: "2-digit", minute: "2-digit",
                })}
              </div>
            )}

            {tip.error && (
              <div
                style={{
                  color: "var(--color-warn)", fontSize: 10, marginTop: 5,
                  maxWidth: 220, whiteSpace: "normal", lineHeight: 1.5,
                }}
              >
                {tip.error}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 범례 */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        {[
          { color: "var(--color-ok)",   label: "정상" },
          { color: "var(--color-fail)", label: "실패" },
          { color: "var(--color-edge)", label: "미테스트" },
          { color: "var(--color-bg2)",  label: "자기 자신", border: "1px solid var(--color-edge)" },
        ].map(({ color, label, border }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <span
              style={{
                width: 10, height: 10,
                background: color,
                display: "inline-block",
                border: border ?? "none",
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontFamily: "var(--font-mono)", fontSize: 10,
                letterSpacing: "0.06em", color: "var(--color-fog)",
              }}
            >
              {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
