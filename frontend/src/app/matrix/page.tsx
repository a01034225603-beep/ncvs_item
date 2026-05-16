"use client";

import { useEffect, useState } from "react";

import { Matrix } from "@/components/Matrix";
import { api } from "@/lib/api";
import { Device, MatrixCell } from "@/lib/types";

export default function MatrixPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [cells, setCells] = useState<MatrixCell[]>([]);

  useEffect(() => {
    api.devices().then(async (ds) => {
      setDevices(ds);
      if (ds.length > 0) setCells(await api.matrix(ds.map((d) => d.id)));
    });
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">
        Cross-test 결과 매트릭스
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        행 = 송신(src), 열 = 수신(dst).{" "}
        <span className="inline-block h-2 w-2 rounded-sm bg-emerald-500 align-middle" /> ok
        <span className="mx-1">·</span>
        <span className="inline-block h-2 w-2 rounded-sm bg-red-500 align-middle" /> fail
        <span className="mx-1">·</span>
        <span className="inline-block h-2 w-2 rounded-sm bg-slate-200 align-middle" /> 미테스트
      </p>
      <div className="mt-6 overflow-auto">
        <Matrix devices={devices} cells={cells} />
      </div>
    </main>
  );
}
