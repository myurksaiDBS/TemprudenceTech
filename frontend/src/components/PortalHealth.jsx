import { AlertTriangle, CheckCircle2, HeartPulse, ShieldAlert, Wrench } from "lucide-react";

const TONE = {
  good: { icon: CheckCircle2, label: "Good", cls: "text-[#1e6b3d]", bar: "bg-[#1e6b3d]" },
  fair: { icon: AlertTriangle, label: "Fair", cls: "text-[#8a5a00]", bar: "bg-[#c48a00]" },
  poor: { icon: ShieldAlert, label: "Needs attention", cls: "text-[var(--tt-red)]", bar: "bg-[var(--tt-red)]" },
};
const toneFor = (score) => (score >= 75 ? "good" : score >= 60 ? "fair" : "poor");

const Ring = ({ score }) => {
  const r = 54, c = 2 * Math.PI * r;
  const color = { good: "#1e6b3d", fair: "#c48a00", poor: "#b03010" }[toneFor(score)];
  return (
    <svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label={`Health score ${score} out of 100`}>
      <circle cx="70" cy="70" r={r} fill="none" stroke="#e3eaf1" strokeWidth="12" />
      <circle cx="70" cy="70" r={r} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} transform="rotate(-90 70 70)" style={{ transition: "stroke-dashoffset 0.8s ease" }} />
      <text x="70" y="68" textAnchor="middle" fontSize="34" fontWeight="700" fill="#002040">{score}</text>
      <text x="70" y="90" textAnchor="middle" fontSize="12" fill="#5b6770">out of 100</text>
    </svg>
  );
};

export const PortalHealth = ({ data }) => {
  if (!data?.overall) return null;
  const o = data.overall;
  return (
    <section className="tt-card p-6 tt-rise" data-testid="portal-health">
      <div className="flex items-center gap-2 tt-eyebrow mb-4"><HeartPulse size={14} /> Health summary</div>
      <div className="grid lg:grid-cols-[auto_1fr_1fr] gap-8 items-start">
        <div className="flex items-center gap-5">
          <Ring score={o.score} />
          <div>
            <div className={`text-2xl font-bold ${TONE[toneFor(o.score)].cls}`} data-testid="portal-health-grade">{o.grade}</div>
            <div className="text-sm text-[var(--tt-navy)] mt-1 max-w-[240px]" data-testid="portal-health-summary">{o.summary}</div>
            <div className="text-xs text-[var(--tt-muted)] mt-2">Based on the latest inventory of {o.computer_count} computer{o.computer_count === 1 ? "" : "s"}</div>
          </div>
        </div>
        <ul className="space-y-4" data-testid="portal-health-categories">
          {data.categories.map((c) => {
            const t = TONE[c.status];
            const Icon = t.icon;
            return (
              <li key={c.key} data-testid={`health-category-${c.key}`}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-[var(--tt-navy)]">{c.name}</span>
                  <span className={`inline-flex items-center gap-1 text-xs font-bold ${t.cls}`}><Icon size={13} /> {t.label}</span>
                </div>
                <div className="h-2 bg-[#eef3f8] rounded mt-1.5"><div className={`h-2 rounded ${t.bar}`} style={{ width: `${c.percent}%`, transition: "width 0.8s ease" }} /></div>
                <div className="text-xs text-[var(--tt-muted)] mt-1">{c.message}</div>
              </li>
            );
          })}
        </ul>
        <div data-testid="portal-health-recommendations">
          <div className="text-sm font-bold text-[var(--tt-blue)] mb-2 flex items-center gap-1.5"><Wrench size={15} /> What we recommend</div>
          {data.recommendations.length === 0 ? (
            <p className="text-sm text-[var(--tt-muted)]">Nothing right now. Keep up the good work.</p>
          ) : (
            <ol className="space-y-2.5">
              {data.recommendations.slice(0, 6).map((r, i) => (
                <li key={r.text} className="text-sm flex gap-2.5" data-testid={`health-rec-${i}`}>
                  <span className="w-5 h-5 shrink-0 rounded-full bg-[var(--tt-blue)] text-white text-[11px] font-bold flex items-center justify-center">{i + 1}</span>
                  <span>
                    <span className="text-[var(--tt-navy)] font-medium">{r.text}</span>
                    <span className="block text-xs text-[var(--tt-muted)]">{r.count} computer{r.count === 1 ? "" : "s"}: {r.computers.slice(0, 4).join(", ")}{r.count > 4 ? "..." : ""}</span>
                  </span>
                </li>
              ))}
            </ol>
          )}
          <p className="text-xs text-[var(--tt-muted)] mt-4">Temprudence Technologies can take care of these for you. Just reach out to your technician.</p>
        </div>
      </div>
    </section>
  );
};

export const HealthPill = ({ score }) => {
  if (score == null) return <span className="text-[var(--tt-muted)]">-</span>;
  const t = TONE[toneFor(score)];
  const Icon = t.icon;
  return <span className={`inline-flex items-center gap-1 text-xs font-bold ${t.cls}`}><Icon size={13} /> {score}/100</span>;
};
