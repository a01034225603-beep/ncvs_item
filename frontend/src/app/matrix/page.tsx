"use client";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { Matrix } from "@/components/Matrix";
import { api } from "@/lib/api";
import { Device, MatrixCell } from "@/lib/types";

const MAX_RECOMMENDED = 64;

function MatrixContent() {
  const searchParams = useSearchParams();

  const [allDevices, setAllDevices] = useState<Device[]>([]);
  const [cells, setCells]           = useState<MatrixCell[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [search, setSearch]         = useState("");
  const [loading, setLoading]       = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    api.devices().then((ds) => {
      setAllDevices(ds);
      const idsParam = searchParams.get("ids");
      if (idsParam) {
        const ids = new Set(idsParam.split(",").map(Number).filter(Boolean));
        setSelectedIds(ids);
      } else {
        setSelectedIds(new Set(ds.slice(0, MAX_RECOMMENDED).map((d) => d.id)));
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadMatrix = useCallback(async (ids: number[]) => {
    if (ids.length === 0) { setCells([]); return; }
    setLoading(true);
    try { setCells(await api.matrix(ids)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    loadMatrix([...selectedIds]);
  }, [selectedIds, loadMatrix]);

  const filteredDevices = useMemo(() => {
    const q = search.toLowerCase();
    return allDevices.filter(
      (d) => !q || d.name.toLowerCase().includes(q) || d.ip_address.includes(q)
    );
  }, [allDevices, search]);

  const matrixDevices = useMemo(
    () => allDevices.filter((d) => selectedIds.has(d.id)),
    [allDevices, selectedIds]
  );

  function toggleDevice(id: number) {
    setSelectedIds((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  }

  const selCount = selectedIds.size;
  const overLimit = selCount > MAX_RECOMMENDED;
  const pairCount = matrixDevices.length * (matrixDevices.length - 1);

  const sideBtn: React.CSSProperties = {
    padding: "3px 8px",
    background: "none",
    border: "1px solid var(--color-wire)",
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    letterSpacing: "0.04em",
    color: "var(--color-haze)",
    cursor: "pointer",
    transition: "border-color 0.1s, color 0.1s",
  };

  return (
    <div style={{ display: "flex", flex: 1, minHeight: "calc(100vh - 44px)" }}>

      {/* ── 사이드바 ── */}
      <aside
        style={{
          width: sidebarOpen ? 240 : 40,
          flexShrink: 0,
          borderRight: "1px solid var(--color-edge)",
          background: "var(--color-bg2)",
          display: "flex",
          flexDirection: "column",
          transition: "width 0.2s ease",
          overflow: "hidden",
          position: "relative",
          zIndex: 20,
        }}
      >
        {/* 사이드바 토글 */}
        <button
          onClick={() => setSidebarOpen((o) => !o)}
          style={{
            flexShrink: 0,
            padding: "10px",
            background: "none", border: "none",
            borderBottom: "1px solid var(--color-edge)",
            cursor: "pointer",
            display: "flex", alignItems: "center", gap: 8,
            fontFamily: "var(--font-mono)", fontSize: 9,
            letterSpacing: "0.06em", color: "var(--color-haze)",
            justifyContent: sidebarOpen ? "flex-start" : "center",
            whiteSpace: "nowrap", width: "100%",
          }}
        >
          <span>{sidebarOpen ? "◀" : "▶"}</span>
          {sidebarOpen && (
            <span>
              장비 선택{" "}
              <span style={{ color: "var(--color-accent)" }}>{selCount}개</span>
            </span>
          )}
        </button>

        {/* 사이드바 본문 */}
        {sidebarOpen && (
          <div
            style={{
              flex: 1,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
              padding: "10px 10px 0",
              gap: 8,
            }}
          >
            {/* 검색 */}
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="장비 검색..."
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-edge)",
                borderLeft: "2px solid var(--color-accent)",
                padding: "5px 8px",
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-snow)", outline: "none", flexShrink: 0,
              }}
            />

            {/* 일괄 버튼 */}
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap", flexShrink: 0 }}>
              <button
                onClick={() => setSelectedIds(new Set(allDevices.slice(0, MAX_RECOMMENDED).map((d) => d.id)))}
                style={sideBtn}
              >
                전체 (≤{MAX_RECOMMENDED})
              </button>
              <button
                onClick={() => setSelectedIds(new Set(filteredDevices.slice(0, MAX_RECOMMENDED).map((d) => d.id)))}
                style={sideBtn}
              >
                현재 목록
              </button>
              <button onClick={() => setSelectedIds(new Set())} style={sideBtn}>
                초기화
              </button>
            </div>

            {/* 초과 경고 */}
            {overLimit && (
              <div
                style={{
                  borderLeft: "2px solid var(--color-warn)",
                  paddingLeft: 8,
                  fontFamily: "var(--font-mono)", fontSize: 9,
                  letterSpacing: "0.04em", color: "var(--color-warn)",
                  lineHeight: 1.5, flexShrink: 0,
                }}
              >
                {selCount}개 선택. {MAX_RECOMMENDED}개 초과 시 느릴 수 있습니다.
              </div>
            )}

            {/* 장비 목록 */}
            <div style={{ flex: 1, overflowY: "auto", paddingBottom: 12 }}>
              {filteredDevices.map((d) => {
                const isSel = selectedIds.has(d.id);
                return (
                  <div
                    key={d.id}
                    onClick={() => toggleDevice(d.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 7,
                      padding: "5px 4px", cursor: "pointer",
                      borderLeft: `2px solid ${isSel ? "var(--color-accent)" : "transparent"}`,
                      background: isSel ? "rgba(93,155,148,0.05)" : "transparent",
                      userSelect: "none",
                    }}
                    onMouseEnter={(e) => { if (!isSel) e.currentTarget.style.background = "rgba(255,255,255,0.02)"; }}
                    onMouseLeave={(e) => { if (!isSel) e.currentTarget.style.background = "transparent"; }}
                  >
                    <span
                      style={{
                        width: 10, height: 10,
                        border: `1px solid ${isSel ? "var(--color-accent)" : "var(--color-wire)"}`,
                        background: isSel ? "rgba(93,155,148,0.2)" : "transparent",
                        display: "inline-flex", alignItems: "center", justifyContent: "center",
                        fontSize: 7, color: "var(--color-accent)", flexShrink: 0,
                      }}
                    >
                      {isSel && "✓"}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)", fontSize: 11,
                        color: isSel ? "var(--color-snow)" : "var(--color-haze)",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}
                    >
                      {d.name}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </aside>

      {/* ── 매트릭스 메인 ── */}
      <main
        style={{ flex: 1, padding: "28px 24px 64px", overflow: "hidden", minWidth: 0 }}
      >
        {/* 헤더 */}
        <div style={{ marginBottom: 24 }}>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 24, fontWeight: 700,
              color: "var(--color-snow)",
              letterSpacing: "-0.02em",
              margin: "0 0 8px",
            }}
          >
            호시험 결과 매트릭스
          </h1>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11, color: "var(--color-fog)",
              letterSpacing: "0.04em", margin: 0,
            }}
          >
            행 = 송신 · 열 = 수신 ·{" "}
            {matrixDevices.length}개 장비 · {pairCount}개 페어
          </p>
        </div>

        {loading ? (
          <div
            className="animate-blink"
            style={{
              textAlign: "center", padding: "80px 0",
              fontFamily: "var(--font-mono)", fontSize: 12,
              letterSpacing: "0.12em", color: "var(--color-fog)",
            }}
          >
            데이터 로딩 중…
          </div>
        ) : matrixDevices.length === 0 ? (
          <div
            style={{
              textAlign: "center", padding: "80px 0",
              fontFamily: "var(--font-mono)", fontSize: 12,
              color: "var(--color-fog)", letterSpacing: "0.08em", lineHeight: 2,
            }}
          >
            왼쪽 사이드바에서 장비를 선택하면 매트릭스가 표시됩니다.
            {!sidebarOpen && (
              <>
                <br />
                <span style={{ fontSize: 10, opacity: 0.6 }}>▶ 를 눌러 사이드바를 열어보세요</span>
              </>
            )}
          </div>
        ) : (
          <div className="panel" style={{ padding: 20, overflow: "visible" }}>
            <Matrix devices={matrixDevices} cells={cells} />
          </div>
        )}
      </main>
    </div>
  );
}

export default function MatrixPage() {
  return (
    <>
      <TopBar />
      <Suspense
        fallback={
          <div
            className="animate-blink"
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              minHeight: "calc(100vh - 44px)",
              fontFamily: "var(--font-mono)", fontSize: 12,
              letterSpacing: "0.12em", color: "var(--color-fog)",
            }}
          >
            초기화 중…
          </div>
        }
      >
        <MatrixContent />
      </Suspense>
    </>
  );
}
