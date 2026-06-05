"use client";
import { useEffect, useState } from "react";
import { Device, DeviceCreate } from "@/lib/types";
import { SIDO_LIST, getSigunguList, getCoord } from "@/lib/korea-districts";

interface Props {
  initial?: Device | null;   // null = 신규 등록, Device = 수정
  onSave: (data: DeviceCreate) => Promise<void>;
  onClose: () => void;
}

const FIELD_STYLE: React.CSSProperties = {
  width: "100%",
  background: "var(--color-bg)",
  border: "1px solid var(--color-edge)",
  borderLeft: "2px solid var(--color-accent)",
  padding: "6px 10px",
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  color: "var(--color-snow)",
  outline: "none",
  boxSizing: "border-box",
};

const LABEL_STYLE: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  letterSpacing: "0.06em",
  color: "var(--color-fog)",
  marginBottom: 4,
  display: "block",
};

export function DeviceFormModal({ initial, onSave, onClose }: Props) {
  const [name, setName]       = useState(initial?.name ?? "");
  const [ip, setIp]           = useState(initial?.ip_address ?? "");
  const [udpPort, setUdpPort] = useState(String(initial?.udp_port ?? 7788));
  const [tcpPort, setTcpPort] = useState(String(initial?.tcp_port ?? 7788));
  const [location, setLoc]    = useState(initial?.location ?? "");
  const [sido, setSido]        = useState(initial?.sido ?? "");
  const [sigungu, setSigungu]  = useState(initial?.sigungu ?? "");
  const [geoX, setGeoX]        = useState<number | null>(initial?.geo_x ?? null);
  const [geoY, setGeoY]        = useState<number | null>(initial?.geo_y ?? null);
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  // 호출시험 전화번호 (숫자·하이픈)
  const [p0Phone, setP0Phone] = useState(initial?.port0_phone ?? "");
  const [p1Phone, setP1Phone] = useState(initial?.port1_phone ?? "");
  const [p2Phone, setP2Phone] = useState(initial?.port2_phone ?? "");
  const [p3Phone, setP3Phone] = useState(initial?.port3_phone ?? "");
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState<string | null>(null);

  // ESC 키로 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  function handleSidoChange(newSido: string) {
    setSido(newSido);
    setSigungu("");
    setGeoX(null);
    setGeoY(null);
    if (newSido) {
      const coord = getCoord(newSido);
      if (coord) { setGeoX(coord.geo_x); setGeoY(coord.geo_y); }
    }
  }

  function handleSigunguChange(newSigungu: string) {
    setSigungu(newSigungu);
    if (sido && newSigungu) {
      const coord = getCoord(sido, newSigungu);
      if (coord) { setGeoX(coord.geo_x); setGeoY(coord.geo_y); }
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !ip.trim()) {
      setError("이름과 IP 주소는 필수입니다.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      // phone 입력값 정규화: 빈 문자열 → null
      const toPhone = (v: string) => v.trim() || null;
      await onSave({
        name: name.trim(),
        ip_address: ip.trim(),
        udp_port: Number(udpPort),
        tcp_port: Number(tcpPort),
        location: location.trim() || null,
        sido: sido || null,
        sigungu: sigungu || null,
        geo_x: geoX,
        geo_y: geoY,
        enabled,
        port0_phone: toPhone(p0Phone),
        port1_phone: toPhone(p1Phone),
        port2_phone: toPhone(p2Phone),
        port3_phone: toPhone(p3Phone),
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  }

  const isEdit = Boolean(initial);

  return (
    /* 오버레이 */
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0,0,0,0.65)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 1000,
      }}
    >
      {/* 패널 — 클릭 버블 차단 */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--color-panel2)",
          border: "1px solid var(--color-wire)",
          width: "100%", maxWidth: 480,
          padding: "28px 28px 24px",
          boxShadow: "0 16px 56px rgba(0,0,0,0.6)",
        }}
      >
        {/* 헤더 */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 18, fontWeight: 700,
              color: "var(--color-snow)", margin: 0,
            }}
          >
            {isEdit ? "장비 수정" : "장비 등록"}
          </h2>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none",
              color: "var(--color-fog)", cursor: "pointer",
              fontFamily: "var(--font-mono)", fontSize: 16,
            }}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* 장비명 */}
          <div>
            <label style={LABEL_STYLE}>장비명 *</label>
            <input value={name} onChange={(e) => setName(e.target.value)} style={FIELD_STYLE} placeholder="BACS-01" required />
          </div>

          {/* IP 주소 */}
          <div>
            <label style={LABEL_STYLE}>IP 주소 *</label>
            <input value={ip} onChange={(e) => setIp(e.target.value)} style={FIELD_STYLE} placeholder="192.168.1.10" required />
          </div>

          {/* 포트 */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={LABEL_STYLE}>UDP 포트</label>
              <input value={udpPort} onChange={(e) => setUdpPort(e.target.value)} style={FIELD_STYLE} type="number" min={1} max={65535} />
            </div>
            <div>
              <label style={LABEL_STYLE}>TCP 포트</label>
              <input value={tcpPort} onChange={(e) => setTcpPort(e.target.value)} style={FIELD_STYLE} type="number" min={1} max={65535} />
            </div>
          </div>

          {/* 위치 (자유 텍스트) */}
          <div>
            <label style={LABEL_STYLE}>위치 설명 (선택)</label>
            <input value={location} onChange={(e) => setLoc(e.target.value)} style={FIELD_STYLE} placeholder="서울 IDC 1F" />
          </div>

          {/* 시/도 선택 */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={LABEL_STYLE}>시/도</label>
              <select
                value={sido}
                onChange={(e) => handleSidoChange(e.target.value)}
                style={{ ...FIELD_STYLE, cursor: "pointer" }}
              >
                <option value="">— 선택 —</option>
                {SIDO_LIST.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label style={LABEL_STYLE}>시/군/구</label>
              <select
                value={sigungu}
                onChange={(e) => handleSigunguChange(e.target.value)}
                disabled={!sido}
                style={{ ...FIELD_STYLE, cursor: sido ? "pointer" : "not-allowed", opacity: sido ? 1 : 0.4 }}
              >
                <option value="">— 선택 —</option>
                {getSigunguList(sido).map((sg) => <option key={sg} value={sg}>{sg}</option>)}
              </select>
            </div>
          </div>

          {/* 좌표 표시 (자동 입력, 확인용) */}
          {(geoX !== null || geoY !== null) && (
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 9,
              color: "var(--color-fog)", letterSpacing: "0.06em",
              paddingLeft: 4,
            }}>
              좌표 → X {geoX?.toFixed(1)} / Y {geoY?.toFixed(1)}  (지도 자동 설정됨)
            </div>
          )}

          {/* 호출시험 전화번호 ─ TX(발신) */}
          <div style={{ borderTop: "1px solid var(--color-wire)", paddingTop: 12 }}>
            <div style={{ ...LABEL_STYLE, color: "var(--color-accent)", marginBottom: 8 }}>호출시험 전화번호 (숫자·하이픈만 허용)</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={LABEL_STYLE}>Port 0 — TX 발신</label>
                <input
                  value={p0Phone}
                  onChange={(e) => setP0Phone(e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="예) 800-1200"
                  pattern="[\d\-]*"
                  title="숫자와 하이픈만 입력 가능"
                />
              </div>
              <div>
                <label style={LABEL_STYLE}>Port 1 — TX 발신</label>
                <input
                  value={p1Phone}
                  onChange={(e) => setP1Phone(e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="예) 800-1201"
                  pattern="[\d\-]*"
                  title="숫자와 하이픈만 입력 가능"
                />
              </div>
              <div>
                <label style={LABEL_STYLE}>Port 2 — RX 착신</label>
                <input
                  value={p2Phone}
                  onChange={(e) => setP2Phone(e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="예) 800-1202"
                  pattern="[\d\-]*"
                  title="숫자와 하이픈만 입력 가능"
                />
              </div>
              <div>
                <label style={LABEL_STYLE}>Port 3 — RX 착신</label>
                <input
                  value={p3Phone}
                  onChange={(e) => setP3Phone(e.target.value)}
                  style={FIELD_STYLE}
                  placeholder="예) 800-1203"
                  pattern="[\d\-]*"
                  title="숫자와 하이픈만 입력 가능"
                />
              </div>
            </div>
          </div>

          {/* 활성 여부 */}
          <label
            style={{
              display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
              fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--color-haze)",
              userSelect: "none",
            }}
          >
            <span
              onClick={() => setEnabled((v) => !v)}
              style={{
                width: 13, height: 13,
                border: `1px solid ${enabled ? "var(--color-accent)" : "var(--color-wire)"}`,
                background: enabled ? "rgba(93,155,148,0.2)" : "transparent",
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                fontSize: 8, color: "var(--color-accent)", flexShrink: 0,
              }}
            >
              {enabled && "✓"}
            </span>
            활성 (헬스체크 포함)
          </label>

          {/* 에러 */}
          {error && (
            <div style={{
              borderLeft: "2px solid var(--color-fail)",
              paddingLeft: 10,
              fontFamily: "var(--font-mono)", fontSize: 11,
              color: "var(--color-fail)", lineHeight: 1.5,
            }}>
              {error}
            </div>
          )}

          {/* 버튼 */}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
            <button
              type="button" onClick={onClose}
              style={{
                padding: "8px 20px", background: "none",
                border: "1px solid var(--color-wire)",
                fontFamily: "var(--font-mono)", fontSize: 11,
                color: "var(--color-fog)", cursor: "pointer",
              }}
            >
              취소
            </button>
            <button
              type="submit" disabled={saving}
              style={{
                padding: "8px 24px",
                background: saving ? "var(--color-edge)" : "var(--color-accent)",
                border: "none",
                fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
                color: saving ? "var(--color-fog)" : "#fff",
                cursor: saving ? "not-allowed" : "pointer",
              }}
            >
              {saving ? "저장 중…" : isEdit ? "수정 완료" : "등록"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
