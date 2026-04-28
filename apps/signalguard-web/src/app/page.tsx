export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <p className="eyebrow mb-2">cstack</p>
        <h1 className="text-22 font-semibold">cstack web initialising</h1>
        <p className="mt-2 text-fg-tertiary text-13">
          Visit{" "}
          <a className="text-brand underline" href="/dashboard">
            /dashboard
          </a>{" "}
          to begin.
        </p>
      </div>
    </main>
  );
}
