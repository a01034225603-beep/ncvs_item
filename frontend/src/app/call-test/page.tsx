"use client";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { PacketLog } from "@/components/PacketLog";
import { api, getToken } from "@/lib/api";
import { Device, Health, PacketEvent, PairStatus, Scenario, SessionWithPairs } from "@/lib/types";
import { computeRounds, ROUND_COLORS } from "@/lib/rounds";

// HealthDot, PhoneCell, PairCard 는 call-test/session-plan/page.tsx 로 이동됨

/* ─── 본문 ──────────────────────────────────────────────────── */
function CallTestContent() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const scenarioId   = Number(searchParams.get("scenario_id"));

  const [scenario,   setScenario]   = useState<Scenario | null>(null);
  const [devices,    setDevices]    = useState<Device[]>([]);
  const [healthMap,  setHealthMap]  = useState<Map<number, Health["status"]>>(new Map());
  const [loading,    setLoading]    = useState(true);
  const [starting,   setStarting]   = useState(false);
  const [runningSessionId, setRunningSessionId] = useState<number | null>(null);
  const [packets,      setPackets]    = useState<PacketEvent[]>([]);
  const [testDone,     setTestDone]   = useState(false);
  // 페어별 실시간 상태 맵: "src_id-dst_id" → PairStatus
  const [pairStateMap, setPairStateMap] = useState<Map<string, PairStatus>>(new Map());
  const packetSseRef = useRef<EventSource | null>(null);
  const streamSseRef = useRef<EventSource | null>(null);

  // testDone 시 결과 페이지로 자동 이동 — 시험 완료 즉시 결과 확인
  useEffect(() => {
    if (testDone && runningSessionId !== null) {
      // SSE 정리 후 결과 페이지 이동
      if (packetSseRef.current) { packetSseRef.current.close(); packetSseRef.current = null; }
      if (streamSseRef.current) { streamSseRef.current.close(); streamSseRef.current = null; }
      router.push(`/tests/${runningSessionId}`);
    }
  }, [testDone, runningSessionId, router]);
  // scenario가 null이면 빈 배열로 처리 (early return이 아래에서 처리)
  const _deviceMap = new Map(devices.map((d) => [d.id, d]));
  const _senderIds   = scenario?.sender_device_ids   ?? [];
  const _receiverIds = scenario?.receiver_device_ids ?? [];
  const _pairs: Array<{ src: Device; dst: Device }> = [];
  for (const srcId of _senderIds) {
    for (const dstId of _receiverIds) {
      if (srcId === dstId) continue;
      const src = _deviceMap.get(srcId);
      const dst = _deviceMap.get(dstId);
      if (src && dst) _pairs.push({ src, dst });
    }
  }
  // Vizing 라운드 계산 — 병렬 실행 가능한 페어 그룹
  const rounds = useMemo(
    () => computeRounds(_pairs.map(({ src, dst }, idx) => ({ id: String(idx), s: src.id, r: dst.id }))),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scenario, devices],
  );

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    if (!scenarioId) { router.replace("/");       return; }

    Promise.all([
      api.scenarios(),
      api.devices(),
      api.health(),
    ]).then(([scenarios, devs, healths]) => {
      const sc = scenarios.find((s) => s.id === scenarioId) ?? null;
      setScenario(sc);
      setDevices(devs);
      setHealthMap(new Map(healths.map((h) => [h.bacs_id, h.status])));
    }).finally(() => setLoading(false));
  }, [router, scenarioId]);

  if (loading) {
    return (
      <>
        <TopBar />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100vh - 48px)", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--color-fog)" }}>
          로딩 중…
        </div>
      </>
    );
  }

  if (!scenario) {
    return (
      <>
        <TopBar />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100vh - 48px)", gap: 12, flexDirection: "column" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--color-fog)" }}>시나리오를 찾을 수 없습니다.</div>
          <button onClick={() => router.push("/")} style={{ padding: "8px 20px", background: "none", border: "1px solid var(--color-wire)", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-haze)", cursor: "pointer" }}>← 돌아가기</button>
        </div>
      </>
    );
  }

  const deviceMap = new Map(devices.map((d) => [d.id, d]));

  // session_service.py 와 동일한 페어 생성 로직 (_pairs 는 위에서 이미 계산)
  const pairs = _pairs;

  const allIds = [...new Set([...scenario.sender_device_ids, ...scenario.receiver_device_ids])];
  const onlineCount  = allIds.filter((id) => healthMap.get(id) === "online").length;
  const offlineCount = allIds.filter((id) => healthMap.get(id) === "offline").length;
  // 포트별 호출: 각 페어당 2콜 (Port 0, Port 1)
  const totalCalls = pairs.length * 2;

  const hasAnyOffline = pairs.some(
    ({ src, dst }) => healthMap.get(src.id) === "offline" || healthMap.get(dst.id) === "offline"
  );
  const hasAnyMissingPhone = pairs.some(
    ({ src, dst }) =>
      !src.port0_phone || !src.port1_phone ||
      !dst.port2_phone || !dst.port3_phone
  );

  /** 호출 중단 — SSE 연결 종료 + 백엔드 세션 cancelled 처리 + 상태 초기화 */
  async function handleCancel() {
    // SSE 연결 즉시 종료
    if (packetSseRef.current) { packetSseRef.current.close(); packetSseRef.current = null; }
    if (streamSseRef.current) { streamSseRef.current.close(); streamSseRef.current = null; }
    // 백엔드 세션 cancelled 상태로 전환
    if (runningSessionId !== null) {
      try {
        await api.cancelSession(runningSessionId);
      } catch {
        // 이미 종료된 세션이면 무시
      }
    }
    // 상태 초기화
    setRunningSessionId(null);
    setPackets([]);
    setTestDone(false);
    setPairStateMap(new Map());
    // 홈 화면으로 이동
    router.push("/");
  }

  async function handleStart() {
    // 이전 SSE 정리
    if (packetSseRef.current) { packetSseRef.current.close(); packetSseRef.current = null; }
    if (streamSseRef.current) { streamSseRef.current.close(); streamSseRef.current = null; }
    setPackets([]);
    setTestDone(false);
    setPairStateMap(new Map());
    setRunningSessionId(null);
    setStarting(true);
    try {
      const session = await api.startTest(scenario!.id);
      setRunningSessionId(session.id);
      // 페이지 이동 없이 즉시 SSE 구독
      const token = getToken()!;
      // Next.js 프록시를 거치면 SSE 응답이 버퍼링됨 → 백엔드(포트 8000)에 직접 연결
      const backendBase = `${window.location.protocol}//${window.location.hostname}:8000`;
      const sse = new EventSource(`${backendBase}/tests/${session.id}/packets?token=${encodeURIComponent(token)}`);
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
        setTestDone(true);
      });
      sse.onerror = () => {
        sse.close();
        packetSseRef.current = null;
        setTestDone(true);
      };

      // 세션 스트림 SSE — 라운드 컨트롤 테이블 실시간 업데이트
      const streamSse = new EventSource(`${backendBase}/tests/${session.id}/stream?token=${encodeURIComponent(token)}`);
      streamSseRef.current = streamSse;
      streamSse.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as SessionWithPairs;
          const next = new Map<string, PairStatus>();
          for (const p of data.pairs) {
            next.set(`${p.src_bacs_id}-${p.dst_bacs_id}`, p.status);
          }
          setPairStateMap(next);
        } catch { /* ignore */ }
      };
      streamSse.addEventListener("done", () => {
        streamSse.close();
        streamSseRef.current = null;
      });
      streamSse.onerror = () => {
        streamSse.close();
        streamSseRef.current = null;
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "시험 시작 실패";
      alert(`오류: ${msg}`);
    } finally {
      setStarting(false);
    }
  }

  const panelStyle: React.CSSProperties = {
    background: "var(--color-panel, #141414)",
    border: "1px solid var(--color-edge)",
    borderRadius: 4,
  };

  return (
    <>
      <TopBar />
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "36px 24px 80px" }}>

        {/* 뒤로 가기 */}
        <button
          onClick={() => router.push("/")}
          style={{
            background: "none", border: "none", padding: 0,
            fontFamily: "var(--font-mono)", fontSize: 11,
            color: "var(--color-fog)", cursor: "pointer",
            letterSpacing: "0.06em", marginBottom: 24,
          }}
        >
          ← 시나리오 목록
        </button>

        {/* 헤더 */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--color-fog)", marginBottom: 6 }}>
            호출 시험 준비  ·  BACS_Control.md §1.3
          </div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--color-snow)", margin: 0, letterSpacing: "-0.02em" }}>
            {scenario.name}
          </h1>
        </div>

        {/* KPI 타일 */}
        <div
          style={{
            ...panelStyle,
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            marginBottom: 24,
          }}
        >
          {[
            { label: "전체 장비",   value: allIds.length,  color: "var(--color-haze)" },
            { label: "ONLINE",     value: onlineCount,    color: "var(--color-ok)" },
            { label: "OFFLINE",    value: offlineCount,   color: offlineCount > 0 ? "var(--color-fail)" : "var(--color-fog)" },
            { label: "세션 페어",  value: pairs.length,   color: "var(--color-accent)" },
            { label: "총 호출 수", value: totalCalls,     color: "var(--color-snow)" },
          ].map(({ label, value, color }, i) => (
            <div
              key={label}
              style={{
                padding: "16px 18px",
                borderRight: i < 4 ? "1px solid var(--color-edge)" : "none",
                textAlign: "center",
              }}
            >
              <div style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: "0.1em", color: "var(--color-fog)", marginTop: 5 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* 세션 계획 보기 버튼 — 클릭 시 별도 탭에서 상세 내용 표시 */}
        <div style={{ marginBottom: 28 }}>
          {pairs.length === 0 ? (
            <div style={{
              padding: "16px", textAlign: "center",
              border: "1px solid var(--color-edge)", background: "var(--color-bg2)",
              fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-fail)",
            }}>
              유효한 페어 없음 — 발신·착신 장비가 동일하거나 데이터 미설정
            </div>
          ) : (
            <button
              onClick={() => window.open(`/call-test/session-plan?scenario_id=${scenarioId}`, "_blank")}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 18px",
                background: "var(--color-bg2)",
                border: "1px solid var(--color-edge)",
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-haze)",
                cursor: "pointer", letterSpacing: "0.06em",
              }}
            >
              <span style={{ color: "var(--color-accent)" }}>☰</span>
              세션 계획 보기
              <span style={{ fontSize: 9, color: "var(--color-fog)" }}>
                ({pairs.length}개 페어 · {totalCalls}회 호출)
              </span>
              <span style={{ fontSize: 9, color: "var(--color-wire)", marginLeft: 4 }}>↗ 새 탭</span>
            </button>
          )}
        </div>

        {/* 경고 메시지 */}
        {(hasAnyOffline || hasAnyMissingPhone) && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 24 }}>
            {hasAnyOffline && (
              <div style={{
                padding: "10px 16px",
                border: "1px solid var(--color-fail)",
                background: "rgba(255,80,80,0.05)",
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-fail)",
                display: "flex", alignItems: "center", gap: 8,
              }}>
                <span>⚠</span>
                OFFLINE 장비가 포함된 세션은 실패로 처리될 수 있습니다.
              </div>
            )}
            {hasAnyMissingPhone && (
              <div style={{
                padding: "10px 16px",
                border: "1px solid var(--color-warn)",
                background: "rgba(217,119,6,0.05)",
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-warn)",
                display: "flex", alignItems: "center", gap: 8,
              }}>
                <span>⚠</span>
                전화번호 미설정 장비가 있습니다. 장비 설정 화면에서 Port0·1 (TX) / Port2·3 (RX) 번호를 입력해주세요.
              </div>
            )}
          </div>
        )}

        {/* 라운드별 진행 현황 — 호출시험 시작 후 표시 */}
        {runningSessionId !== null && rounds.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.14em",
              textTransform: "uppercase", color: "var(--color-fog)", marginBottom: 10,
              display: "flex", alignItems: "center", gap: 10,
            }}>
              라운드별 진행 현황
              <span style={{ fontSize: 8, color: "var(--color-wire)" }}>
                (같은 라운드 = 병렬 실행)
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {rounds.map((round, ri) => {
                const color = ROUND_COLORS[ri % ROUND_COLORS.length];
                return (
                  <div
                    key={ri}
                    style={{
                      border: `1px solid ${color}33`,
                      background: "var(--color-bg2)",
                      overflow: "hidden",
                    }}
                  >
                    {/* 라운드 헤더 */}
                    <div style={{
                      padding: "5px 12px",
                      background: `${color}18`,
                      borderBottom: `1px solid ${color}33`,
                      display: "flex", alignItems: "center", gap: 10,
                    }}>
                      <span style={{
                        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
                        letterSpacing: "0.1em", color,
                      }}>
                        ROUND {ri + 1}
                      </span>
                      <span style={{
                        fontFamily: "var(--font-mono)", fontSize: 8,
                        color: "var(--color-fog)",
                      }}>
                        {round.pairs.length}개 병렬
                      </span>
                    </div>

                    {/* 페어 행 목록 */}
                    <div style={{ display: "flex", flexDirection: "column" }}>
                      {round.pairs.map((p, pi) => {
                        const src = deviceMap.get(p.s);
                        const dst = deviceMap.get(p.r);
                        const stKey = `${p.s}-${p.r}`;
                        const st: PairStatus = pairStateMap.get(stKey) ?? "pending";

                        const stCfg: Record<PairStatus, { label: string; color: string }> = {
                          pending:  { label: "대기",   color: "var(--color-wire)" },
                          running:  { label: "실행 중", color: "var(--color-warn)" },
                          ok:       { label: "OK",     color: "var(--color-ok)" },
                          fail:     { label: "FAIL",   color: "var(--color-fail)" },
                          skipped:  { label: "SKIP",   color: "var(--color-fog)" },
                        };
                        const cfg = stCfg[st];

                        return (
                          <div
                            key={pi}
                            style={{
                              display: "flex", alignItems: "center", gap: 8,
                              padding: "6px 12px",
                              borderTop: pi > 0 ? "1px solid var(--color-edge)" : "none",
                            }}
                          >
                            {/* 상태 배지 */}
                            <span style={{
                              fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
                              letterSpacing: "0.06em", color: cfg.color,
                              minWidth: 50, textAlign: "center",
                              padding: "2px 6px",
                              background: `${cfg.color}18`,
                              border: `1px solid ${cfg.color}55`,
                              flexShrink: 0,
                            }}>
                              {cfg.label}
                            </span>
                            {/* 발신 */}
                            <span style={{
                              fontFamily: "var(--font-mono)", fontSize: 10,
                              color: "var(--color-ok)", fontWeight: 600,
                            }}>
                              {src?.name ?? `ID${p.s}`}
                            </span>
                            <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)" }}>
                              {src?.ip_address}
                            </span>
                            <span style={{ color: "var(--color-fog)", fontSize: 12, flexShrink: 0 }}>→</span>
                            {/* 착신 */}
                            <span style={{
                              fontFamily: "var(--font-mono)", fontSize: 10,
                              color: "var(--color-warn)", fontWeight: 600,
                            }}>
                              {dst?.name ?? `ID${p.r}`}
                            </span>
                            <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)" }}>
                              {dst?.ip_address}
                            </span>
                            {/* running 일 때 깜빡이는 점 */}
                            {st === "running" && (
                              <span style={{
                                width: 6, height: 6, borderRadius: "50%",
                                background: "var(--color-warn)",
                                flexShrink: 0, marginLeft: 4,
                                animation: "pulse 1s infinite",
                              }} />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 실시간 패킷 로그 */}
        {runningSessionId !== null && (
          <div style={{ marginTop: 24 }}>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              marginBottom: 8,
            }}>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 11,
                letterSpacing: "0.08em", color: "var(--color-fog)",
                textTransform: "uppercase",
              }}>
                {testDone ? "● 시험 완료 — 결과 화면으로 이동 중…" : "● 실시간 패킷"}
              </span>
            </div>
            <PacketLog packets={packets} isRunning={!testDone} />
          </div>
        )}

        {/* 시작 / 중단 버튼 영역 */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
          {/* 세션 실행 중 → 호출 중단 / 그 외 → 뒤로 가기 */}
          {runningSessionId !== null ? (
            <button
              onClick={handleCancel}
              style={{
                padding: "12px 28px", background: "rgba(255,80,80,0.08)",
                border: "1px solid var(--color-fail)",
                fontFamily: "var(--font-mono)", fontSize: 11,
                letterSpacing: "0.06em", color: "var(--color-fail)",
                cursor: "pointer",
              }}
            >
              ■ 호출 중단
            </button>
          ) : (
            <button
              onClick={() => router.push("/")}
              style={{
                padding: "12px 28px", background: "none",
                border: "1px solid var(--color-wire)",
                fontFamily: "var(--font-mono)", fontSize: 11,
                letterSpacing: "0.06em", color: "var(--color-fog)",
                cursor: "pointer",
              }}
            >
              취소
            </button>
          )}
          <button
            onClick={handleStart}
            disabled={starting || pairs.length === 0}
            style={{
              padding: "12px 40px",
              background: starting ? "var(--color-wire)" : "rgba(93,155,148,0.15)",
              border: `1px solid ${starting || pairs.length === 0 ? "var(--color-wire)" : "var(--color-accent)"}`,
              fontFamily: "var(--font-mono)", fontSize: 13,
              letterSpacing: "0.1em",
              color: starting || pairs.length === 0 ? "var(--color-fog)" : "var(--color-accent)",
              cursor: starting || pairs.length === 0 ? "not-allowed" : "pointer",
              fontWeight: 700, transition: "all 0.15s",
            }}
          >
            {starting ? "시작 중..." : `▶ 호출 시험 시작 (${pairs.length}페어)`}
          </button>
        </div>
      </div>
    </>
  );
}

export default function CallTestPage() {
  return (
    <Suspense>
      <CallTestContent />
    </Suspense>
  );
}

