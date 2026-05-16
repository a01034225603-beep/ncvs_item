import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>NCVS BACS Monitor</h1>
      <p>
        <Link href="/login">Login</Link>
      </p>
    </main>
  );
}
