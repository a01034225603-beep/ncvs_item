"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DeviceTable } from "@/components/DeviceTable";
import { api, getToken } from "@/lib/api";
import { Device, Health } from "@/lib/types";

export default function DevicesPage() {
  const router = useRouter();
  const [devices, setDevices] = useState<Device[]>([]);
  const [health, setHealth] = useState<Map<number, Health>>(new Map());
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
  }, [router]);

  const loadHealth = useCallback(async () => {
    const rows = await api.health();
    setHealth(new Map(rows.map((r) => [r.bacs_id, r])));
  }, []);

  useEffect(() => {
    api.devices().then(setDevices);
    loadHealth();
    const t = setInterval(loadHealth, 3000);
    return () => clearInterval(t);
  }, [loadHealth]);

  function toggle(id: number) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function startTest() {
    if (selected.size < 2) {
      alert("2개 이상 선택하세요");
      return;
    }
    const session = await api.startTest([...selected]);
    router.push(`/tests/${session.id}`);
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">BACS 장비</h1>
          <p className="mt-1 text-sm text-slate-500">
            상태는 3초마다 갱신됩니다. 2개 이상 선택 후 cross-test를 시작하세요.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => api.refreshHealth().then(loadHealth)}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Refresh Health
          </button>
          <button
            onClick={startTest}
            disabled={selected.size < 2}
            className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            Cross-test 시작 ({selected.size})
          </button>
        </div>
      </header>
      <div className="mt-6">
        <DeviceTable
          devices={devices}
          health={health}
          selected={selected}
          onToggle={toggle}
        />
      </div>
    </main>
  );
}
