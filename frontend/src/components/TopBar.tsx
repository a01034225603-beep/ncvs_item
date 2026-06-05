"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";
import { useTheme } from "@/lib/theme";

const NAV = [
  { href: "/",        label: "홈" },
  { href: "/devices", label: "장비 목록" },
  { href: "/tests",   label: "시나리오 등록" },
  { href: "/matrix",  label: "호시험 결과" },
];

export function TopBar() {
  const pathname = usePathname();
  const router   = useRouter();
  const { theme, toggle } = useTheme();
  const isLight = theme === "light";

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        height: 44,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        background: isLight ? "rgba(242,245,249,0.96)" : "rgba(11,14,24,0.96)",
        backdropFilter: "blur(8px)",
        borderBottom: "1px solid var(--color-edge)",
      }}
    >
      {/* 왼쪽: 브랜드 + 네비 */}
      <div style={{ display: "flex", alignItems: "center", height: "100%" }}>
        <Link
          href="/"
          style={{
            fontFamily: "var(--font-mono)",
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: "0.18em",
            color: "var(--color-snow)",
            textDecoration: "none",
            marginRight: 24,
          }}
        >
          NCVS
        </Link>

        <div style={{ width: 1, height: 16, background: "var(--color-edge)", marginRight: 8 }} />

        <nav style={{ display: "flex", height: "100%" }}>
          {NAV.map(({ href, label }) => {
            const active = href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "0 14px",
                  height: "100%",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  letterSpacing: "0.06em",
                  color: active ? "var(--color-snow)" : "var(--color-haze)",
                  textDecoration: "none",
                  borderBottom: active
                    ? "2px solid var(--color-accent)"
                    : "2px solid transparent",
                  transition: "color 0.12s",
                }}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* 오른쪽: 상태 + 테마 + 로그아웃 */}
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        {/* ONLINE 표시 */}
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.1em",
            color: "var(--color-ok)",
          }}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: "50%",
              background: "var(--color-ok)",
              display: "inline-block",
              animation: "pulse 2s ease-in-out infinite",
            }}
          />
          ONLINE
        </span>

        <div style={{ width: 1, height: 14, background: "var(--color-edge)" }} />

        {/* 테마 토글 */}
        <button
          onClick={toggle}
          title={isLight ? "다크 모드로 전환" : "라이트 모드로 전환"}
          style={{
            background: "none",
            border: "1px solid var(--color-wire)",
            borderRadius: 2,
            padding: "3px 10px",
            cursor: "pointer",
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.08em",
            color: "var(--color-haze)",
            transition: "border-color 0.12s, color 0.12s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--color-accent)";
            e.currentTarget.style.color = "var(--color-accent)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--color-wire)";
            e.currentTarget.style.color = "var(--color-haze)";
          }}
        >
          {isLight ? "다크 모드" : "라이트 모드"}
        </button>

        <div style={{ width: 1, height: 14, background: "var(--color-edge)" }} />

        {/* 로그아웃 */}
        <button
          onClick={logout}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.08em",
            color: "var(--color-haze)",
            padding: 0,
            transition: "color 0.12s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "var(--color-fail)")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-haze)")}
        >
          로그아웃
        </button>
      </div>
    </header>
  );
}
