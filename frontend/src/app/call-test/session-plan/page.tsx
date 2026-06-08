"use client";
/** 세션 계획 상세(/call-test/session-plan) - 실행 예정 페어 전체 목록과 포트별 전화번호 사전 확인. */
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { api, getToken } from "@/lib/api";
import { Device, Health, Scenario } from "@/lib/types";

/* ─── 헬스 dot ────────────────────────────────────────────────── */
function HealthDot({ status }: { status: Health["status"] | undefined }) {
  const color =
    status === "online"  ? "var(--color-ok)"  :
    status === "offline" ? "var(--color-fail)" :
    "var(--color-wire)";
  return (
    <span
      title={status ?? "unknown"}
      style={{
        display: "inline-block",
        width: 7, height: 7, borderRadius: "50%",
        background: color, flexShrink: 0,
        boxShadow: status === "online" ? "0 0 5px var(--color-ok)" : "none",
      }}
    />
  );
}

/* ─── 전화번호 셀 ──────────────────────────────────────────────── */
function PhoneCell({
  phone,
  portLabel,
  role,
}: {
  phone: string | null | undefined;
  portLabel: string;
  role: "tx" | "rx";
}) {
  const color = role === "tx" ? "var(--color-ok)" : "var(--color-warn)";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: role === "tx" ? "flex-start" : "flex-end", gap: 2 }}>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: "0.1em", color: "var(--color-fog)", textTransform: "uppercase" }}>
        {portLabel}
      </span>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700, color: phone ? color : "var(--color-wire)", letterSpacing: "0.04em" }}>
        {phone ?? "미설정"}
      </span>
    </div>
  );
}

/* ─── 페어 상세 카드 ────────────────────────────────────────────── */
function PairCard({
  index,
  src,
  dst,
  srcHealth,
  dstHealth,
}: {
  index: number;
  src: Device;
  dst: Device;
  srcHealth?: Health["status"];
  dstHealth?: Health["status"];
}) {
  const hasOffline = srcHealth === "offline" || dstHealth === "offline";
  const missingPhone =
    !src.port0_phone || !src.port1_phone ||
    !dst.port2_phone || !dst.port3_phone;

  return (
    <div
      style={{
        border: `1px solid ${hasOffline ? "var(--color-fail)33" : "var(--color-edge)"}`,
        background: "var(--color-bg2)",
        overflow: "hidden",
      }}
    >
      {/* 카드 헤더 — 페어 번호 + 장비 정보 */}
      <div
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "8px 14px",
          background: "var(--color-bg)",
          borderBottom: "1px solid var(--color-edge)",
          gap: 12, flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)", minWidth: 26 }}>
            #{String(index + 1).padStart(2, "0")}
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-accent)" }}>
            TCP:7788
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <HealthDot status={srcHealth} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--color-snow)", fontWeight: 600 }}>
              {src.name}
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)" }}>
              {src.ip_address}
            </span>
          </div>
          <span style={{ color: "var(--color-fog)", fontSize: 10 }}>→</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-accent)", letterSpacing: "0.06em" }}>접속</span>
          <span style={{ color: "var(--color-fog)", fontSize: 10 }}>→</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <HealthDot status={dstHealth} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--color-snow)", fontWeight: 600 }}>
              {dst.name}
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fog)" }}>
              {dst.ip_address}
            </span>
          </div>
        </div>
        {hasOffline && (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-fail)", letterSpacing: "0.06em" }}>⚠ OFFLINE</span>
        )}
        {missingPhone && !hasOffline && (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--color-warn)", letterSpacing: "0.06em" }}>⚠ 전화번호 미설정</span>
        )}
      </div>

      {/* 포트별 호출 계획 — 2개 행 (Port0→Port2, Port1→Port3) */}
      <div style={{ padding: "10px 14px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: "0.12em", color: "var(--color-fog)", marginBottom: 2 }}>
          CALL PLAN  (BACS_Control.md §1.3.3 CALL_REQ)
        </div>
        {[
          { txPort: 0, rxPort: 2, txPhone: src.port0_phone, rxPhone: dst.port2_phone },
          { txPort: 1, rxPort: 3, txPhone: src.port1_phone, rxPhone: dst.port3_phone },
        ].map(({ txPort, rxPort, txPhone, rxPhone }) => (
          <div
            key={txPort}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 36px auto 36px 1fr",
              alignItems: "center",
              gap: 6, padding: "7px 10px",
              background: "var(--color-bg)",
              border: "1px solid var(--color-edge)",
            }}
          >
            <div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--color-fog)", marginBottom: 2 }}>{src.name}</div>
              <PhoneCell phone={txPhone} portLabel={`Port ${txPort} TX`} role="tx" />
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 7, color: "var(--color-fog)", marginBottom: 2 }}>REQ</div>
              <div style={{ color: "var(--color-accent)", fontSize: 14, lineHeight: 1 }}>→</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 8, fontWeight: 700,
                letterSpacing: "0.08em", color: "var(--color-accent)",
                background: "rgba(93,155,148,0.12)",
                padding: "2px 7px",
                border: "1px solid rgba(93,155,148,0.3)",
                display: "block", whiteSpace: "nowrap",
              }}>
                CALL_REQ<br />Port={txPort}
              </span>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 7, color: "var(--color-fog)", marginBottom: 2 }}>RPT</div>
              <div style={{ color: "var(--color-warn)", fontSize: 14, lineHeight: 1 }}>→</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--color-fog)", marginBottom: 2 }}>{dst.name}</div>
              <PhoneCell phone={rxPhone} portLabel={`Port ${rxPort} RX`} role="rx" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── 세션 계획 본문 ─────────────────────────────────────────── */
function SessionPlanContent() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const scenarioId   = Number(searchParams.get("scenario_id"));

  const [scenario,  setScenario]  = useState<Scenario | null>(null);
  const [devices,   setDevices]   = useState<Device[]>([]);
  const [healthMap, setHealthMap] = useState<Map<number, Health["status"]>>(new Map());
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    if (!scenarioId) { router.replace("/");      return; }

    Promise.all([api.scenarios(), api.devices(), api.health()])
      .then(([scenarios, devs, healths]) => {
        setScenario(scenarios.find((s) => s.id === scenarioId) ?? null);
        setDevices(devs);
        setHealthMap(new Map(healths.map((h) => [h.bacs_id, h.status])));
      })
      .finally(() => setLoading(false));
  }, [router, scenarioId]);

  if (loading) {
    return (
      <>
        <TopBar />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100vh - 48px)", fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--color-fog)" }}>
          로딩 중…
        </div>
      </>
    );
  }

  if (!scenario) {
    return (
      <>
        <TopBar />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "calc(100vh - 48px)", flexDirection: "column", gap: 12 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--color-fog)" }}>시나리오를 찾을 수 없습니다.</div>
          <button onClick={() => window.close()} style={{ padding: "8px 20px", background: "none", border: "1px solid var(--color-wire)", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-haze)", cursor: "pointer" }}>
            닫기
          </button>
        </div>
      </>
    );
  }

  // 페어 목록 계산 (session_service.py 와 동일 로직)
  const deviceMap = new Map(devices.map((d) => [d.id, d]));
  const pairs: Array<{ src: Device; dst: Device }> = [];
  for (const srcId of scenario.sender_device_ids) {
    for (const dstId of scenario.receiver_device_ids) {
      if (srcId === dstId) continue;
      const src = deviceMap.get(srcId);
      const dst = deviceMap.get(dstId);
      if (src && dst) pairs.push({ src, dst });
    }
  }

  const totalCalls = pairs.length * 2;
  const hasAnyOffline = pairs.some(
    ({ src, dst }) => healthMap.get(src.id) === "offline" || healthMap.get(dst.id) === "offline",
  );
  const hasAnyMissingPhone = pairs.some(
    ({ src, dst }) => !src.port0_phone || !src.port1_phone || !dst.port2_phone || !dst.port3_phone,
  );

  return (
    <>
      <TopBar />
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "36px 24px 80px" }}>

        {/* 닫기 버튼 */}
        <button
          onClick={() => window.close()}
          style={{
            background: "none", border: "none", padding: 0,
            fontFamily: "var(--font-mono)", fontSize: 11,
            color: "var(--color-fog)", cursor: "pointer",
            letterSpacing: "0.06em", marginBottom: 24,
          }}
        >
          ✕ 닫기
        </button>

        {/* 헤더 */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--color-fog)", marginBottom: 6 }}>
            세션 계획  ·  BACS_Control.md §1.3
          </div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: "var(--color-snow)", margin: 0, letterSpacing: "-0.02em" }}>
            {scenario.name}
          </h1>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-fog)", marginTop: 8 }}>
            {pairs.length}개 페어 · {totalCalls}회 호출
            <span style={{ marginLeft: 12, fontSize: 9, color: "var(--color-wire)" }}>
              (§1.3.1 TCP 접속 → §1.3.3 CALL_REQ → §1.3.4 CALL_RPT)
            </span>
          </div>
        </div>

        {/* 경고 메시지 */}
        {(hasAnyOffline || hasAnyMissingPhone) && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 24 }}>
            {hasAnyOffline && (
              <div style={{ padding: "10px 16px", border: "1px solid var(--color-fail)", background: "rgba(255,80,80,0.05)", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-fail)", display: "flex", alignItems: "center", gap: 8 }}>
                <span>⚠</span> OFFLINE 장비가 포함된 세션은 실패로 처리될 수 있습니다.
              </div>
            )}
            {hasAnyMissingPhone && (
              <div style={{ padding: "10px 16px", border: "1px solid var(--color-warn)", background: "rgba(217,119,6,0.05)", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-warn)", display: "flex", alignItems: "center", gap: 8 }}>
                <span>⚠</span> 전화번호 미설정 장비가 있습니다. 장비 설정 화면에서 Port0·1 (TX) / Port2·3 (RX) 번호를 입력해주세요.
              </div>
            )}
          </div>
        )}

        {/* 페어 카드 목록 */}
        {pairs.length === 0 ? (
          <div style={{ padding: "32px", textAlign: "center", border: "1px solid var(--color-edge)", background: "var(--color-bg2)", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-fail)" }}>
            유효한 페어 없음 — 발신·착신 장비가 동일하거나 데이터 미설정
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {pairs.map(({ src, dst }, i) => (
              <PairCard
                key={`${src.id}-${dst.id}`}
                index={i}
                src={src}
                dst={dst}
                srcHealth={healthMap.get(src.id)}
                dstHealth={healthMap.get(dst.id)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

export default function SessionPlanPage() {
  return (
    <Suspense>
      <SessionPlanContent />
    </Suspense>
  );
}
