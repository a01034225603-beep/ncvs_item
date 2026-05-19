"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { TestProgress } from "@/components/TestProgress";
import { api } from "@/lib/api";
import { Session } from "@/lib/types";

export default function TestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: idParam } = use(params);
  const id = Number(idParam);
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const s = await api.session(id);
        if (active) setSession(s);
      } catch { /* silently ignore */ }
    }
    poll();
    const t = setInterval(poll, 3000);
    return () => { active = false; clearInterval(t); };
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
                fontFamily: "var(--font-display)",
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
              {session && (
                <button
                  onClick={() => router.push(`/matrix?ids=${session.device_ids.join(",")}`)}
                  style={{
                    padding: "8px 14px",
                    background: "none",
                    border: "1px solid var(--color-wire)",
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    letterSpacing: "0.08em",
                    color: "var(--color-haze)",
                    cursor: "pointer",
                    transition: "border-color 0.15s, color 0.15s",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-accent)"; e.currentTarget.style.color = "var(--color-accent)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-wire)"; e.currentTarget.style.color = "var(--color-haze)"; }}
                >
                  매트릭스 보기 →
                </button>
              )}

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

        {/* 뒤로 가기 */}
        <div style={{ marginTop: 20 }}>
          <a
            href="/devices"
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
            ← 장비 목록으로
          </a>
        </div>
      </div>
    </>
  );
}
