"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { api, getToken } from "@/lib/api";
import { Device, Health } from "@/lib/types";

/* ─── 세션 쌍 타입 ──────────────────────────────────────────── */
interface Pair { id: string; s: number; r: number }
let pairSeq = 0;
function mkPairId() { return `p${++pairSeq}`; }

/* ─── Vizing 엣지 컬러링 알고리즘 ───────────────────────────────
 * 방향 엣지 독립 처리: 같은 라운드에서 각 노드는
 * 송신자(sender) 1번 + 수신자(receiver) 1번만 허용
 * 입력: Pair[] / 출력: 라운드별 Pair 그룹
 */
interface Round { pairs: Pair[] }

function computeRounds(pairs: Pair[]): Round[] {
  const rounds: { senders: Set<number>; receivers: Set<number>; pairs: Pair[] }[] = [];
  for (const pair of pairs) {
    let placed = false;
    for (const round of rounds) {
      // 해당 라운드에서 이미 같은 송신자 혹은 같은 수신자가 있으면 배정 불가
      if (!round.senders.has(pair.s) && !round.receivers.has(pair.r)) {
        round.senders.add(pair.s);
        round.receivers.add(pair.r);
        round.pairs.push(pair);
        placed = true;
        break;
      }
    }
    if (!placed) {
      rounds.push({
        senders:   new Set([pair.s]),
        receivers: new Set([pair.r]),
        pairs:     [pair],
      });
    }
  }
  return rounds.map((r) => ({ pairs: r.pairs }));
}

/* 라운드별 강조 색상 (순환) */
const ROUND_COLORS = [
  "#5d9b94", "#e0a96d", "#8b8fce", "#c97b84",
  "#6bbc7a", "#d4ae5c", "#7ab8de", "#b07ac9",
];

/* ─── 드래그 소스 태그 ────────────────────────────────────────── */
/* 헬스 상태 색상 */
function healthColor(status: Health["status"] | undefined): string {
  if (status === "online")  return "var(--color-ok)";
  if (status === "offline") return "var(--color-fail)";
  return "var(--color-wire)";
}

function DeviceTag({
  device,
  onRemove,
  draggable = false,
  onDragStart,
  dimmed = false,
  healthStatus,
}: {
  device: Device;
  onRemove?: () => void;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
  dimmed?: boolean;
  healthStatus?: Health["status"];
}) {
  return (
    <div
      draggable={draggable}
      onDragStart={onDragStart}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        border: "1px solid var(--color-wire)",
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: dimmed ? "var(--color-fog)" : "var(--color-haze)",
        background: dimmed ? "transparent" : "var(--color-bg2)",
        cursor: draggable ? "grab" : "default",
        userSelect: "none",
        opacity: dimmed ? 0.4 : 1,
        borderRadius: 2,
      }}
    >
      {/* 헬스 상태 점 */}
      <span
        title={healthStatus ?? "unknown"}
        style={{
          width: 6, height: 6, borderRadius: "50%",
          background: healthColor(healthStatus),
          flexShrink: 0,
          boxShadow: healthStatus === "online" ? `0 0 4px var(--color-ok)` : "none",
        }}
      />
      {device.name}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          style={{
            background: "none", border: "none", padding: "0 0 0 4px",
            cursor: "pointer", color: "var(--color-fog)", fontSize: 13, lineHeight: 1,
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}

/* ─── 메인 페이지 ─────────────────────────────────────────────── */
export default function ScenarioBuilderPage() {
  const router = useRouter();
  const [devices, setDevices]       = useState<Device[]>([]);
  const [search, setSearch]         = useState("");
  const [group, setGroup]           = useState<number[]>([]);      // 그룹에 추가된 장비 id
  const [pairs, setPairs]           = useState<Pair[]>([]);        // 활성 세션 쌍
  const [scenarioName, setScenarioName] = useState("");
  const [saving, setSaving]         = useState(false);
  const [toast, setToast]           = useState<{ msg: string; ok: boolean } | null>(null);
  const [over, setOver]             = useState(false);
  const [healthMap, setHealthMap]   = useState<Map<number, Health["status"]>>(new Map());
  const dragId                      = useRef<number | null>(null);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    api.devices().then(setDevices).catch((e) => {
      setToast({ msg: e instanceof Error ? e.message : "장비 목록을 불러오지 못했습니다.", ok: false });
    });
    /* UDP 헬스체크 결과 로드 (bacs_id = device.id) */
    api.health().then((list) => {
      setHealthMap(new Map(list.map((h) => [h.bacs_id, h.status])));
    }).catch((e) => {
      setToast({ msg: e instanceof Error ? e.message : "헬스 정보를 불러오지 못했습니다.", ok: false });
    });
  }, []);

  const deviceMap = new Map(devices.map((d) => [d.id, d]));

  const visible = devices.filter((d) => {
    const q = search.toLowerCase();
    return !q || d.name.toLowerCase().includes(q);
  });

  /* 드래그 시작 */
  function handleDragStart(e: React.DragEvent, id: number) {
    dragId.current = id;
    e.dataTransfer.setData("deviceId", String(id));
    e.dataTransfer.effectAllowed = "copy";
  }

  /* 그룹에 장비 추가 → 양방향 쌍 자동 생성 */
  function addToGroup(id: number) {
    if (group.includes(id)) return;
    // 기존 그룹 멤버와 양방향 쌍 추가
    const newPairs: Pair[] = group.flatMap((existing) => [
      { id: mkPairId(), s: existing, r: id },
      { id: mkPairId(), s: id,       r: existing },
    ]);
    setGroup((prev) => [...prev, id]);
    setPairs((prev) => [...prev, ...newPairs]);
  }

  /* 그룹에서 장비 제거 → 관련 쌍 모두 삭제 */
  function removeFromGroup(id: number) {
    setGroup((prev) => prev.filter((x) => x !== id));
    setPairs((prev) => prev.filter((p) => p.s !== id && p.r !== id));
  }

  /* 개별 쌍 삭제 */
  function removePair(pairId: string) {
    setPairs((prev) => prev.filter((p) => p.id !== pairId));
  }

  /* 초기화 */
  function handleReset() {
    setGroup([]);
    setPairs([]);
    setScenarioName("");
  }

  /* 토스트 */
  function showToast(msg: string, ok: boolean) {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  }

  /* 등록 */
  async function handleRegister() {
    if (!scenarioName.trim()) { showToast("시나리오 이름을 입력하세요.", false); return; }
    if (pairs.length === 0)   { showToast("세션 쌍을 1개 이상 구성하세요.", false); return; }
    setSaving(true);
    try {
      // 활성 쌍에서 유니크 발신/착신 추출
      const senderIds   = [...new Set(pairs.map((p) => p.s))];
      const receiverIds = [...new Set(pairs.map((p) => p.r))];
      await api.createScenario({
        name: scenarioName.trim(),
        sender_device_ids: senderIds,
        receiver_device_ids: receiverIds,
      });
      showToast("시나리오가 등록되었습니다.", true);
      handleReset();
    } catch {
      showToast("등록 중 오류가 발생했습니다.", false);
    } finally {
      setSaving(false);
    }
  }

  /* ─── Vizing 라운드 계산 (pairs 변경 시마다 재계산) ─── */
  const rounds = useMemo(() => computeRounds(pairs), [pairs]);

  /* ─── 매트릭스 셀 룩업: "송신ID-수신ID" → 라운드 인덱스 ─── */
  const pairRoundMap = useMemo(() => {
    const m = new Map<string, number>();
    rounds.forEach((round, idx) => {
      round.pairs.forEach((p) => m.set(`${p.s}-${p.r}`, idx));
    });
    return m;
  }, [rounds]);

  const panelStyle: React.CSSProperties = {
    background: "var(--color-panel, #141414)",
    border: "1px solid var(--color-edge)",
    borderRadius: 4,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  };

  const panelHeader: React.CSSProperties = {
    padding: "10px 14px 8px",
    borderBottom: "1px solid var(--color-edge)",
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    letterSpacing: "0.12em",
    textTransform: "uppercase" as const,
    color: "var(--color-fog)",
    background: "var(--color-bg2)",
    flexShrink: 0,
  };

  return (
    <>
      <TopBar />

      {/* 토스트 알림 */}
      {toast && (
        <div
          style={{
            position: "fixed", top: 60, right: 20, zIndex: 9999,
            padding: "10px 20px",
            background: toast.ok ? "var(--color-ok)" : "var(--color-fail)",
            color: "#000",
            fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600,
            borderRadius: 3, boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
          }}
        >
          {toast.msg}
        </div>
      )}

      <div
        style={{
          height: "calc(100vh - 48px)",
          display: "flex", flexDirection: "column",
          padding: "16px 20px 12px", gap: 12,
          boxSizing: "border-box",
        }}
      >
        {/* ── 상단: 시나리오 이름 입력 ── */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              fontFamily: "var(--font-mono)", fontSize: 9,
              letterSpacing: "0.14em", textTransform: "uppercase",
              color: "var(--color-fog)", whiteSpace: "nowrap",
            }}
          >
            시나리오 이름
          </div>
          <input
            value={scenarioName}
            onChange={(e) => setScenarioName(e.target.value)}
            placeholder="예: 전국 관제 시나리오"
            maxLength={128}
            style={{
              flex: 1, maxWidth: 480,
              background: "var(--color-bg2)",
              border: "1px solid var(--color-edge)",
              borderLeft: "2px solid var(--color-accent)",
              padding: "8px 14px",
              fontFamily: "var(--font-mono)", fontSize: 13,
              color: "var(--color-snow)", outline: "none",
            }}
          />
          <div style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--color-fog)" }}>
            {pairs.length > 0 && (
              <span>총 <span style={{ color: "var(--color-accent)" }}>{pairs.length}</span>개 세션 쌍</span>
            )}
          </div>
        </div>

        {/* ── 3-패널 본문 ── */}
        <div
          style={{
            flex: 1, display: "grid",
            gridTemplateColumns: "220px 1fr 260px",
            gap: 10, minHeight: 0,
          }}
        >
          {/* ── 왼쪽: BACS 장비 목록 ── */}
          <div style={panelStyle}>
            <div style={panelHeader}>BACS 시스템 목록</div>
            <div style={{ padding: "8px 10px", borderBottom: "1px solid var(--color-edge)", flexShrink: 0 }}>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="장비 검색..."
                style={{
                  width: "100%", background: "transparent",
                  border: "1px solid var(--color-wire)",
                  padding: "5px 10px",
                  fontFamily: "var(--font-mono)", fontSize: 11,
                  color: "var(--color-snow)", outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px", display: "flex", flexDirection: "column", gap: 4 }}>
              {visible.length === 0 ? (
                <div style={{ color: "var(--color-fog)", fontFamily: "var(--font-mono)", fontSize: 10, textAlign: "center", marginTop: 20 }}>
                  장비 없음
                </div>
              ) : (
                visible.map((d) => (
                  <DeviceTag
                    key={d.id}
                    device={d}
                    draggable
                    dimmed={group.includes(d.id)}
                    healthStatus={healthMap.get(d.id)}
                    onDragStart={(e) => handleDragStart(e, d.id)}
                  />
                ))
              )}
            </div>
            <div style={{ padding: "6px 10px", borderTop: "1px solid var(--color-edge)", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)", flexShrink: 0 }}>
              {devices.length}개 장비 · 드래그하여 배치
            </div>
          </div>

          {/* ── 가운데: 세션 그룹 드롭 존 ── */}
          <div style={panelStyle}>
            <div style={panelHeader}>세션 그룹</div>
            <div
              onDragOver={(e) => { e.preventDefault(); setOver(true); }}
              onDragLeave={() => setOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setOver(false);
                const id = Number(e.dataTransfer.getData("deviceId"));
                if (id) addToGroup(id);
              }}
              style={{
                flex: 1,
                margin: 12,
                border: `1px dashed ${over ? "var(--color-accent)" : "var(--color-wire)"}`,
                borderRadius: 4,
                padding: "14px 14px",
                background: over ? "rgba(93,155,148,0.06)" : "transparent",
                transition: "border-color 0.15s, background 0.15s",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              {group.length === 0 ? (
                <div
                  style={{
                    flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
                    flexDirection: "column", gap: 8,
                  }}
                >
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-fog)", textAlign: "center", lineHeight: 1.8 }}>
                    장비를 드래그하여<br />그룹에 추가하세요<br />
                    <span style={{ fontSize: 9, color: "var(--color-edge)" }}>양방향 세션 쌍이 자동 생성됩니다</span>
                  </div>
                </div>
              ) : (
                <>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.1em", color: "var(--color-accent)", marginBottom: 4 }}>
                    그룹 장비 ({group.length}개)
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {group.map((id) => {
                      const d = deviceMap.get(id);
                      if (!d) return null;
                      return (
                        <DeviceTag
                          key={id}
                          device={d}
                          onRemove={() => removeFromGroup(id)}
                        />
                      );
                    })}
                  </div>
                  <div
                    style={{
                      marginTop: "auto",
                      padding: "8px 10px",
                      background: "var(--color-bg2)",
                      border: "1px solid var(--color-edge)",
                      borderRadius: 3,
                      fontFamily: "var(--font-mono)",
                      fontSize: 9,
                      color: "var(--color-fog)",
                      lineHeight: 1.7,
                    }}
                  >
                    장비 {group.length}개 → 최대{" "}
                    <span style={{ color: "var(--color-accent)" }}>
                      {group.length * (group.length - 1)}
                    </span>
                    개 양방향 쌍 가능
                    <br />
                    오른쪽에서 불필요한 쌍만 개별 삭제 가능
                  </div>
                </>
              )}
            </div>
          </div>

          {/* ── 오른쪽: 세션 매핑 정보 ── */}
          <div style={panelStyle}>
            <div style={panelHeader}>세션 매핑 정보</div>
            <div style={{ flex: 1, overflowY: "auto", padding: "8px 12px" }}>
              {pairs.length === 0 ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--color-fog)", textAlign: "center", marginTop: 30, lineHeight: 1.9 }}>
                  그룹에 장비를 추가하면<br />세션 쌍이 자동으로<br />생성됩니다
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  {pairs.map((p) => {
                    const src = deviceMap.get(p.s);
                    const dst = deviceMap.get(p.r);
                    return (
                      <div
                        key={p.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 5,
                          padding: "4px 6px",
                          background: "var(--color-bg2)",
                          borderLeft: "2px solid var(--color-accent)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 10,
                          color: "var(--color-haze)",
                        }}
                      >
                        <span style={{ color: "var(--color-ok)", fontSize: 9 }}>{`#${p.s}`}</span>
                        <span style={{ color: "var(--color-fog)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 60 }}>
                          {src?.name ?? `ID${p.s}`}
                        </span>
                        <span style={{ color: "var(--color-fog)", flexShrink: 0 }}>→</span>
                        <span style={{ color: "var(--color-warn)", fontSize: 9 }}>{`#${p.r}`}</span>
                        <span style={{ color: "var(--color-fog)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 60 }}>
                          {dst?.name ?? `ID${p.r}`}
                        </span>
                        {/* 개별 쌍 삭제 버튼 */}
                        <button
                          onClick={() => removePair(p.id)}
                          title="이 쌍 삭제"
                          style={{
                            background: "none", border: "none",
                            padding: "0 2px", cursor: "pointer",
                            color: "var(--color-fog)", fontSize: 13,
                            lineHeight: 1, flexShrink: 0,
                            opacity: 0.6,
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
                          onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.6")}
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            <div style={{ padding: "6px 12px", borderTop: "1px solid var(--color-edge)", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)", flexShrink: 0 }}>
              활성 쌍:{" "}
              <span style={{ color: "var(--color-accent)" }}>{pairs.length}</span>
              개
            </div>
          </div>
        </div>

        {/* ── 하단: 발신×착신 매트릭스 (셀 색상 = 라운드) ── */}
        {group.length >= 2 && (
          <div
            style={{
              flexShrink: 0,
              background: "var(--color-panel, #141414)",
              border: "1px solid var(--color-edge)",
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            {/* ── 헤더 바 ── */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "7px 14px",
                borderBottom: "1px solid var(--color-edge)",
                background: "var(--color-bg2)",
              }}
            >
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--color-fog)", flex: 1 }}>
                호출 시험 매트릭스 &mdash; 셀 색상 = 라운드
              </span>
              {/* 라운드 색상 범례 */}
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                {rounds.map((_, idx) => {
                  const c = ROUND_COLORS[idx % ROUND_COLORS.length];
                  return (
                    <span
                      key={idx}
                      style={{
                        display: "inline-flex", alignItems: "center", gap: 4,
                        fontFamily: "var(--font-mono)", fontSize: 9, color: c,
                      }}
                    >
                      <span style={{ width: 8, height: 8, borderRadius: 1, background: c, display: "inline-block" }} />
                      R{idx + 1}
                    </span>
                  );
                })}
              </div>
              {/* 요약 */}
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)", whiteSpace: "nowrap" }}>
                <span style={{ color: "var(--color-accent)", fontWeight: 700 }}>{rounds.length}</span> 라운드
                &nbsp;/&nbsp;
                <span style={{ color: "var(--color-haze)", fontWeight: 700 }}>{pairs.length}</span> 세션
              </span>
            </div>

            {/* ── 매트릭스 테이블 ── */}
            <div style={{ overflowX: "auto", padding: "10px 14px 12px" }}>
              {/* 그리드: 1(빈코너) + group.length(착신 헤더 열) */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: `80px repeat(${group.length}, minmax(56px, 1fr))`,
                  gap: 2,
                  minWidth: group.length * 58 + 82,
                }}
              >
                {/* ─ 코너 셀 (빈칸 + 착신 레이블) ─ */}
                <div
                  style={{
                    fontFamily: "var(--font-mono)", fontSize: 8,
                    color: "var(--color-fog)", textAlign: "center",
                    padding: "2px 0 6px",
                    borderBottom: "1px solid var(--color-edge)",
                    display: "flex", alignItems: "flex-end", justifyContent: "center",
                  }}
                >
                  <span>송신↓ / 착신→</span>
                </div>

                {/* ─ 착신 장비 헤더 열 ─ */}
                {group.map((rId) => {
                  const d = deviceMap.get(rId);
                  return (
                    <div
                      key={rId}
                      style={{
                        fontFamily: "var(--font-mono)", fontSize: 9,
                        color: "var(--color-warn)",
                        textAlign: "center", padding: "2px 2px 6px",
                        borderBottom: "1px solid var(--color-edge)",
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}
                      title={d?.name ?? `ID${rId}`}
                    >
                      {d?.name ?? `ID${rId}`}
                    </div>
                  );
                })}

                {/* ─ 행: 송신 장비 ─ */}
                {group.map((sId) => {
                  const sd = deviceMap.get(sId);
                  return (
                    <>
                      {/* 송신 장비 이름 셀 */}
                      <div
                        key={`row-${sId}`}
                        style={{
                          fontFamily: "var(--font-mono)", fontSize: 9,
                          color: "var(--color-ok)",
                          display: "flex", alignItems: "center",
                          padding: "0 6px 0 0",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                          height: 32,
                        }}
                        title={sd?.name ?? `ID${sId}`}
                      >
                        {sd?.name ?? `ID${sId}`}
                      </div>

                      {/* 착신 장비별 셀 */}
                      {group.map((rId) => {
                        /* 자기 자신 대각선 */
                        if (sId === rId) {
                          return (
                            <div
                              key={`${sId}-${rId}`}
                              style={{
                                height: 32,
                                background: "rgba(255,255,255,0.03)",
                                border: "1px solid var(--color-edge)",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontFamily: "var(--font-mono)", fontSize: 10,
                                color: "var(--color-wire)",
                              }}
                            >
                              ─
                            </div>
                          );
                        }

                        const roundIdx = pairRoundMap.get(`${sId}-${rId}`);

                        /* 쌍이 없는 셀 */
                        if (roundIdx === undefined) {
                          return (
                            <div
                              key={`${sId}-${rId}`}
                              style={{
                                height: 32,
                                border: "1px solid var(--color-edge)",
                                background: "transparent",
                              }}
                            />
                          );
                        }

                        /* 쌍이 있는 셀 — 라운드 색상으로 채움 */
                        const color = ROUND_COLORS[roundIdx % ROUND_COLORS.length];
                        const sName = sd?.name ?? `ID${sId}`;
                        const rName = deviceMap.get(rId)?.name ?? `ID${rId}`;
                        return (
                          <div
                            key={`${sId}-${rId}`}
                            title={`R${roundIdx + 1}: ${sName} → ${rName}`}
                            style={{
                              height: 32,
                              background: `${color}28`,
                              border: `1px solid ${color}88`,
                              display: "flex", alignItems: "center", justifyContent: "center",
                              fontFamily: "var(--font-mono)", fontSize: 9,
                              color: color, fontWeight: 700,
                              cursor: "default",
                            }}
                          >
                            R{roundIdx + 1}
                          </div>
                        );
                      })}
                    </>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── 하단: 버튼 ── */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexShrink: 0 }}>
          <button
            onClick={handleReset}
            style={{
              padding: "10px 24px", background: "none",
              border: "1px solid var(--color-wire)",
              fontFamily: "var(--font-mono)", fontSize: 11,
              letterSpacing: "0.06em", color: "var(--color-fog)",
              cursor: "pointer",
            }}
          >
            초기화
          </button>
          <button
            onClick={handleRegister}
            disabled={saving}
            style={{
              padding: "10px 32px",
              background: saving ? "var(--color-wire)" : "rgba(93,155,148,0.15)",
              border: `1px solid ${saving ? "var(--color-wire)" : "var(--color-accent)"}`,
              fontFamily: "var(--font-mono)", fontSize: 12,
              letterSpacing: "0.08em",
              color: saving ? "var(--color-fog)" : "var(--color-accent)",
              cursor: saving ? "not-allowed" : "pointer",
              fontWeight: 600, transition: "all 0.15s",
            }}
          >
            {saving ? "등록 중..." : "등록하기"}
          </button>
        </div>
      </div>
    </>
  );
}
