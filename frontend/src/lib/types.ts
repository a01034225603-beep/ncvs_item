export type HealthStatus = "online" | "offline" | "unknown";
export type SessionStatus = "queued" | "running" | "completed" | "cancelled" | "failed";
export type PairStatus = "pending" | "running" | "ok" | "fail" | "skipped";

/** SSE stream 이벤트 — 페어 한 개의 현재 상태 */
export interface PairState {
  id: number;
  src_bacs_id: number;
  dst_bacs_id: number;
  status: PairStatus;
  error_message: string | null;
}

export interface Device {
  id: number;
  name: string;
  ip_address: string;
  udp_port: number;
  tcp_port: number;
  location: string | null;
  enabled: boolean;
  // 호출시험용 전화번호 (Port0·1 = TX 발신, Port2·3 = RX 착신)
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

/** stream SSE 이벤트 — Session + 전체 페어 상태 목록 */
export interface SessionWithPairs extends Session {
  pairs: PairState[];
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

/**
 * 패킷 이벤트 — BACS_Control.md §1.3 기준으로 파싱된 단일 TCP 패킷.
 * /api/tests/{id}/packets SSE 스트림에서 수신한다.
 */
export interface PacketParsed {
  pkt_type?: string;
  data_len?: number;
  node_id?: number;
  msg_type?: string;
  msg_data_len?: number;
  // CONNECT_LEVEL
  level?: string;
  // ERROR_RPT
  err_code?: number;
  err_code_desc?: string;
  // CALL_REQ
  port?: number;
  phone_len?: number;
  phone?: string;
  // CALL_RPT
  result_code?: string;
  result_desc?: string;
  // 파싱 실패
  parse_error?: string;
  [key: string]: unknown;
}

export interface PacketEvent {
  session_id: number;
  pair_label: string;
  /** TX = 서버→BACS 송신, RX = BACS→서버 수신 */
  direction: "TX" | "RX";
  /** 단계 레이블 (예: "CONNECT_REQ", "STARTUP_RPT", "CALL_REQ[Port=0]") */
  step: string;
  /** raw hex (예: "01 10 09 00 ...") */
  hex_dump: string;
  /** BACS_Control.md 기준 파싱 결과 */
  parsed: PacketParsed;
  /** ISO 8601 UTC 타임스탬프 */
  ts: string;
}
