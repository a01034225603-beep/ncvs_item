"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { api, getToken } from "@/lib/api";
import { Device, Scenario } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  // null = 아직 토큰 확인 전, true/false = 인증 여부
  const [authed, setAuthed]       = useState<boolean | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [devices, setDevices]     = useState<Device[]>([]);
  const [loading, setLoading]     = useState(true);
  const [deleting, setDeleting]   = useState<number | null>(null);

  /* 클라이언트에서 토큰 확인 (리다이렉트 없이 상태만 변경) */
  useEffect(() => {
    setAuthed(!!getToken());
  }, []);

  const load = useCallback(async () => {
    try {
      const [sc, dv] = await Promise.all([api.scenarios(), api.devices()]);
      setScenarios(sc);
      setDevices(dv);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authed) load();
    else if (authed === false) setLoading(false);
  }, [authed, load]);

  /* 장비 ID → 이름 Map */
  const deviceMap = new Map(devices.map((d) => [d.id, d]));

  /* 시나리오 삭제 */
  async function handleDelete(id: number) {
    if (!confirm("시나리오를 삭제하시겠습니까?")) return;
    setDeleting(id);
    try {
      await api.deleteScenario(id);
      setScenarios((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setDeleting(null);
    }
  }

  /* ── 인증 전: 랜딩 화면 ── */
  if (authed === false) {
    return (
      <>
        <TopBar />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "calc(100vh - 48px)",
            gap: 24,
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 9,
                letterSpacing: "0.2em",
                textTransform: "uppercase",
                color: "var(--color-fog)",
                marginBottom: 10,
              }}
            >
              RICS BACS Monitor
            </div>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 28,
                fontWeight: 700,
                color: "var(--color-snow)",
                margin: 0,
                letterSpacing: "-0.02em",
              }}
            >
              BACS 상태 모니터링
            </h1>
            <p
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                color: "var(--color-fog)",
                marginTop: 12,
                letterSpacing: "0.04em",
              }}
            >
              서비스를 이용하려면 로그인이 필요합니다
            </p>
          </div>
          <button
            onClick={() => router.push("/login")}
            style={{
              padding: "12px 36px",
              background: "rgba(93,155,148,0.12)",
              border: "1px solid var(--color-accent)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              letterSpacing: "0.1em",
              color: "var(--color-accent)",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            로그인
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <TopBar />
      <div
        style={{
          maxWidth: 900,
          margin: "0 auto",
          padding: "36px 24px 64px",
        }}
      >
        {/* 헤더 */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: 28,
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 9,
                letterSpacing: "0.2em",
                textTransform: "uppercase",
                color: "var(--color-fog)",
                marginBottom: 6,
              }}
            >
              BACS Monitor
            </div>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 24,
                fontWeight: 700,
                color: "var(--color-snow)",
                margin: 0,
                letterSpacing: "-0.02em",
              }}
            >
              시나리오 선택
            </h1>
          </div>

          <button
            onClick={() => router.push("/tests")}
            style={{
              padding: "9px 20px",
              background: "rgba(93,155,148,0.1)",
              border: "1px solid var(--color-accent)",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              letterSpacing: "0.08em",
              color: "var(--color-accent)",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            + 시나리오 등록
          </button>
        </div>

        {/* 시나리오 목록 */}
        {loading ? (
          <div
            style={{
              padding: "60px 0",
              textAlign: "center",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--color-fog)",
              letterSpacing: "0.1em",
            }}
          >
            로딩 중…
          </div>
        ) : scenarios.length === 0 ? (
          <div
            style={{
              padding: "60px 24px",
              textAlign: "center",
              border: "1px dashed var(--color-wire)",
              borderRadius: 4,
            }}
          >
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--color-fog)", marginBottom: 16, letterSpacing: "0.06em" }}>
              등록된 시나리오가 없습니다
            </div>
            <button
              onClick={() => router.push("/tests")}
              style={{
                padding: "8px 20px",
                background: "none",
                border: "1px solid var(--color-wire)",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-haze)",
                cursor: "pointer",
              }}
            >
              시나리오 등록하러 가기 →
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {scenarios.map((sc) => {
              const senders   = sc.sender_device_ids.map((id) => deviceMap.get(id));
              const receivers = sc.receiver_device_ids.map((id) => deviceMap.get(id));
              const pairCount = sc.sender_device_ids.length * sc.receiver_device_ids.length;
              const createdAt = new Date(sc.created_at).toLocaleString("ko-KR", {
                month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
              });

              return (
                <div
                  key={sc.id}
                  style={{
                    border: "1px solid var(--color-edge)",
                    borderRadius: 4,
                    overflow: "hidden",
                    background: "var(--color-panel, #141414)",
                    transition: "border-color 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--color-wire)")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--color-edge)")}
                >
                  {/* 상단: 이름 + 메타 */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "12px 16px 10px",
                      borderBottom: "1px solid var(--color-edge)",
                      flexWrap: "wrap",
                      gap: 8,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span
                        style={{
                          fontFamily: "var(--font-display)",
                          fontSize: 15,
                          fontWeight: 600,
                          color: "var(--color-snow)",
                          letterSpacing: "-0.01em",
                        }}
                      >
                        {sc.name}
                      </span>
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: 9,
                          letterSpacing: "0.08em",
                          color: "var(--color-accent)",
                          background: "rgba(93,155,148,0.1)",
                          padding: "2px 8px",
                          borderRadius: 2,
                        }}
                      >
                        {pairCount}쌍
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)" }}>
                        {createdAt}
                      </span>
                      {/* 이전 결과 보기 */}
                      <button
                        onClick={async () => {
                          const latest = await api.latestSessionByScenario(sc.id);
                          if (latest) {
                            router.push(`/tests/${latest.id}`);
                          } else {
                            alert("이전 시험 기록이 없습니다");
                          }
                        }}
                        style={{
                          padding: "2px 14px",
                          background: "none",
                          border: "1px solid var(--color-wire)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 9,
                          letterSpacing: "0.06em",
                          color: "var(--color-fog)",
                          cursor: "pointer",
                        }}
                      >
                        이전 결과 →
                      </button>
                      {/* 호출 시험 준비 화면으로 이동 */}
                      <button
                        onClick={() => router.push(`/call-test?scenario_id=${sc.id}`)}
                        style={{
                          padding: "2px 14px",
                          background: "rgba(93,155,148,0.1)",
                          border: "1px solid var(--color-accent)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 9,
                          letterSpacing: "0.06em",
                          color: "var(--color-accent)",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                      >
                        ▶ 호출 시험
                      </button>
                      <button
                        onClick={() => handleDelete(sc.id)}
                        disabled={deleting === sc.id}
                        style={{
                          padding: "2px 10px",
                          background: "none",
                          border: "1px solid var(--color-edge)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 9,
                          color: "var(--color-fail)",
                          cursor: deleting === sc.id ? "not-allowed" : "pointer",
                          opacity: deleting === sc.id ? 0.5 : 1,
                        }}
                      >
                        삭제
                      </button>
                    </div>
                  </div>

                  {/* 하단: 발신/착신 정보 */}
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr auto 1fr",
                      gap: 0,
                      padding: "10px 16px",
                      alignItems: "start",
                    }}
                  >
                    {/* 발신 */}
                    <div>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.1em", color: "var(--color-ok)", marginBottom: 6 }}>
                        ▲ 발신 ({sc.sender_device_ids.length})
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {senders.map((d, i) => (
                          <span
                            key={i}
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: 10,
                              color: "var(--color-haze)",
                              background: "var(--color-bg2)",
                              border: "1px solid var(--color-wire)",
                              padding: "2px 8px",
                              borderRadius: 2,
                            }}
                          >
                            {d ? d.name : `ID${sc.sender_device_ids[i]}`}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* 화살표 */}
                    <div
                      style={{
                        padding: "0 16px",
                        fontFamily: "var(--font-mono)",
                        fontSize: 18,
                        color: "var(--color-edge)",
                        lineHeight: 1,
                        alignSelf: "center",
                      }}
                    >
                      →
                    </div>

                    {/* 착신 */}
                    <div>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.1em", color: "var(--color-warn)", marginBottom: 6 }}>
                        ▼ 착신 ({sc.receiver_device_ids.length})
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {receivers.map((d, i) => (
                          <span
                            key={i}
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: 10,
                              color: "var(--color-haze)",
                              background: "var(--color-bg2)",
                              border: "1px solid var(--color-wire)",
                              padding: "2px 8px",
                              borderRadius: 2,
                            }}
                          >
                            {d ? d.name : `ID${sc.receiver_device_ids[i]}`}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
