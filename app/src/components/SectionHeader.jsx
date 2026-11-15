export default function SectionHeader({ index, label, title, intro }) {
  return (
    <div className="grid grid-cols-1 gap-6 border-b border-white/10 pb-8 md:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] md:items-end md:gap-12">
      <div>
        <div className="mb-5 flex items-center gap-3">
          <span className="mono-label text-[#38BDF8]">{index}</span>
          <span className="h-px w-8 bg-[#0369A1]" aria-hidden="true" />
          <span className="mono-label text-[#F8FAFC]/40">{label}</span>
        </div>
        <h2 className="display text-[clamp(2rem,5.5vw,4.75rem)] text-[#F8FAFC]">{title}</h2>
      </div>
      <p className="max-w-xl text-sm leading-relaxed text-[#F8FAFC]/55 md:justify-self-end">
        {intro}
      </p>
    </div>
  );
}
