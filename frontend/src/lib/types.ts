export type HealthStatus = "online" | "offline" | "unknown";
export type SessionStatus = "queued" | "running" | "completed" | "cancelled" | "failed";
export type PairStatus = "pending" | "running" | "ok" | "fail" | "skipped";

export interface Device {
  id: number;
  name: string;
  ip_address: string;
  udp_port: number;
  tcp_port: number;
  location: string | null;
  enabled: boolean;
  // migration 0008 — 지도 위치 정보
  sido: string | null;
  sigungu: string | null;
  geo_x: number | null;
  geo_y: number | null;
  // 포트별 전화번호 (0·1 = 발신TX, 2·3 = 착신RX)
  port0_phone: string | null;
  port1_phone: string | null;
  port2_phone: string | null;
  port3_phone: string | null;
}

export interface DeviceCreate {
  name: string;
  ip_address: string;
  udp_port?: number;
  tcp_port?: number;
  location?: string | null;
  enabled?: boolean;
  sido?: string | null;
  sigungu?: string | null;
  geo_x?: number | null;
  geo_y?: number | null;
  port0_phone?: string | null;
  port1_phone?: string | null;
  port2_phone?: string | null;
  port3_phone?: string | null;
}

export interface Health {
  bacs_id: number;
  status: HealthStatus;
  last_checked_at: string | null;
  last_ok_at: string | null;
  last_error: string | null;
}

export interface Session {
  id: number;
  scenario_id: number | null;
  status: SessionStatus;
  device_ids: number[];
  total_pairs: number;
  done_pairs: number;
  ok_pairs: number;
  fail_pairs: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface PairStateItem {
  id: number;
  src_bacs_id: number;
  dst_bacs_id: number;
  status: PairStatus;
  error_message: string | null;
}

export interface SessionWithPairs extends Session {
  pairs: PairStateItem[];
}

/** SSE 패킷 이벤트 — 호출시험 중 TX/RX 패킷 실시간 스트림 */
export interface PacketEvent {
  session_id: number;
  pair_label: string;
  direction: string;   // "TX" | "RX"
  step: string;        // e.g. "CONNECT_REQ", "STARTUP_RPT"
  hex_dump: string;    // 공백 구분 hex 문자열
  parsed: Record<string, unknown>;
  ts: string;          // ISO 8601
}

export interface Scenario {
  id: number;
  name: string;
  sender_device_ids: number[];
  receiver_device_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  name: string;
  sender_device_ids: number[];
  receiver_device_ids: number[];
}

export interface MatrixCell {
  src_bacs_id: number;
  dst_bacs_id: number;
  status: "ok" | "fail";
  tested_at: string;
  error_message: string | null;
}
