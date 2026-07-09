"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { DeviceGrid } from "@/components/DeviceGrid";
import { DeviceFormModal } from "@/components/DeviceFormModal";
import { api, getToken } from "@/lib/api";
import { Device, DeviceCreate, Health } from "@/lib/types";

export default function DevicesPage() {
  const router = useRouter();
  const [devices, setDevices]   = useState<Device[]>([]);
  const [health, setHealth]     = useState<Map<number, Health>>(new Map());
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]           = useState<string | null>(null);

  // 모달 상태: null = 닫힘, undefined = 신규 등록, Device = 수정
  const [editTarget, setEditTarget] = useState<Device | null | undefined>(undefined);
  const modalOpen = editTarget !== undefined;

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  const loadDevices = useCallback(async () => {
    try {
      const rows = await api.devices();
      setDevices(rows);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "장비 목록을 불러오지 못했습니다.");
    }
  }, []);

  const loadHealth = useCallback(async () => {
    try {
      const rows = await api.health();
      setHealth(new Map(rows.map((r) => [r.bacs_id, r])));
    } catch {
      // 폴링 에러는 기존 헬스 데이터 유지
    }
  }, []);

  useEffect(() => {
    loadDevices();
    loadHealth();
    const t = setInterval(loadHealth, 3000);
    return () => clearInterval(t);
  }, [loadDevices, loadHealth]);

  async function refresh() {
    setRefreshing(true);
    try {
      await api.refreshHealth();
      await loadHealth();
    } finally {
      setRefreshing(false);
    }
  }

  // 장비 저장 (신규/수정)
  async function handleSave(data: DeviceCreate) {
    if (editTarget) {
      // 수정
      await api.updateDevice(editTarget.id, data);
    } else {
      // 신규
      await api.createDevice(data);
    }
    await loadDevices();
  }

  // 장비 삭제
  async function handleDelete(device: Device) {
    if (!confirm(`"${device.name}" 를 삭제하시겠습니까?`)) return;
    await api.deleteDevice(device.id);
    await loadDevices();
  }

  const okCount  = [...devices].filter((d) => health.get(d.id)?.status === "online").length;
  const failCount= [...devices].filter((d) => health.get(d.id)?.status === "offline").length;

  return (
    <>
      <TopBar />

      {/* ── 에러 배너 ── */}
      {error && (
        <div
          style={{
            position: "relative",
            zIndex: 20,
            background: "rgba(180,60,60,0.15)",
            border: "1px solid rgba(180,60,60,0.4)",
            borderLeft: "3px solid #c0392b",
            padding: "10px 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "#e57373",
            letterSpacing: "0.05em",
          }}
        >
          <span>⚠ {error}</span>
          <button
            onClick={() => setError(null)}
            style={{
              background: "none", border: "none",
              color: "var(--color-fog)", cursor: "pointer",
              fontSize: 16, lineHeight: 1, padding: "0 4px",
            }}
          >×</button>
        </div>
      )}

      {/* ── 헬스 요약 바 ── */}
      {health.size > 0 && (() => {
        const vals = [...health.values()];
        const ok      = vals.filter((h) => h.status === "online").length;
        const fail    = vals.filter((h) => h.status === "offline").length;
        const unknown = vals.filter((h) => h.status === "unknown").length;
        return (
          <div
            style={{
              position: "relative",
              zIndex: 10,
              borderBottom: "1px solid var(--color-wire)",
              backgroundColor: "rgba(10,10,18,0.85)",
              backdropFilter: "blur(8px)",
              padding: "8px 24px",
              display: "flex",
              alignItems: "center",
              gap: 24,
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              letterSpacing: "0.1em",
            }}
          >
            <span style={{ color: "var(--color-haze)", textTransform: "uppercase" }}>
              BACS STATUS
            </span>
            {[
              { label: "ONLINE",  count: ok,      color: "var(--color-ok)"   },
              { label: "OFFLINE", count: fail,    color: "var(--color-fail)" },
              { label: "UNKNOWN", count: unknown, color: "var(--color-haze)" },
            ].map(({ label, count, color }) => (
              <span key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {/* 컬러 점 */}
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    backgroundColor: color,
                    display: "inline-block",
                    boxShadow: count > 0 ? `0 0 6px ${color}` : "none",
                  }}
                />
                <span style={{ color }}>{count}</span>
                <span style={{ color: "var(--color-haze)", opacity: 0.6 }}>{label}</span>
              </span>
            ))}
          </div>
        );
      })()}

      {/* 장비 등록/수정 모달 */}
      {modalOpen && (
        <DeviceFormModal
          initial={editTarget ?? null}
          onSave={handleSave}
          onClose={() => setEditTarget(undefined)}
        />
      )}

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
                { label: "ONLINE",  value: okCount,   color: "var(--color-ok)" },
                { label: "OFFLINE", value: failCount, color: failCount > 0 ? "var(--color-fail)" : "var(--color-fog)" },
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
            {/* 장비 등록 */}
            <button
              onClick={() => setEditTarget(null)}
              style={{
                padding: "8px 16px",
                background: "none",
                border: "1px solid var(--color-ok)",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                letterSpacing: "0.08em",
                color: "var(--color-ok)",
                cursor: "pointer",
              }}
            >
              + 장비 등록
            </button>

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


          </div>
        </div>

        {/* ── 장비 목록 ── */}
        <DeviceGrid
          devices={devices}
          health={health}
          onEdit={(device) => setEditTarget(device)}
          onDelete={handleDelete}
        />
      </div>
    </>
  );
}
