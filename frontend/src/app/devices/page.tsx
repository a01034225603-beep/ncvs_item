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
    <main>
      <h1>BACS 장비</h1>
      <div style={{ marginBottom: 12 }}>
        <button onClick={() => api.refreshHealth().then(loadHealth)}>
          Refresh Health
        </button>
        <button onClick={startTest} style={{ marginLeft: 8 }}>
          선택 장비 Cross-test 시작 ({selected.size})
        </button>
      </div>
      <DeviceTable
        devices={devices}
        health={health}
        selected={selected}
        onToggle={toggle}
      />
    </main>
  );
}
