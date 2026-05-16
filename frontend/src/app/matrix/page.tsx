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
    <main>
      <h1>Cross-test 결과 매트릭스</h1>
      <p style={{ fontSize: 12, color: "#666" }}>
        행 = 송신(src), 열 = 수신(dst). 녹색 ok / 빨강 fail / 회색 미테스트.
      </p>
      <Matrix devices={devices} cells={cells} />
    </main>
  );
}
