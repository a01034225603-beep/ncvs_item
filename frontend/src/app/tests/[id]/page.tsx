"use client";

import { use, useEffect, useState } from "react";

import { TestProgress } from "@/components/TestProgress";
import { api } from "@/lib/api";
import { Session } from "@/lib/types";

export default function TestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: idParam } = use(params);
  const id = Number(idParam);
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const s = await api.session(id);
        if (active) setSession(s);
      } catch {
        /* ignore */
      }
    }
    poll();
    const t = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, [id]);

  if (!session) return <main>로딩…</main>;
  return (
    <main>
      <h1>Test Session #{session.id}</h1>
      <TestProgress s={session} />
      {session.status === "running" && (
        <button onClick={() => api.cancelSession(id)} style={{ marginTop: 12 }}>
          취소
        </button>
      )}
    </main>
  );
}
