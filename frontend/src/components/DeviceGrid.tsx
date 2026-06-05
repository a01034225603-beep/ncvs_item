"use client";
import { useMemo, useState } from "react";
import { Device, Health, HealthStatus } from "@/lib/types";
import { HealthBadge } from "./HealthBadge";

type Props = {
  devices: Device[];
  health: Map<number, Health>;
  onEdit?: (device: Device) => void;
  onDelete?: (device: Device) => void;
};

const STATUS_TABS: { key: "all" | HealthStatus; label: string }[] = [
  { key: "all",     label: "전체" },
  { key: "online",  label: "ONLINE" },
  { key: "offline", label: "OFFLINE" },
  { key: "unknown", label: "UNKNOWN" },
];

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return "방금";
  if (diff < 60_000) return `${Math.floor(diff / 1000)}초 전`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`;
  return new Date(iso).toLocaleTimeString("ko-KR", { hour12: false, hour: "2-digit", minute: "2-digit" });
}

export function DeviceGrid({ devices, health, onEdit, onDelete }: Props) {
  const [search, setSearch]       = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | HealthStatus>("all");
  const [sortBy, setSortBy]       = useState<"name" | "status">("status");

  const counts = useMemo(() => {
    const c = { online: 0, offline: 0, unknown: 0 };
    for (const d of devices) c[health.get(d.id)?.status ?? "unknown"]++;
    return c;
  }, [devices, health]);

  const visible = useMemo(() => {
    const q = search.toLowerCase();
    let list = devices.filter((d) => {
      const status = health.get(d.id)?.status ?? "unknown";
      if (statusFilter !== "all" && status !== statusFilter) return false;
      if (q && !d.name.toLowerCase().includes(q) && !d.ip_address.includes(q)) return false;
      return true;
    });
    list = [...list].sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      const order: Record<string, number> = { offline: 0, unknown: 1, online: 2 };
      const sa = order[health.get(a.id)?.status ?? "unknown"] ?? 1;
      const sb = order[health.get(b.id)?.status ?? "unknown"] ?? 1;
      return sa - sb || a.name.localeCompare(b.name);
    });
    return list;
  }, [devices, health, search, statusFilter, sortBy]);

  return (
    <div>
      {/* ── 툴바 ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 10,
          flexWrap: "wrap",
        }}
      >
        {/* 검색 */}
        <div style={{ position: "relative", flex: "1 1 180px", minWidth: 140 }}>
          <span
            style={{
              position: "absolute",
              left: 10,
              top: "50%",
              transform: "translateY(-50%)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--color-fog)",
              pointerEvents: "none",
            }}
          >
            /
          </span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="이름 또는 IP 검색..."
            style={{
              width: "100%",
              background: "var(--color-panel)",
              border: "1px solid var(--color-edge)",
              borderLeft: "2px solid var(--color-accent)",
              padding: "7px 10px 7px 24px",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--color-snow)",
              outline: "none",
            }}
          />
        </div>

        {/* 상태 탭 */}
        <div style={{ display: "flex", border: "1px solid var(--color-edge)" }}>
          {STATUS_TABS.map(({ key, label }) => {
            const cnt = key === "all" ? devices.length : counts[key as HealthStatus];
            const active = statusFilter === key;
            return (
              <button
                key={key}
                onClick={() => setStatusFilter(key)}
                style={{
                  padding: "6px 12px",
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  letterSpacing: "0.05em",
                  border: "none",
                  borderRight: "1px solid var(--color-edge)",
                  background: active ? "var(--color-panel2)" : "var(--color-bg2)",
                  color: active ? "var(--color-snow)" : "var(--color-haze)",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  transition: "background 0.1s, color 0.1s",
                }}
              >
                {label}{" "}
                <span
                  style={{
                    color: active ? "var(--color-accent)" : "var(--color-fog)",
                    fontSize: 9,
                  }}
                >
                  {cnt}
                </span>
              </button>
            );
          })}
        </div>

        {/* 정렬 */}
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          style={{
            background: "var(--color-bg2)",
            border: "1px solid var(--color-edge)",
            padding: "6px 10px",
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.04em",
            color: "var(--color-haze)",
            outline: "none",
            cursor: "pointer",
          }}
        >
          <option value="status">정렬: 상태</option>
          <option value="name">정렬: 이름</option>

        </select>
      </div>



      {/* ── 장비 테이블 ── */}
      <div className="panel" style={{ overflow: "hidden" }}>
        {/* 헤더 + 데이터 행을 같은 스크롤 컨테이너 안에 넣어 열 폭 일치 */}
        <div style={{ maxHeight: 520, overflowY: "auto" }}>
          {/* 헤더 (sticky) */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 170px 90px 130px 100px",
              gap: 0,
              borderBottom: "1px dashed var(--color-edge)",
              background: "var(--color-bg2)",
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--color-fog)",
              alignItems: "stretch",
              position: "sticky",
              top: 0,
              zIndex: 1,
            }}
          >
            <span style={{ padding: "8px 12px", borderRight: "1px dashed var(--color-edge)" }}>장비명</span>
            <span style={{ padding: "8px 12px", borderRight: "1px dashed var(--color-edge)" }}>IP · 포트</span>
            <span style={{ padding: "8px 12px", borderRight: "1px dashed var(--color-edge)" }}>상태</span>
            <span style={{ padding: "8px 12px", borderRight: "1px dashed var(--color-edge)" }}>최근 확인</span>
            <span style={{ padding: "8px 12px" }}>관리</span>
          </div>
          {visible.length === 0 ? (
            <div
              style={{
                padding: "44px 0",
                textAlign: "center",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                letterSpacing: "0.08em",
                color: "var(--color-fog)",
              }}
            >
              해당 조건의 장비가 없습니다
            </div>
          ) : (
            visible.map((d) => {
              const h       = health.get(d.id);
              const status  = h?.status ?? "unknown";
              return (
                <div
                  key={d.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 170px 90px 130px 100px",
                    gap: 0,
                    padding: "0",
                    borderBottom: "1px dashed var(--color-edge)",
                    alignItems: "center",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.02)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                  }}
                >
                  {/* 장비명 */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      fontWeight: 500,
                      color: "var(--color-haze)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      padding: "9px 12px",
                      borderRight: "1px dashed var(--color-edge)",
                    }}
                  >
                    {d.name}
                  </span>

                  {/* IP */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      color: "var(--color-fog)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      padding: "9px 12px",
                      borderRight: "1px dashed var(--color-edge)",
                    }}
                  >
                    {d.ip_address}:{d.udp_port}
                  </span>

                  {/* 상태 */}
                  <span style={{ padding: "9px 12px", borderRight: "1px dashed var(--color-edge)", display: "flex", alignItems: "center" }}><HealthBadge status={status} /></span>

                  {/* 마지막 확인 */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      color: "var(--color-fog)",
                      padding: "9px 12px",
                      borderRight: "1px dashed var(--color-edge)",
                    }}
                  >
                    {relativeTime(h?.last_checked_at ?? null)}
                  </span>

                  {/* 수정/삭제 버튼 */}
                  {(onEdit || onDelete) && (
                    <div
                      style={{ display: "flex", gap: 4, padding: "9px 10px", alignItems: "center" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {onEdit && (
                        <button
                          onClick={() => onEdit(d)}
                          title="수정"
                          style={{
                            padding: "2px 7px",
                            background: "none",
                            border: "1px solid var(--color-wire)",
                            fontFamily: "var(--font-mono)", fontSize: 10,
                            color: "var(--color-haze)", cursor: "pointer",
                          }}
                        >
                          편집
                        </button>
                      )}
                      {onDelete && (
                        <button
                          onClick={() => onDelete(d)}
                          title="삭제"
                          style={{
                            padding: "2px 7px",
                            background: "none",
                            border: "1px solid var(--color-edge)",
                            fontFamily: "var(--font-mono)", fontSize: 10,
                            color: "var(--color-fail)", cursor: "pointer",
                          }}
                        >
                          삭제
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 하단 카운트 */}
      <div
        style={{
          marginTop: 6,
          display: "flex",
          justifyContent: "flex-end",
          fontFamily: "var(--font-mono)",
          fontSize: 9,
          letterSpacing: "0.06em",
          color: "var(--color-fog)",
        }}
      >
        {visible.length} / {devices.length}개 표시
      </div>
    </div>
  );
}
