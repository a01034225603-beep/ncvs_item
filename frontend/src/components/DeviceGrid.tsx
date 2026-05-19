"use client";
import { useMemo, useState } from "react";
import { Device, Health, HealthStatus } from "@/lib/types";
import { HealthBadge } from "./HealthBadge";

type Props = {
  devices: Device[];
  health: Map<number, Health>;
  selected: Set<number>;
  onToggle: (id: number) => void;
  onSelectAll: (ids: number[]) => void;
  onClearAll: () => void;
};

const STATUS_TABS: { key: "all" | HealthStatus; label: string }[] = [
  { key: "all",     label: "전체" },
  { key: "ok",      label: "정상" },
  { key: "fail",    label: "장애" },
  { key: "unknown", label: "미확인" },
];

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return "방금";
  if (diff < 60_000) return `${Math.floor(diff / 1000)}초 전`;
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`;
  return new Date(iso).toLocaleTimeString("ko-KR", { hour12: false, hour: "2-digit", minute: "2-digit" });
}

export function DeviceGrid({ devices, health, selected, onToggle, onSelectAll, onClearAll }: Props) {
  const [search, setSearch]       = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | HealthStatus>("all");
  const [sortBy, setSortBy]       = useState<"name" | "status" | "fail">("status");

  const counts = useMemo(() => {
    const c = { ok: 0, fail: 0, unknown: 0 };
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
      if (sortBy === "fail") {
        return (health.get(b.id)?.consecutive_fail ?? 0) - (health.get(a.id)?.consecutive_fail ?? 0);
      }
      const order: Record<string, number> = { fail: 0, unknown: 1, ok: 2 };
      const sa = order[health.get(a.id)?.status ?? "unknown"] ?? 1;
      const sb = order[health.get(b.id)?.status ?? "unknown"] ?? 1;
      return sa - sb || a.name.localeCompare(b.name);
    });
    return list;
  }, [devices, health, search, statusFilter, sortBy]);

  function selectByStatus(s: HealthStatus) {
    onSelectAll(devices.filter((d) => (health.get(d.id)?.status ?? "unknown") === s).map((d) => d.id));
  }

  const selCount = selected.size;

  /* Shared small-button style */
  const chip: React.CSSProperties = {
    padding: "3px 10px",
    background: "none",
    border: "1px solid var(--color-wire)",
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    letterSpacing: "0.04em",
    color: "var(--color-haze)",
    cursor: "pointer",
    transition: "border-color 0.12s, color 0.12s",
  };

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
          <option value="fail">정렬: 장애 횟수</option>
        </select>
      </div>

      {/* ── 일괄 선택 ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          marginBottom: 8,
          flexWrap: "wrap",
          fontFamily: "var(--font-mono)",
          fontSize: 10,
        }}
      >
        <span style={{ color: "var(--color-fog)", marginRight: 2 }}>일괄 선택</span>

        <button
          onClick={() => onSelectAll(visible.map((d) => d.id))}
          style={chip}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-accent)"; e.currentTarget.style.color = "var(--color-accent)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-wire)"; e.currentTarget.style.color = "var(--color-haze)"; }}
        >
          현재 목록 ({visible.length})
        </button>

        <button
          onClick={() => selectByStatus("ok")}
          style={chip}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-ok)"; e.currentTarget.style.color = "var(--color-ok)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-wire)"; e.currentTarget.style.color = "var(--color-haze)"; }}
        >
          전체 정상 ({counts.ok})
        </button>

        <button
          onClick={() => selectByStatus("fail")}
          style={chip}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-fail)"; e.currentTarget.style.color = "var(--color-fail)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-wire)"; e.currentTarget.style.color = "var(--color-haze)"; }}
        >
          전체 장애 ({counts.fail})
        </button>

        {selCount > 0 && (
          <>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-accent)",
                letterSpacing: "0.02em",
                marginLeft: 8,
              }}
            >
              {selCount}개 선택됨
            </span>
            <button
              onClick={onClearAll}
              style={chip}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--color-fail)"; e.currentTarget.style.color = "var(--color-fail)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-wire)"; e.currentTarget.style.color = "var(--color-haze)"; }}
            >
              선택 초기화
            </button>
          </>
        )}
      </div>

      {/* ── 장비 테이블 ── */}
      <div className="panel" style={{ overflow: "hidden" }}>
        {/* 헤더 */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "28px 1fr 170px 90px 80px 130px",
            gap: "0 12px",
            padding: "8px 14px",
            borderBottom: "1px solid var(--color-edge)",
            background: "var(--color-bg2)",
            fontFamily: "var(--font-mono)",
            fontSize: 9,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--color-fog)",
            alignItems: "center",
          }}
        >
          <span />
          <span>장비명</span>
          <span>IP · 포트</span>
          <span>상태</span>
          <span>연속 장애</span>
          <span>최근 확인</span>
        </div>

        {/* 스크롤 영역 */}
        <div style={{ maxHeight: 520, overflowY: "auto" }}>
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
              const isSel   = selected.has(d.id);
              const failCnt = h?.consecutive_fail ?? 0;

              return (
                <div
                  key={d.id}
                  onClick={() => onToggle(d.id)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "28px 1fr 170px 90px 80px 130px",
                    gap: "0 12px",
                    padding: "9px 14px",
                    borderBottom: "1px solid var(--color-edge)",
                    borderLeft: `2px solid ${isSel ? "var(--color-accent)" : "transparent"}`,
                    background: isSel ? "rgba(93,155,148,0.05)" : "transparent",
                    cursor: "pointer",
                    alignItems: "center",
                    transition: "background 0.1s",
                    userSelect: "none",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSel) e.currentTarget.style.background = "rgba(255,255,255,0.02)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSel) e.currentTarget.style.background = "transparent";
                  }}
                >
                  {/* 체크박스 */}
                  <span
                    style={{
                      width: 13,
                      height: 13,
                      border: `1px solid ${isSel ? "var(--color-accent)" : "var(--color-wire)"}`,
                      background: isSel ? "rgba(93,155,148,0.2)" : "transparent",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      transition: "border-color 0.1s",
                    }}
                  >
                    {isSel && (
                      <span style={{ fontSize: 8, color: "var(--color-accent)", lineHeight: 1 }}>✓</span>
                    )}
                  </span>

                  {/* 장비명 */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      fontWeight: 500,
                      color: isSel ? "var(--color-snow)" : "var(--color-haze)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
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
                    }}
                  >
                    {d.ip_address}:{d.udp_port}
                  </span>

                  {/* 상태 */}
                  <span><HealthBadge status={status} /></span>

                  {/* 연속 장애 */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      color: failCnt > 0 ? "var(--color-fail)" : "var(--color-fog)",
                      fontWeight: failCnt > 2 ? 600 : 400,
                    }}
                  >
                    {failCnt > 0 ? `× ${failCnt}` : "—"}
                  </span>

                  {/* 마지막 확인 */}
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      color: "var(--color-fog)",
                    }}
                  >
                    {relativeTime(h?.last_checked_at ?? null)}
                  </span>
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
