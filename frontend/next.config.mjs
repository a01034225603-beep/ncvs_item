const config = {
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL ?? "http://backend:8000";
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};
export default config;
