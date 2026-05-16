import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold tracking-tight">NCVS BACS Monitor</h1>
      <p className="mt-4 text-slate-600">
        BACS 장비 헬스 체크와 cross-test 모니터링 콘솔.
      </p>
      <div className="mt-8 flex gap-3">
        <Link
          href="/login"
          className="inline-flex items-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          로그인
        </Link>
        <Link
          href="/devices"
          className="inline-flex items-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          장비 대시보드
        </Link>
      </div>
    </main>
  );
}
