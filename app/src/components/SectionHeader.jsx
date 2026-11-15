export default function SectionHeader({ index, label, title, intro }) {
  return (
    <div className="grid grid-cols-1 gap-6 border-b border-white/10 pb-8 md:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] md:items-end md:gap-12">
      <div>
        <div className="mb-5 flex items-center gap-3">
          <span className="mono-label text-[#0057FF]">{index}</span>
          <span className="h-px w-8 bg-[#0057FF]" aria-hidden="true" />
          <span className="mono-label text-[#F2F2F2]/40">{label}</span>
        </div>
        <h2 className="display text-[clamp(2rem,5.5vw,4.75rem)] text-[#F2F2F2]">{title}</h2>
      </div>
      <p className="max-w-xl text-sm leading-relaxed text-[#F2F2F2]/55 md:justify-self-end">
        {intro}
      </p>
    </div>
  );
}
