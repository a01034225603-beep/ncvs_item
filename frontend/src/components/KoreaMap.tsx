"use client";

/**
 * KoreaMap — 대한민국 간략 SVG 지도 (폐쇄망 내장)
 * viewBox: "0 0 100 100"  →  geo_x/geo_y (0~100%) 좌표계와 1:1 대응
 */

import React from "react";

/** 한반도 본토 윤곽선 (단순화된 다각형) */
const MAINLAND_PATH =
  "M28,9 L35,7 L45,5 L55,4 L65,5 L72,6 L80,8 L87,12 L92,18 L94,26 " +
  "L93,34 L92,42 L91,50 L89,57 L87,63 L85,67 L82,69 L78,72 L73,73 " +
  "L68,72 L63,71 L57,73 L52,75 L47,76 L42,78 L37,80 L33,79 L30,74 " +
  "L28,68 L30,60 L27,53 L26,45 L28,37 L26,29 L27,20 L28,13 Z";

/** 제주도 */
const JEJU_PATH = "M24,90 L28,88 L34,88 L38,90 L36,94 L30,95 L25,93 Z";

/** 울릉도·독도 (소형 원으로 표시) */
const ISLANDS: Array<{ cx: number; cy: number; r: number; label: string }> = [
  { cx: 93, cy: 22, r: 1.2, label: "울릉도" },
];

export interface MapNode {
  id: number;
  label: string;
  geo_x: number;
  geo_y: number;
}

export interface MapEdge {
  src_id: number;
  dst_id: number;
  /** 성공 비율 0~1 (0=전체실패, 1=전체성공) */
  ratio: number;
  /** 해당 엣지의 총 쌍 수 */
  total: number;
  /** 성공 쌍 수 */
  ok: number;
}

interface Props {
  nodes: MapNode[];
  edges: MapEdge[];
  /** 클러스터 노드 클릭 콜백 */
  onNodeClick?: (nodeId: number) => void;
  /** 같은 위치 루프(자체 통신) 정보: nodeId → {ok, total} */
  selfLoops?: Record<number, { ok: number; total: number }>;
}

function edgeColor(ratio: number): string {
  if (ratio >= 1)   return "var(--color-ok, #3dba7e)";
  if (ratio >= 0.5) return "#e8a735";
  return "var(--color-fail, #ff3355)";
}

function nodeColor(ratio: number): string {
  if (ratio >= 1)   return "var(--color-ok, #3dba7e)";
  if (ratio >= 0.5) return "#e8a735";
  if (ratio >= 0)   return "var(--color-fail, #ff3355)";
  return "var(--color-accent, #5d9b94)";   // 결과 없음
}

export function KoreaMap({ nodes, edges, onNodeClick, selfLoops = {} }: Props) {
  /** nodeId → 좌표 맵 */
  const posMap = React.useMemo(() => {
    const m = new Map<number, { x: number; y: number }>();
    nodes.forEach((n) => m.set(n.id, { x: n.geo_x, y: n.geo_y }));
    return m;
  }, [nodes]);

  /** 노드별 최악 결과 비율 (엣지 기준) */
  const nodeRatio = React.useMemo(() => {
    const m = new Map<number, number>();
    edges.forEach((e) => {
      const prev = m.get(e.src_id) ?? Infinity;
      m.set(e.src_id, Math.min(prev, e.ratio));
      const prevD = m.get(e.dst_id) ?? Infinity;
      m.set(e.dst_id, Math.min(prevD, e.ratio));
    });
    return m;
  }, [edges]);

  return (
    <svg
      viewBox="0 0 100 100"
      style={{ width: "100%", height: "100%", display: "block" }}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* ── 본토 윤곽 ── */}
      <path
        d={MAINLAND_PATH}
        fill="rgba(93,155,148,0.06)"
        stroke="var(--color-wire, #2a2a2a)"
        strokeWidth="0.5"
      />

      {/* ── 제주도 ── */}
      <path
        d={JEJU_PATH}
        fill="rgba(93,155,148,0.06)"
        stroke="var(--color-wire, #2a2a2a)"
        strokeWidth="0.4"
      />

      {/* ── 부속 도서 ── */}
      {ISLANDS.map((i) => (
        <circle key={i.label} cx={i.cx} cy={i.cy} r={i.r}
          fill="rgba(93,155,148,0.15)" stroke="var(--color-wire)" strokeWidth="0.3" />
      ))}

      {/* ── 결과 엣지 ── */}
      {edges.map((e) => {
        const src = posMap.get(e.src_id);
        const dst = posMap.get(e.dst_id);
        if (!src || !dst) return null;
        const color = edgeColor(e.ratio);
        const mx = (src.x + dst.x) / 2;
        const my = (src.y + dst.y) / 2 - 3; // 약간 위로 휘어짐
        return (
          <g key={`${e.src_id}-${e.dst_id}`}>
            <path
              d={`M${src.x},${src.y} Q${mx},${my} ${dst.x},${dst.y}`}
              fill="none"
              stroke={color}
              strokeWidth="0.7"
              strokeOpacity="0.85"
            />
            {/* 비율 텍스트 */}
            <text
              x={mx} y={my - 0.8}
              fontSize="2.2" fill={color} textAnchor="middle"
              style={{ fontFamily: "monospace", pointerEvents: "none" }}
            >
              {e.ok}/{e.total}
            </text>
          </g>
        );
      })}

      {/* ── 장비 노드 ── */}
      {nodes.map((n) => {
        const ratio = nodeRatio.has(n.id) ? (nodeRatio.get(n.id) ?? -1) : -1;
        const loop = selfLoops[n.id];
        const color = nodeColor(ratio);
        return (
          <g
            key={n.id}
            onClick={() => onNodeClick?.(n.id)}
            style={{ cursor: onNodeClick ? "pointer" : "default" }}
          >
            <circle
              cx={n.geo_x} cy={n.geo_y} r="2.2"
              fill={color} fillOpacity="0.9"
              stroke="#0a0a0a" strokeWidth="0.4"
            />
            {/* 자체 루프 아이콘 */}
            {loop && (
              <text
                x={n.geo_x + 2.6} y={n.geo_y - 1.5}
                fontSize="2.4"
                fill={loop.ok === loop.total ? "var(--color-ok)" : loop.ok === 0 ? "var(--color-fail)" : "#e8a735"}
                style={{ fontFamily: "monospace", userSelect: "none" }}
              >
                ↺{loop.ok}/{loop.total}
              </text>
            )}
            {/* 장비명 */}
            <text
              x={n.geo_x} y={n.geo_y + 4}
              fontSize="2" fill="var(--color-fog, #555)" textAnchor="middle"
              style={{ fontFamily: "monospace", pointerEvents: "none", userSelect: "none" }}
            >
              {n.label.length > 10 ? n.label.slice(0, 9) + "…" : n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
