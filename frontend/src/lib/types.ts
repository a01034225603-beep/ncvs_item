export type HealthStatus = "ok" | "fail" | "unknown";
export type SessionStatus = "queued" | "running" | "completed" | "cancelled" | "failed";

export interface Device {
  id: number;
  name: string;
  node_id: number;
  ip_address: string;
  udp_port: number;
  tcp_port: number;
  location: string | null;
  enabled: boolean;
}

export interface Health {
  bacs_id: number;
  status: HealthStatus;
  last_checked_at: string | null;
  last_ok_at: string | null;
  last_error: string | null;
  consecutive_fail: number;
}

export interface Session {
  id: number;
  status: SessionStatus;
  device_ids: number[];
  total_pairs: number;
  done_pairs: number;
  ok_pairs: number;
  fail_pairs: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface MatrixCell {
  src_bacs_id: number;
  dst_bacs_id: number;
  status: "ok" | "fail";
  tested_at: string;
  error_message: string | null;
}
