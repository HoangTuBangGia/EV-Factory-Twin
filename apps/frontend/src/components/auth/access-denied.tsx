import Link from "next/link";

export function AccessDenied() {
  return (
    <section className="panel access-denied" role="alert">
      <div className="eyebrow">403 Forbidden</div>
      <h2>Administrator access required</h2>
      <p>This account cannot manage users or view the administrative audit log.</p>
      <Link className="button" href="/">Return to operations</Link>
    </section>
  );
}
