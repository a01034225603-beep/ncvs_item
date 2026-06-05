const TOKEN_KEY = "ncvs_token";

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  devices: () => request<import("./types").Device[]>("/devices"),
  health: () => request<import("./types").Health[]>("/devices/health"),
  refreshHealth: () => request<{ status: string }>("/health/refresh", { method: "POST" }),
  // ── 호출시험 ──
  // POST /tests — scenario_id 기반으로 시험 세션 생성
  startTest: (scenario_id: number) =>
    request<import("./types").Session>("/tests", {
      method: "POST",
      body: JSON.stringify({ scenario_id }),
    }),
  session: (id: number) => request<import("./types").Session>(`/tests/${id}`),
  cancelSession: (id: number) =>
    request<{ status: string }>(`/tests/${id}/cancel`, { method: "POST" }),
  matrix: (deviceIds: number[]) => {
    const qs = deviceIds.map((id) => `device_ids=${id}`).join("&");
    return request<import("./types").MatrixCell[]>(`/pair-matrix?${qs}`);
  },

  // ── 장비 CRUD ──
  createDevice: (body: import("./types").DeviceCreate) =>
    request<import("./types").Device>("/devices", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateDevice: (id: number, body: Partial<import("./types").DeviceCreate>) =>
    request<import("./types").Device>(`/devices/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteDevice: async (id: number): Promise<void> => {
    const token = getToken();
    const res = await fetch(`/api/devices/${id}`, {
      method: "DELETE",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  },

  // ── 시나리오 CRUD ──
  scenarios: () => request<import("./types").Scenario[]>("/scenarios"),
  createScenario: (body: import("./types").ScenarioCreate) =>
    request<import("./types").Scenario>("/scenarios", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteScenario: (id: number) =>
    fetch(`/api/scenarios/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    }),

  // ── 시나리오별 최신 세션 조회 — 홈 화면 "이전 결과 보기" 용
  latestSessionByScenario: async (scenarioId: number): Promise<import("./types").Session | null> => {
    const list = await request<import("./types").Session[]>(`/tests?scenario_id=${scenarioId}`);
    return list.length > 0 ? list[0] : null;
  },

};
