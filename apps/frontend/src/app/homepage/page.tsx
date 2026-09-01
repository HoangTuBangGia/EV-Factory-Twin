import Link from "next/link";

const capabilities = [
  {
    number: "01",
    title: "Realtime factory twin",
    description: "Theo dõi vị trí, trạng thái, pin và nhiệm vụ của đội AMR trên bản đồ nhà máy 3D.",
  },
  {
    number: "02",
    title: "Layout what-if",
    description: "Thay đổi station, route và vùng tắc nghẽn rồi chạy SimPy để đo tác động trước khi áp dụng.",
  },
  {
    number: "03",
    title: "Human approval",
    description: "Designer đề xuất, Monitor đánh giá và phê duyệt trước khi cấu hình đi tới runtime mô phỏng.",
  },
] as const;

export default function Homepage() {
  return (
    <main className="landing-page">
      <header className="landing-header">
        <Link className="landing-brand" href="/homepage" aria-label="RAV-11 Factory Twin homepage">
          <span className="brand-mark">R11</span>
          <span><strong>RAV-11</strong><small>FACTORY TWIN</small></span>
        </Link>
        <nav className="landing-nav" aria-label="Homepage navigation">
          <a href="#capabilities">Năng lực</a>
          <a href="#workflow">Quy trình</a>
          <Link className="landing-login" href="/login">Đăng nhập</Link>
        </nav>
      </header>

      <section className="landing-hero" aria-labelledby="landing-title">
        <div className="landing-hero-copy">
          <p className="landing-kicker"><i/> EV battery intralogistics</p>
          <h1 id="landing-title">Quan sát nhà máy.<br/><span>Thử nghiệm trước khi áp dụng.</span></h1>
          <p className="landing-lead">
            Digital Twin hợp nhất đội robot, layout nhà máy và dữ liệu vận hành trong một không gian mô phỏng an toàn.
          </p>
          <div className="landing-actions">
            <Link className="landing-primary" href="/login">Truy cập hệ thống <span aria-hidden="true">→</span></Link>
            <a className="landing-secondary" href="#capabilities">Khám phá nền tảng</a>
          </div>
         <div className="landing-trust" aria-label="Platform technologies">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
        </div>

        <div className="landing-twin" aria-label="Minh họa bản sao số nhà máy">
          <div className="landing-twin-head">
            <span><i/> DIGITAL TWIN ONLINE</span><small>120 × 40 M</small>
          </div>
          <div className="landing-factory-grid">
            <div className="landing-zone warehouse"><b>WAREHOUSE</b><span>Inbound logistics</span></div>
            <div className="landing-zone production"><b>PRODUCTION</b><span>Battery assembly</span></div>
            <div className="landing-zone shipping"><b>SHIPPING / QC</b><span>Outbound</span></div>
            <svg viewBox="0 0 720 300" role="img" aria-label="AMR transport route across three factory zones">
              <path d="M70 210 C180 210 190 92 310 92 S470 220 650 135"/>
              <circle cx="84" cy="205" r="8"/><circle cx="315" cy="93" r="8"/><circle cx="646" cy="137" r="8"/>
            </svg>
            <span className="landing-robot robot-one">AMR-01<small>82%</small></span>
            <span className="landing-robot robot-two">AMR-02<small>67%</small></span>
          </div>
          <div className="landing-twin-foot"><span>5 AMR ACTIVE</span><span>24.8 TASKS/H</span><span>18 MS UPDATE</span></div>
        </div>
      </section>

      <section className="landing-capabilities" id="capabilities" aria-labelledby="capabilities-title">
        <div className="landing-section-intro">
          <p className="landing-kicker">Nền tảng vận hành</p>
          <h2 id="capabilities-title">Từ dữ liệu realtime đến quyết định có kiểm chứng.</h2>
        </div>
        <div className="landing-capability-grid">
          {capabilities.map((capability) => (
            <article key={capability.number}>
              <span>{capability.number}</span>
              <h3>{capability.title}</h3>
              <p>{capability.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-workflow" id="workflow" aria-labelledby="workflow-title">
        <div>
          <p className="landing-kicker">Controlled workflow</p>
          <h2 id="workflow-title">Không thay đổi mù quáng.</h2>
          <p>Mọi phương án được mô phỏng, đo lường và phê duyệt bởi con người trước khi đồng bộ vào Digital Twin runtime.</p>
        </div>
        <ol>
          <li><span>01</span>CREATE</li><li><span>02</span>SIMULATE</li><li><span>03</span>COMPARE</li>
          <li><span>04</span>APPROVE</li><li><span>05</span>MONITOR</li>
        </ol>
      </section>

      <footer className="landing-footer">
        <div><strong>RAV-11 FACTORY TWIN</strong><span>Digital Twin for AMR-based EV battery intralogistics</span></div>
        <Link href="/login">Bắt đầu phiên làm việc →</Link>
      </footer>
    </main>
  );
}
