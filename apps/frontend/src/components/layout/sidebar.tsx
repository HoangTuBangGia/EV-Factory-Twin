import Link from "next/link";

const links = [["Overview", "/"], ["Factory", "/factory"], ["Fleet", "/fleet"], ["Tasks", "/tasks"], ["Analytics", "/analytics"], ["Scenarios", "/scenarios"]];

export function Sidebar() {
  return <aside className="sidebar"><div className="brand"><div className="brand-mark">R11</div><div><strong>RAV-11</strong><span>FACTORY TWIN</span></div></div><nav className="nav">{links.map(([label, href]) => <Link key={href} href={href}>{label}</Link>)}</nav><div className="sidebar-foot">SIMULATION ENVIRONMENT<br/>v0.1.0 · MOCK</div></aside>;
}
