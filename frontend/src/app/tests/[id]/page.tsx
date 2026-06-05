"use client";
import { use, useEffect, useRef, useState } from "react";
import { TopBar } from "@/components/TopBar";
import { TestProgress } from "@/components/TestProgress";
import { PacketLog } from "@/components/PacketLog";
import { Matrix } from "@/components/Matrix";
import { MapTopology } from "@/components/MapTopology";
import { api, getToken } from "@/lib/api";
import { Device, MatrixCell, PacketEvent, Scenario, Session } from "@/lib/types";

export default function TestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: idParam } = use(params);
  const id = Number(idParam);
  const [session, setSession] = useState<Session | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [packets, setPackets] = useState<PacketEvent[]>([]);
  const [matrixCells, setMatrixCells] = useState<MatrixCell[]>([]);
  const [matrixDevices, setMatrixDevices] = useState<Device[]>([]);
  const [resultView, setResultView] = useState<"matrix" | "map">("map");
  // 패킷 SSE 중복 방지용 ref
  const packetSseRef = useRef<EventSource | null>(null);

  // ── 시나리오 조회 — session.scenario_id 확정되면 해당 시나리오 이름 표시
  useEffect(() => {
    if (!session?.scenario_id) return;
    api.scenarios().then((list) => {
      const found = list.find((s) => s.id === session.scenario_id);
      if (found) setScenario(found);
    }).catch(() => { /* 무시 — 시나리오명은 부가정보 */ });
  }, [session?.scenario_id]);

  // ── 세션 완료 시 결과 매트릭스 로드
  useEffect(() => {
    if (!session || !["completed", "cancelled", "failed"].includes(session.status)) return;
    if (session.device_ids.length === 0) return;
    Promise.all([
      api.matrix(session.device_ids),
      api.devices(),
    ]).then(([cells, allDevices]) => {
      setMatrixCells(cells);
      setMatrixDevices(allDevices.filter((d) => session.device_ids.includes(d.id)));
    }).catch(() => { /* 무시 */ });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.status]);

  // ── 세션 상태 SSE ────────────────────────────────────────────────────
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const sse = new EventSource(`/api/tests/${id}/stream?token=${encodeURIComponent(token)}`);
    sse.onmessage = (e) => {
      try { setSession(JSON.parse(e.data) as Session); } catch { /* ignore */ }
    };
    sse.addEventListener("done", () => sse.close());
    sse.onerror = () => sse.close();
    return () => sse.close();
  }, [id]);

  // ── 패킷 이벤트 SSE ─────────────────────────────────────────────────
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    // 이미 연결 중이면 재연결하지 않음
    if (packetSseRef.current) return;
    const sse = new EventSource(`/api/tests/${id}/packets?token=${encodeURIComponent(token)}`);
    packetSseRef.current = sse;
    sse.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as PacketEvent;
        setPackets((prev) => [...prev, ev]);
      } catch { /* ignore */ }
    };
    sse.addEventListener("done", () => {
      sse.close();
      packetSseRef.current = null;
    });
    sse.onerror = () => {
      sse.close();
      packetSseRef.current = null;
    };
    return () => {
      sse.close();
      packetSseRef.current = null;
    };
  }, [id]);

  async function cancel() {
    if (!confirm(`세션 #${id}을 취소하겠습니까?`)) return;
    setCancelling(true);
    try { await api.cancelSession(id); }
    finally { setCancelling(false); }
  }

  return (
    <>
      <TopBar />
      <div
        style={{
          position: "relative",
          zIndex: 10,
          maxWidth: 860,
          margin: "0 auto",
          padding: "28px 24px 64px",
        }}
      >
        {/* 헤더 */}
        <div style={{ marginBottom: 28 }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              color: "var(--color-accent)",
              marginBottom: 8,
            }}
          >
            02// TEST SESSION
          </div>

            {/* 시나리오명 표시 — scenario_id가 있는 세션의 경우 */}
            {scenario && (
              <div style={{
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-fog)", letterSpacing: "0.06em",
                marginBottom: 4,
              }}>
                시나리오: <span style={{ color: "var(--color-haze)", fontWeight: 600 }}>{scenario.name}</span>
              </div>
            )}

          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 14,
            }}
          >
            <h1
              style={{
                fontSize: 26,
                fontWeight: 700,
                color: "var(--color-snow)",
                letterSpacing: "-0.02em",
                margin: 0,
              }}
            >
              세션 #{id}
            </h1>

            <div style={{ display: "flex", gap: 8 }}>
              {session?.status === "running" && (
                <button
                  onClick={cancel}
                  disabled={cancelling}
                  style={{
                    padding: "8px 14px",
                    background: "rgba(255,51,85,0.08)",
                    border: "1px solid var(--color-fail)",
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    letterSpacing: "0.08em",
                    color: "var(--color-fail)",
                    cursor: cancelling ? "not-allowed" : "pointer",
                    opacity: cancelling ? 0.6 : 1,
                  }}
                >
                  {cancelling ? "취소 중…" : "✕ 테스트 취소"}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* 진행 상황 */}
        {session ? (
          <div className="panel-frame" style={{ padding: "24px 24px 28px" }}>
            <TestProgress s={session} />
          </div>
        ) : (
          <div
            className="animate-blink"
            style={{
              textAlign: "center",
              padding: "80px 0",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              letterSpacing: "0.18em",
              color: "var(--color-fog)",
            }}
          >
            세션 {id} 로딩 중…
          </div>
        )}

        {/* 결과 뷰 — 세션 완료/취소/실패 시 망도 + 매트릭스 탭 */}
        {matrixCells.length > 0 && matrixDevices.length > 0 && (
          <div className="panel-frame" style={{ padding: "20px 24px 24px", marginTop: 16 }}>
            {/* 탭 헤더 */}
            <div style={{ display: "flex", gap: 0, marginBottom: 14, borderBottom: "1px solid var(--color-edge)" }}>
              {(["map", "matrix"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setResultView(v)}
                  style={{
                    padding: "4px 16px 6px",
                    background: "none",
                    border: "none",
                    borderBottom: resultView === v ? "2px solid var(--color-accent)" : "2px solid transparent",
                    fontFamily: "var(--font-mono)",
                    fontSize: 9,
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                    color: resultView === v ? "var(--color-accent)" : "var(--color-fog)",
                    cursor: "pointer",
                  }}
                >
                  {v === "map" ? "광역 망도" : "매트릭스"}
                </button>
              ))}
            </div>
            {/* 탭 콘텐츠 */}
            {resultView === "map" ? (
              <MapTopology devices={matrixDevices} cells={matrixCells} />
            ) : (
              <Matrix devices={matrixDevices} cells={matrixCells} />
            )}
          </div>
        )}

        {/* 패킷 로그 — TX/RX 패킷 상세 (BACS_Control.md §1.3) */}
        <div
          className="panel-frame"
          style={{ padding: "20px 24px 24px", marginTop: 16 }}
        >
          <PacketLog
            packets={packets}
            isRunning={session?.status === "running"}
          />
        </div>

        {/* 뒤로 가기 */}
        <div style={{ marginTop: 20 }}>
          <a
            href="/"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              letterSpacing: "0.08em",
              color: "var(--color-fog)",
              textDecoration: "none",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--color-accent)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-fog)")}
          >
            ← 홈으로
          </a>
        </div>
      </div>
    </>
  );
}
