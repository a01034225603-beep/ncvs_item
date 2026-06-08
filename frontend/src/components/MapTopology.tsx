/**
 * 호출시험 결과 망도(Network Topology) 컴포넌트
 *
 * 역할:
 *   KoreaMap SVG 위에 호출시험 결과(MatrixCell[])를 겹쳐 표시한다.
 *   장비 위치 마커와 발신->착신 연결선 색상으로 ok/fail 결과를 시각화한다.
 *   tests/[id]/page.tsx(결과 화면)에서 사용된다.
 */
"use client";

/**
 * MapTopology — 호출시험 결과를 대한민국 지도 위에 망도로 표시
 *
 * - 위치 정보(geo_x/geo_y)가 있는 장비만 지도에 표시
 * - 위치 정보가 없는 장비는 하단 "미배치 장비" 목록으로 표시
 * - 같은 위치(같은 sid/sigungu) 장비 간 통신 → 루프 아이콘(↺)
 * - 서로 다른 위치 → 구역 간 엣지(선)로 표시
 * - 노드 클릭 → 해당 위치 장비 목록 + 개별 결과 팝업
 */

import React, { useState, useMemo } from "react";
import { KoreaMap, MapNode, MapEdge } from "./KoreaMap";
import { Device, MatrixCell } from "@/lib/types";

interface Props {
  devices: Device[];
  cells: MatrixCell[];
}

interface NodeGroup {
  /** 대표 nodeId (devices 배열 내 첫 번째 장비 id를 그룹 대표로 사용) */
  groupId: number;
  label: string;  // sido + sigungu
  geo_x: number;
  geo_y: number;
  deviceIds: number[];
}

interface PopupInfo {
  groupId: number;
  label: string;
  deviceIds: number[];
}

export function MapTopology({ devices, cells }: Props) {
  const [popup, setPopup] = useState<PopupInfo | null>(null);

  // ── 위치 있는 장비만 노드 그룹으로 묶기 ─────────────────────────────
  const { groups, ungrouped } = useMemo(() => {
    const groupMap = new Map<string, NodeGroup>();
    const ungroupedDevices: Device[] = [];

    devices.forEach((d) => {
      if (d.geo_x == null || d.geo_y == null) {
        ungroupedDevices.push(d);
        return;
      }
      // sido+sigungu 조합으로 그룹 키 생성
      const key = `${d.sido ?? ""}::${d.sigungu ?? ""}::${d.geo_x.toFixed(1)}::${d.geo_y.toFixed(1)}`;
      const label = [d.sido, d.sigungu].filter(Boolean).join(" ") || `(${d.geo_x.toFixed(0)},${d.geo_y.toFixed(0)})`;

      if (!groupMap.has(key)) {
        groupMap.set(key, {
          groupId: d.id,  // 첫 번째 장비 id를 그룹 대표
          label,
          geo_x: d.geo_x,
          geo_y: d.geo_y,
          deviceIds: [],
        });
      }
      groupMap.get(key)!.deviceIds.push(d.id);
    });

    return {
      groups: Array.from(groupMap.values()),
      ungrouped: ungroupedDevices,
    };
  }, [devices]);

  // ── deviceId → groupId 역맵 ───────────────────────────────────────
  const deviceGroupMap = useMemo(() => {
    const m = new Map<number, number>();
    groups.forEach((g) => g.deviceIds.forEach((id) => m.set(id, g.groupId)));
    return m;
  }, [groups]);

  // ── 엣지 및 루프 계산 ─────────────────────────────────────────────
  const { edges, selfLoops } = useMemo(() => {
    // 그룹 간 엣지: {src_groupId → {dst_groupId → {ok, total}}}
    const edgeMap = new Map<string, { src: number; dst: number; ok: number; total: number }>();
    // 같은 그룹 내 루프: {groupId → {ok, total}}
    const loopMap = new Map<number, { ok: number; total: number }>();

    cells.forEach((c) => {
      const srcGroup = deviceGroupMap.get(c.src_bacs_id);
      const dstGroup = deviceGroupMap.get(c.dst_bacs_id);
      if (srcGroup == null || dstGroup == null) return;

      const isOk = c.status === "ok" ? 1 : 0;

      if (srcGroup === dstGroup) {
        // 같은 그룹 내 자기 루프
        const prev = loopMap.get(srcGroup) ?? { ok: 0, total: 0 };
        loopMap.set(srcGroup, { ok: prev.ok + isOk, total: prev.total + 1 });
      } else {
        // 그룹 간 엣지 (src < dst 방향으로 정규화하여 중복 방지는 하지 않음 — 단방향 표시)
        const key = `${srcGroup}-${dstGroup}`;
        const prev = edgeMap.get(key) ?? { src: srcGroup, dst: dstGroup, ok: 0, total: 0 };
        edgeMap.set(key, { ...prev, ok: prev.ok + isOk, total: prev.total + 1 });
      }
    });

    const mapEdges: MapEdge[] = Array.from(edgeMap.values()).map((e) => ({
      src_id: e.src,
      dst_id: e.dst,
      ratio: e.total > 0 ? e.ok / e.total : 0,
      ok: e.ok,
      total: e.total,
    }));

    const selfLoopsRecord: Record<number, { ok: number; total: number }> = {};
    loopMap.forEach((v, k) => { selfLoopsRecord[k] = v; });

    return { edges: mapEdges, selfLoops: selfLoopsRecord };
  }, [cells, deviceGroupMap]);

  // ── KoreaMap용 노드 변환 ─────────────────────────────────────────
  const mapNodes: MapNode[] = useMemo(() =>
    groups.map((g) => ({
      id: g.groupId,
      label: g.label,
      geo_x: g.geo_x,
      geo_y: g.geo_y,
    })),
  [groups]);

  // ── 팝업 내 장비별 결과 ────────────────────────────────────────────
  function getDeviceResults(deviceId: number) {
    const asSrc = cells.filter((c) => c.src_bacs_id === deviceId);
    const asDst = cells.filter((c) => c.dst_bacs_id === deviceId);
    return { asSrc, asDst };
  }

  function getDeviceName(id: number) {
    return devices.find((d) => d.id === id)?.name ?? `#${id}`;
  }

  const SELECT_STYLE: React.CSSProperties = {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--color-snow)",
  };

  return (
    <div style={{ position: "relative" }}>
      {/* ── 지도 영역 ─────────────────────────────────────────────── */}
      <div
        style={{
          width: "100%",
          aspectRatio: "1 / 1.3",
          background: "var(--color-bg)",
          border: "1px solid var(--color-edge)",
          borderRadius: 4,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <KoreaMap
          nodes={mapNodes}
          edges={edges}
          selfLoops={selfLoops}
          onNodeClick={(groupId) => {
            const g = groups.find((x) => x.groupId === groupId);
            if (!g) return;
            setPopup({ groupId, label: g.label, deviceIds: g.deviceIds });
          }}
        />

        {/* 범례 */}
        <div
          style={{
            position: "absolute", bottom: 8, right: 10,
            display: "flex", flexDirection: "column", gap: 3,
          }}
        >
          {[
            { color: "var(--color-ok, #3dba7e)", label: "전체 성공" },
            { color: "#e8a735",                  label: "일부 실패" },
            { color: "var(--color-fail, #ff3355)",label: "전체 실패" },
          ].map(({ color, label }) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{ width: 8, height: 2, background: color, borderRadius: 1 }} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 7, color: "var(--color-fog)" }}>
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── 미배치 장비 목록 ───────────────────────────────────────── */}
      {ungrouped.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.12em",
            color: "var(--color-fog)", marginBottom: 4,
          }}>
            위치 미등록 장비 ({ungrouped.length}대) — 지도에 표시되지 않음
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {ungrouped.map((d) => {
              const results = getDeviceResults(d.id);
              const total = results.asSrc.length + results.asDst.length;
              const ok = results.asSrc.filter((c) => c.status === "ok").length
                       + results.asDst.filter((c) => c.status === "ok").length;
              return (
                <div
                  key={d.id}
                  style={{
                    padding: "3px 8px",
                    border: "1px solid var(--color-edge)",
                    fontFamily: "var(--font-mono)", fontSize: 9,
                    color: "var(--color-haze)",
                  }}
                >
                  {d.name}
                  {total > 0 && (
                    <span style={{ color: ok === total ? "var(--color-ok)" : "var(--color-fail)", marginLeft: 4 }}>
                      {ok}/{total}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 팝업 — 노드 클릭 시 장비 상세 ────────────────────────── */}
      {popup && (
        <div
          onClick={() => setPopup(null)}
          style={{
            position: "fixed", inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--color-panel2, #141414)",
              border: "1px solid var(--color-wire)",
              padding: "20px 22px 18px",
              minWidth: 320, maxWidth: 480,
              maxHeight: "70vh", overflowY: "auto",
              boxShadow: "0 12px 48px rgba(0,0,0,0.6)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 14 }}>
              <span style={{ ...SELECT_STYLE, fontSize: 13, fontWeight: 700, color: "var(--color-snow)" }}>
                {popup.label}
              </span>
              <button
                onClick={() => setPopup(null)}
                style={{ background: "none", border: "none", color: "var(--color-fog)", cursor: "pointer", fontSize: 14 }}
              >✕</button>
            </div>

            {popup.deviceIds.map((devId) => {
              const { asSrc, asDst } = getDeviceResults(devId);
              const hasCells = asSrc.length > 0 || asDst.length > 0;
              return (
                <div key={devId} style={{ marginBottom: 12 }}>
                  <div style={{ ...SELECT_STYLE, fontWeight: 600, color: "var(--color-haze)", marginBottom: 4 }}>
                    {getDeviceName(devId)}
                  </div>

                  {!hasCells && (
                    <div style={{ ...SELECT_STYLE, color: "var(--color-fog)" }}>결과 없음</div>
                  )}

                  {asSrc.length > 0 && (
                    <div style={{ marginBottom: 4 }}>
                      <div style={{ ...SELECT_STYLE, fontSize: 8, color: "var(--color-fog)", marginBottom: 2 }}>
                        발신 (TX)
                      </div>
                      {asSrc.map((c) => (
                        <div key={`${c.src_bacs_id}-${c.dst_bacs_id}`}
                          style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 2 }}>
                          <span style={{
                            ...SELECT_STYLE, fontSize: 8,
                            color: c.status === "ok" ? "var(--color-ok)" : "var(--color-fail)",
                            minWidth: 14,
                          }}>
                            {c.status === "ok" ? "✓" : "✕"}
                          </span>
                          <span style={{ ...SELECT_STYLE, color: "var(--color-fog)" }}>
                            → {getDeviceName(c.dst_bacs_id)}
                          </span>
                          {c.error_message && (
                            <span style={{ ...SELECT_STYLE, color: "var(--color-fail)", fontSize: 8 }}>
                              {c.error_message}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {asDst.length > 0 && (
                    <div>
                      <div style={{ ...SELECT_STYLE, fontSize: 8, color: "var(--color-fog)", marginBottom: 2 }}>
                        착신 (RX)
                      </div>
                      {asDst.map((c) => (
                        <div key={`${c.src_bacs_id}-${c.dst_bacs_id}`}
                          style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 2 }}>
                          <span style={{
                            ...SELECT_STYLE, fontSize: 8,
                            color: c.status === "ok" ? "var(--color-ok)" : "var(--color-fail)",
                            minWidth: 14,
                          }}>
                            {c.status === "ok" ? "✓" : "✕"}
                          </span>
                          <span style={{ ...SELECT_STYLE, color: "var(--color-fog)" }}>
                            ← {getDeviceName(c.src_bacs_id)}
                          </span>
                          {c.error_message && (
                            <span style={{ ...SELECT_STYLE, color: "var(--color-fail)", fontSize: 8 }}>
                              {c.error_message}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
