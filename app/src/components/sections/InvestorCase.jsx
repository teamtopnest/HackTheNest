import SectionHeader from '@/components/SectionHeader';

const METRICS = [
  { value: '1,240', label: 'Recorded hours', detail: 'Closed sessions, 10 pilot users' },
  { value: '2.6M', label: 'Decoded tokens', detail: 'Phrase-level output logged' },
  { value: '3', label: 'Institutional LOIs', detail: 'Research and clinical sites' },
  { value: '38', unit: 'ms', label: 'Median latency', detail: 'Signal in to text out' },
];

const THESIS = [
  {
    id: 'A',
    title: 'The sensor is already solved',
    body: 'G.tech ships a validated, open 8-channel board at consumer price. We do not fund a hardware science project — we build the decoding layer on top of it.',
  },
  {
    id: 'B',
    title: 'Decoders got cheap',
    body: 'Feature-level classification plus a language model constraint gives readable output on a phone-class processor. No supercomputer, no data centre.',
  },
  {
    id: 'C',
    title: 'The demand is here',
    body: 'ALS, locked-in patients, and hands-busy industrial work all need text entry without a keyboard. Eight channels is enough to serve them today.',
  },
];

export default function InvestorCase() {
  return (
    <section id="case" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="06"
          label="For investors & partners"
          title={<>A decoding layer,<br className="hidden md:block" /> not a hardware bet.</>}
          intro="EEG Neurotec is the software and signal layer between an affordable G.tech headset and the written word. We are raising a seed round to take a working eight-channel prototype into clinical pilots."
        />

        <div className="mt-12 grid grid-cols-2 gap-px bg-white/10 lg:grid-cols-4">
          {METRICS.map((metric) => (
            <div key={metric.label} className="bg-[#050505] p-6">
              <div className="flex items-baseline gap-1">
                <span className="display text-[clamp(1.8rem,4vw,2.8rem)] text-[#F2F2F2]">{metric.value}</span>
                {metric.unit ? <span className="mono text-xs text-[#0057FF]">{metric.unit}</span> : null}
              </div>
              <span className="mono-label mt-3 block text-[#F2F2F2]/55">{metric.label}</span>
              <span className="mt-1 block text-xs leading-relaxed text-[#F2F2F2]/35">{metric.detail}</span>
            </div>
          ))}
        </div>

        <div className="mt-px grid grid-cols-1 gap-px bg-white/10 lg:grid-cols-3">
          {THESIS.map((item) => (
            <div key={item.id} className="group bg-[#050505] p-6 transition-colors duration-300 hover:bg-[#080808] sm:p-8">
              <div className="flex items-center gap-3">
                <span className="grid h-7 w-7 place-items-center border border-[#C5A059] mono-label text-[0.625rem] text-[#C5A059]">
                  {item.id}
                </span>
                <span className="mono-label text-[#F2F2F2]/30">Thesis</span>
              </div>
              <h3 className="mt-6 font-heading text-xl font-semibold leading-tight tracking-tight text-[#F2F2F2]">
                {item.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#F2F2F2]/55">{item.body}</p>
            </div>
          ))}
        </div>

        <p className="mono-label mt-4 text-[0.5625rem] text-[#F2F2F2]/25">
          Illustrative figures for template purposes — replace with your own verified data
        </p>
      </div>
    </section>
  );
}