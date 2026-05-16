export const metadata = { title: "NCVS BACS Monitor" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body style={{ fontFamily: "system-ui", margin: 0, padding: 16 }}>{children}</body>
    </html>
  );
}
