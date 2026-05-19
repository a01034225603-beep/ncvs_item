"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { DeviceGrid } from "@/components/DeviceGrid";
import { api, getToken } from "@/lib/api";
import { Device, Health } from "@/lib/types";

export default function DevicesPage() {
  const router = useRouter();
  const [devices, setDevices]   = useState<Device[]>([]);
  const [health, setHealth]     = useState<Map<number, Health>>(new Map());
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  const loadHealth = useCallback(async () => {
    const rows = await api.health();
    setHealth(new Map(rows.map((r) => [r.bacs_id, r])));
  }, []);

  useEffect(() => {
    api.devices().then(setDevices);
    loadHealth();
    const t = setInterval(loadHealth, 3000);
    return () => clearInterval(t);
  }, [loadHealth]);

  function toggle(id: number) {
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  }

  function addToSelection(ids: number[]) {
    setSelected((s) => {
      const n = new Set(s);
      ids.forEach((id) => n.add(id));
      return n;
    });
  }

  async function refresh() {
    setRefreshing(true);
    try {
      await api.refreshHealth();
      await loadHealth();
    } finally {
      setRefreshing(false);
    }
  }

  async function startTest() {
    if (selected.size < 2) return;
    const session = await api.startTest([...selected]);
    router.push(`/tests/${session.id}`);
  }

  const selArr   = [...selected];
  const canTest  = selected.size >= 2;
  const okCount  = [...devices].filter((d) => health.get(d.id)?.status === "ok").length;
  const failCount= [...devices].filter((d) => health.get(d.id)?.status === "fail").length;

  return (
    <>
      <TopBar />
      <div
        style={{
          position: "relative",
          zIndex: 10,
          maxWidth: 1200,
          margin: "0 auto",
          padding: "32px 24px 64px",
        }}
      >
        {/* ── 페이지 헤더 ── */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
            marginBottom: 28,
          }}
        >
          <div>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 24,
                fontWeight: 700,
                color: "var(--color-snow)",
                margin: "0 0 12px",
                letterSpacing: "-0.02em",
              }}
            >
              BACS 장비 목록
            </h1>

            {/* 플릿 요약 */}
            <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
              {[
                { label: "전체",  value: devices.length, color: "var(--color-haze)" },
                { label: "정상",  value: okCount,         color: "var(--color-ok)" },
                { label: "장애",  value: failCount,        color: failCount > 0 ? "var(--color-fail)" : "var(--color-fog)" },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 20,
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

              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  color: "var(--color-fog)",
                  letterSpacing: "0.04em",
                }}
              >
                · 3초 자동 갱신
              </span>
            </div>
          </div>

          {/* 액션 버튼 */}
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button
              onClick={refresh}
              disabled={refreshing}
              style={{
                padding: "8px 14px",
                background: "none",
                border: "1px solid var(--color-wire)",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                letterSpacing: "0.08em",
                color: refreshing ? "var(--color-fog)" : "var(--color-haze)",
                cursor: refreshing ? "not-allowed" : "pointer",
                opacity: refreshing ? 0.6 : 1,
                transition: "color 0.12s, border-color 0.12s",
              }}
            >
              {refreshing ? "갱신 중…" : "↻ 새로고침"}
            </button>

            {canTest && (
              <button
                onClick={() => router.push(`/matrix?ids=${selArr.join(",")}`)}
                style={{
                  padding: "8px 14px",
                  background: "none",
                  border: "1px solid var(--color-accent)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  letterSpacing: "0.08em",
                  color: "var(--color-accent)",
                  cursor: "pointer",
                  transition: "background 0.12s",
                }}
              >
                결과 매트릭스 →
              </button>
            )}

            <button
              onClick={startTest}
              disabled={!canTest}
              style={{
                padding: "8px 20px",
                background: canTest ? "var(--color-accent)" : "var(--color-edge)",
                border: "none",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.1em",
                color: canTest ? "#fff" : "var(--color-fog)",
                cursor: canTest ? "pointer" : "not-allowed",
                transition: "background 0.18s",
              }}
            >
              테스트 실행 {canTest ? `(${selected.size})` : ""}
            </button>
          </div>
        </div>

        {/* ── 장비 목록 ── */}
        <DeviceGrid
          devices={devices}
          health={health}
          selected={selected}
          onToggle={toggle}
          onSelectAll={addToSelection}
          onClearAll={() => setSelected(new Set())}
        />
      </div>
    </>
  );
}
