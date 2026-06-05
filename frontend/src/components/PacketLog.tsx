"use client";
import { useEffect, useRef, useState } from "react";
import { PacketEvent } from "@/lib/types";

const DIR_CFG: Record<string, { label: string; bg: string; color: string }> = {
  TX: { label: "TX", bg: "rgba(93,155,148,0.18)", color: "var(--color-accent)" },
  RX: { label: "RX", bg: "rgba(44,201,128,0.14)", color: "var(--color-ok)" },
};

function stepColor(step: string): string {
  if (step.includes("ERROR")) return "var(--color-fail)";
  if (step.includes("STARTUP")) return "var(--color-ok)";
  if (step.includes("CALL_RPT")) return "var(--color-warn)";
  return "var(--color-snow)";
}

interface PairStatusResult {
  status: "ok" | "fail" | "running" | "none";
  failReason: string | null;
}

function pairStatus(events: PacketEvent[]): PairStatusResult {
  let lastCallRptFail: string | null = null;

  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    // ERROR_RPT (connect 단계 실패) 등장 시 즉시 FAIL
    if (ev.step.includes("ERROR_RPT")) {
      const errCode = ev.parsed.err_code !== undefined ? String(ev.parsed.err_code) : "";
      const errDesc = ev.parsed.err_code_desc ? String(ev.parsed.err_code_desc) : "";
      const detail = errDesc ? `${errCode} ${errDesc}`.trim() : (errCode || "unknown error");
      return { status: "fail", failReason: `CONNECT 실패 — ${detail}` };
    }
    // CALL_RPT 당 결과 확인
    if (ev.step.includes("CALL_RPT")) {
      const desc = String(ev.parsed.result_desc ?? "");
      const code = ev.parsed.result_code !== undefined ? ` (0x${Number(ev.parsed.result_code).toString(16).padStart(2,"0")})` : "";
      if (desc.startsWith("OK")) {
        lastCallRptFail = null;  // 성공
      } else if (desc) {
        lastCallRptFail = `${ev.step} 실패 — ${desc}${code}`;
      }
    }
  }

  // 모든 패킷을 어답 들어도 결정적 CALL_RPT가 없으면 이지지 판단 불가
  const lastCall = events.filter(e => e.step.includes("CALL_RPT")).pop();
  if (!lastCall) return { status: "none", failReason: null };

  const finalDesc = String(lastCall.parsed.result_desc ?? "");
  if (finalDesc.startsWith("OK")) return { status: "ok", failReason: null };
  const finalCode = lastCall.parsed.result_code !== undefined
    ? ` (0x${Number(lastCall.parsed.result_code).toString(16).padStart(2,"0")})`
    : "";
  return {
    status: "fail",
    failReason: lastCallRptFail ?? `${lastCall.step} 실패 — ${finalDesc}${finalCode}`,
  };
}

// ── single packet row ──────────────────────────────────────────────────────

function PacketRow({ ev, idx }: { ev: PacketEvent; idx: number }) {
  const [open, setOpen] = useState(false);
  const dirCfg = DIR_CFG[ev.direction] ?? DIR_CFG.TX;
  const time = new Date(ev.ts).toLocaleTimeString("ko-KR", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 2,
  } as Intl.DateTimeFormatOptions);

  const FIELD_ORDER = [
    "pkt_type", "data_len", "node_id", "msg_type", "msg_data_len",
    "level", "err_code", "err_code_desc",
    "port", "phone_len", "phone",
    "result_code", "result_desc",
    "parse_error",
  ];
  const parsedEntries = Object.entries(ev.parsed).sort(([a], [b]) => {
    const ai = FIELD_ORDER.indexOf(a);
    const bi = FIELD_ORDER.indexOf(b);
    if (ai === -1 && bi === -1) return 0;
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });

  const hasError = ev.parsed.parse_error || ev.parsed.err_code !== undefined;

  return (
    <div
      style={{
        borderLeft: `2px solid ${hasError ? "var(--color-fail)" : dirCfg.color}`,
        marginBottom: 1,
        background: open ? "rgba(255,255,255,0.03)" : "transparent",
      }}
    >
      <button
        onClick={() => setOpen((p) => !p)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 8,
          padding: "6px 10px", background: "none", border: "none",
          cursor: "pointer", textAlign: "left",
        }}
      >
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)", minWidth: 22 }}>
          {String(idx + 1).padStart(3, "0")}
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)", minWidth: 72 }}>
          {time}
        </span>
        <span
          style={{
            fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
            letterSpacing: "0.08em", padding: "1px 5px",
            background: dirCfg.bg, color: dirCfg.color,
            minWidth: 22, textAlign: "center",
          }}
        >
          {dirCfg.label}
        </span>
        <span
          style={{
            fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 600,
            color: stepColor(ev.step), flex: 1,
          }}
        >
          {ev.step}
        </span>
        <span style={{ fontSize: 9, color: "var(--color-fog)" }}>
          {open ? "▲" : "▼"}
        </span>
      </button>

      {open && (
        <div style={{ padding: "8px 14px 12px 44px", display: "flex", flexDirection: "column", gap: 10 }}>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: "0.1em", color: "var(--color-fog)", marginBottom: 4 }}>
              RAW HEX
            </div>
            <code
              style={{
                fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-haze)",
                background: "var(--color-bg)", padding: "6px 10px", display: "block",
                wordBreak: "break-all", letterSpacing: "0.04em",
                border: "1px solid var(--color-edge)",
              }}
            >
              {ev.hex_dump}
            </code>
          </div>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: "0.1em", color: "var(--color-fog)", marginBottom: 4 }}>
              PARSED · BACS_Control.md §1.3
            </div>
            <table style={{ borderCollapse: "collapse", width: "100%", fontFamily: "var(--font-mono)", fontSize: 10 }}>
              <tbody>
                {parsedEntries.map(([key, val]) => (
                  <tr key={key}>
                    <td style={{ padding: "2px 10px 2px 0", color: "var(--color-fog)", whiteSpace: "nowrap", verticalAlign: "top", width: "38%" }}>
                      {key}
                    </td>
                    <td
                      style={{
                        padding: "2px 0",
                        color:
                          key === "result_desc" && String(val).startsWith("OK")
                            ? "var(--color-ok)"
                            : key === "result_desc" || key === "err_code_desc" || key === "parse_error"
                            ? "var(--color-fail)"
                            : "var(--color-snow)",
                        wordBreak: "break-word",
                      }}
                    >
                      {String(val)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── pair section ───────────────────────────────────────────────────────────

const STATUS_CFG = {
  ok:      { label: "OK",      color: "var(--color-ok)" },
  fail:    { label: "FAIL",    color: "var(--color-fail)" },
  running: { label: "RUNNING", color: "var(--color-accent)" },
  none:    { label: "",        color: "var(--color-fog)" },
};

function PairSection({
  label, events, sectionIdx, isRunning,
}: {
  label: string;
  events: PacketEvent[];
  sectionIdx: number;
  isRunning: boolean;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const { status, failReason } = pairStatus(events);
  const displayStatus: "ok" | "fail" | "running" | "none" =
    status === "none" && isRunning ? "running" : status;
  const sCfg = STATUS_CFG[displayStatus];

  return (
    <div style={{ border: "1px solid var(--color-edge)", marginBottom: 6, background: "var(--color-bg2)" }}>
      {/* 세션 헤더 */}
      <button
        onClick={() => setCollapsed((p) => !p)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 10,
          padding: "7px 12px", background: "var(--color-bg)", border: "none",
          borderBottom: (collapsed && displayStatus !== "fail") ? "none" : "1px solid var(--color-edge)",
          cursor: "pointer", textAlign: "left",
        }}
      >
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700, letterSpacing: "0.14em", color: "var(--color-fog)", minWidth: 60 }}>
          SESSION {String(sectionIdx + 1).padStart(2, "0")}
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--color-haze)", flex: 1 }}>
          {label}
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)", marginRight: 8 }}>
          {events.length}패킷
        </span>
        {sCfg.label && (
          <span
            style={{
              fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
              letterSpacing: "0.1em", padding: "1px 6px",
              border: `1px solid ${sCfg.color}`, color: sCfg.color, marginRight: 6,
            }}
          >
            {sCfg.label}
          </span>
        )}
        <span style={{ fontSize: 9, color: "var(--color-fog)" }}>
          {collapsed ? "▶" : "▼"}
        </span>
      </button>

      {/* 실패 원인 밌드 네임플맠 — 헤더 아래 항상 표시 */}
      {displayStatus === "fail" && failReason && (
        <div
          style={{
            padding: "5px 12px 6px",
            background: "rgba(220,60,60,0.07)",
            borderBottom: "1px solid var(--color-edge)",
            display: "flex", alignItems: "center", gap: 8,
          }}
        >
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--color-fail)", letterSpacing: "0.1em", whiteSpace: "nowrap" }}>
            ⚠ FAIL REASON
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fail)", wordBreak: "break-word" }}>
            {failReason}
          </span>
        </div>
      )}

      {!collapsed && (
        <div>
          <div
            style={{
              display: "flex", gap: 8, padding: "4px 10px",
              background: "rgba(0,0,0,0.15)",
              fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: "0.08em",
              color: "var(--color-fog)", borderBottom: "1px solid var(--color-edge)",
            }}
          >
            <span style={{ minWidth: 22 }}>#</span>
            <span style={{ minWidth: 72 }}>TIME</span>
            <span style={{ minWidth: 22 }}>DIR</span>
            <span>STEP</span>
          </div>
          {events.map((ev, i) => (
            <PacketRow key={`${ev.ts}-${i}`} ev={ev} idx={i} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── main export ────────────────────────────────────────────────────────────

interface PacketLogProps {
  packets: PacketEvent[];
  isRunning: boolean;
}

export function PacketLog({ packets, isRunning }: PacketLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // group by pair_label, preserving first-seen order
  const pairOrder: string[] = [];
  const grouped: Record<string, PacketEvent[]> = {};
  for (const ev of packets) {
    if (!grouped[ev.pair_label]) {
      pairOrder.push(ev.pair_label);
      grouped[ev.pair_label] = [];
    }
    grouped[ev.pair_label].push(ev);
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [packets.length]);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--color-fog)" }}>
          PACKET LOG · BACS TCP §1.3
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          {isRunning && (
            <span
              style={{
                width: 5, height: 5, borderRadius: "50%",
                background: "var(--color-accent)", display: "inline-block",
                animation: "pulse 1.5s ease-in-out infinite",
              }}
            />
          )}
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)" }}>
            {pairOrder.length > 0
              ? `${pairOrder.length}세션 · ${packets.length}패킷`
              : `${packets.length}패킷`}
          </span>
        </div>
      </div>

      <div style={{ minHeight: 120, maxHeight: 560, overflowY: "auto" }}>
        {packets.length === 0 ? (
          <div
            style={{
              padding: "28px 18px", fontFamily: "var(--font-mono)", fontSize: 10,
              color: "var(--color-fog)", textAlign: "center",
              border: "1px solid var(--color-edge)", background: "var(--color-bg2)",
            }}
          >
            {isRunning ? "패킷 수신 대기 중..." : "호출시험을 실행하면 패킷이 표시됩니다."}
          </div>
        ) : (
          <>
            {pairOrder.map((label, si) => (
              <PairSection
                key={label}
                label={label}
                events={grouped[label]}
                sectionIdx={si}
                isRunning={isRunning}
              />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  );
}
