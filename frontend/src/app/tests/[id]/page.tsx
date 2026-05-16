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

  if (!session) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-16 text-center text-slate-500">
        로딩…
      </main>
    );
  }
  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">
        Test Session #{session.id}
      </h1>
      <div className="mt-6">
        <TestProgress s={session} />
      </div>
      {session.status === "running" && (
        <button
          onClick={() => api.cancelSession(id)}
          className="mt-4 rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
        >
          취소
        </button>
      )}
    </main>
  );
}
