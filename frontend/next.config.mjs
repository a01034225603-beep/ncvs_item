const config = {
  // standalone: Windows Portable 패키지용 — Node.js 런타임 내장 번들 생성
  // Docker 빌드에는 영향 없음 (output 옵션을 Docker가 별도 처리하지 않음)
  output: "standalone",
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? "http://backend:8000";
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};
export default config;
