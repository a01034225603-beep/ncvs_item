/**
 * Next.js 루트 레이아웃
 *
 * 역할:
 *   - 모든 페이지를 감싸는 최상위 레이아웃이다.
 *   - ThemeProvider 를 통해 전체 앱에 테마 컨텍스트를 제공한다.
 *   - globals.css 의 CSS 변수 기반 디자인 시스템을 적용한다.
 */
import type { Metadata } from "next";
import { Space_Mono, Manrope, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/lib/theme";
import "./globals.css";

const spaceMono = Space_Mono({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-space-mono",
  display: "swap",
});

const manrope = Manrope({
  weight: ["300", "400", "500", "600", "700", "800"],
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BACS MONITOR // NCVS",
  description: "BACS device health monitoring & cross-test console",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="ko"
      data-theme="dark"
      suppressHydrationWarning
      className={`${spaceMono.variable} ${manrope.variable} ${jetbrains.variable}`}
    >
      <head>
        {/* 페이지 로드 시 깜빡임 없이 저장된 테마 즉시 적용 */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('ncvs_theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}`,
          }}
        />
      </head>
      <body>
        <ThemeProvider>
          <div className="relative z-10 min-h-screen">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  );
}
