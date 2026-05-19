import Link from "next/link";

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Subtle ambient glow */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `
            radial-gradient(ellipse 60% 50% at 30% 20%, rgba(93,155,148,0.06), transparent),
            radial-gradient(ellipse 50% 40% at 70% 80%, rgba(44,201,128,0.04), transparent)
          `,
          pointerEvents: "none",
        }}
      />

      {/* Content */}
      <div style={{ textAlign: "center", position: "relative", maxWidth: 480, padding: "0 24px" }}>
        {/* Eyebrow */}
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.24em",
            textTransform: "uppercase",
            color: "var(--color-fog)",
            marginBottom: 20,
          }}
        >
          Network Cross-Validation System
        </div>

        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(40px, 8vw, 88px)",
            fontWeight: 700,
            letterSpacing: "-0.03em",
            lineHeight: 0.9,
            color: "var(--color-snow)",
            margin: "0 0 20px",
          }}
        >
          BACS
          <br />
          <span style={{ color: "var(--color-accent)" }}>MONITOR</span>
        </h1>

        <p
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 400,
            fontSize: 15,
            color: "var(--color-haze)",
            lineHeight: 1.7,
            margin: "0 auto 36px",
          }}
        >
          BACS 장비 상태를 실시간으로 모니터링하고,{" "}
          <strong style={{ color: "var(--color-snow)", fontWeight: 500 }}>호시험 결과</strong>를
          매트릭스로 시각화합니다.
        </p>

        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <Link
            href="/login"
            style={{
              padding: "11px 28px",
              background: "var(--color-accent)",
              color: "var(--color-bg)",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              textDecoration: "none",
              display: "inline-block",
              transition: "opacity 0.15s",
            }}
          >
            로그인
          </Link>

          <Link
            href="/devices"
            style={{
              padding: "11px 24px",
              background: "none",
              border: "1px solid var(--color-wire)",
              color: "var(--color-haze)",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              textDecoration: "none",
              display: "inline-block",
              transition: "border-color 0.15s, color 0.15s",
            }}
          >
            장비 목록
          </Link>
        </div>
      </div>

      {/* Bottom tag */}
      <div
        style={{
          position: "absolute",
          bottom: 24,
          fontFamily: "var(--font-mono)",
          fontSize: 9,
          letterSpacing: "0.12em",
          color: "var(--color-fog)",
          opacity: 0.6,
        }}
      >
        BACS MONITOR · NCVS v2
      </div>
    </main>
  );
}
