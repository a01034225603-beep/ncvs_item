"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]   = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [dots, setDots]     = useState("");

  useEffect(() => {
    if (!loading) { setDots(""); return; }
    const t = setInterval(() => setDots((d) => (d.length >= 3 ? "" : d + ".")), 380);
    return () => clearInterval(t);
  }, [loading]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await api.login(username, password);
      setToken(access_token);
      router.push("/");
    } catch {
      setError("인증 정보가 올바르지 않습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      {/* Ambient */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 60% 50% at 50% 40%, rgba(93,155,148,0.06), transparent)",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          position: "relative",
          width: 340,
          background: "var(--color-panel)",
          border: "1px solid var(--color-edge)",
          padding: "36px 32px",
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--color-accent)",
              marginBottom: 8,
            }}
          >
            BACS Monitor
          </div>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 20,
              fontWeight: 700,
              color: "var(--color-snow)",
              margin: 0,
              letterSpacing: "-0.01em",
            }}
          >
            운영자 로그인
          </h1>
        </div>

        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Error */}
          {error && (
            <div
              style={{
                padding: "9px 12px",
                background: "rgba(229,72,77,0.08)",
                border: "1px solid rgba(229,72,77,0.3)",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                letterSpacing: "0.02em",
                color: "var(--color-fail)",
              }}
            >
              {error}
            </div>
          )}

          {/* 운영자 ID */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label
              htmlFor="uid"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--color-fog)",
              }}
            >
              운영자 ID
            </label>
            <input
              id="uid"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-edge)",
                borderLeft: "2px solid var(--color-accent)",
                padding: "9px 12px",
                fontFamily: "var(--font-mono)",
                fontSize: 13,
                color: "var(--color-snow)",
                outline: "none",
                width: "100%",
                transition: "border-color 0.12s",
              }}
            />
          </div>

          {/* 비밀번호 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label
              htmlFor="pwd"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--color-fog)",
              }}
            >
              비밀번호
            </label>
            <input
              id="pwd"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-edge)",
                borderLeft: "2px solid var(--color-accent)",
                padding: "9px 12px",
                fontFamily: "var(--font-mono)",
                fontSize: 13,
                color: "var(--color-snow)",
                outline: "none",
                width: "100%",
                transition: "border-color 0.12s",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 4,
              width: "100%",
              background: loading ? "var(--color-aclo)" : "var(--color-accent)",
              color: "#fff",
              border: "none",
              padding: "11px 12px",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              cursor: loading ? "not-allowed" : "pointer",
              transition: "background 0.18s",
            }}
          >
            {loading ? `로그인 중${dots}` : "로그인"}
          </button>
        </form>
      </div>
    </main>
  );
}
