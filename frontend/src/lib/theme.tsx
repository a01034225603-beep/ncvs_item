/**
 * 다크/라이트 테마 컨텍스트 모듈
 *
 * 역할:
 *   ThemeProvider: 앱 전체에 테마 상태를 공급하는 React Context Provider.
 *   useTheme():    현재 테마와 토글 함수를 반환하는 커스텀 훅.
 *
 *   - 초기값: localStorage('ncvs_theme') 에서 복원, 없으면 'dark'
 *   - 테마 변경 시 document.documentElement[data-theme] 속성을 갱신하여
 *     globals.css 의 CSS 변수가 자동으로 전환된다.
 */
"use client";
import { createContext, useContext, useEffect, useState } from "react";

type Theme = "dark" | "light";

const ThemeContext = createContext<{ theme: Theme; toggle: () => void }>({
  theme: "dark",
  toggle: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");

  /* localStorage에서 저장된 테마 복원 */
  useEffect(() => {
    const saved = localStorage.getItem("ncvs_theme") as Theme | null;
    if (saved === "light" || saved === "dark") setTheme(saved);
  }, []);

  /* html[data-theme] 업데이트 + 저장 */
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ncvs_theme", theme);
  }, [theme]);

  function toggle() {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
