import { useEffect, useState } from 'react';
import SectionHeader from '@/components/SectionHeader';

const THOUGHT =
  'THE FUTURE OF COMMUNICATION IS NON-VERBAL. EIGHT CHANNELS OF CORTICAL ACTIVITY BECOME CLEAN, EDITABLE TEXT.';

const STATS = [
  { value: '38', unit: 'ms', label: 'End-to-end latency' },
  { value: '96.4', unit: '%', label: 'Word accuracy' },
  { value: '120', unit: 'wpm', label: 'Decoded throughput' },
];

function RawSignal() {
  const bars = Array.from({ length: 96 }, (_, i) => {
    const h = 18 + Math.abs(Math.sin(i * 0.7) * 30) + Math.abs(Math.cos(i * 0.31) * 22);
    return Math.min(100, h);
  });

  return (
    <div className="relative h-24 overflow-hidden border-b border-white/10 bg-[#050505]">
      <div className="absolute inset-0 flex items-end gap-[3px] px-3 pb-3 opacity-90">
        {bars.map((h, i) => (
          <span
            key={i}
            className="flex-1 bg-[#0057FF]"
            style={{ height: `${h}%`, opacity: 0.35 + (i % 5) * 0.12 }}
          />
        ))}
      </div>
      <div className="absolute inset-x-0 top-2 flex justify-between px-3">
        <span className="mono-label text-[0.5625rem] text-[#F2F2F2]/40">Raw · 8 ch · 250 hz</span>
        <span className="mono-label text-[0.5625rem] text-[#00FF41]">streaming</span>
      </div>
    </div>
  );
}

export default function ConversionStream() {
  const [typed, setTyped] = useState('');
  const [runId, setRunId] = useState(0);

  useEffect(() => {
    setTyped('');
    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      setTyped(THOUGHT.slice(0, i));
      if (i >= THOUGHT.length) clearInterval(timer);
    }, 32);
    return () => clearInterval(timer);
  }, [runId]);

  return (
    <section id="stream" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="signal-grid pointer-events-none absolute inset-0 opacity-60" aria-hidden="true" />
      <div className="relative mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="03"
          label="The conversion stream"
          title={<>Signal in.<br className="hidden md:block" /> Sentence out.</>}
          intro="A frozen decoder runs on the device itself: band-power features are classified against a language model, then emitted as plain text into any field you choose."
        />

        <div className="mt-12 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.9fr)]">
          <div className="flex flex-col border border-white/10">
            {STATS.map((stat) => (
              <div key={stat.label} className="border-b border-white/10 px-6 py-7 last:border-b-0">
                <div className="flex items-baseline gap-1.5">
                  <span className="display text-[clamp(2.2rem,5vw,3.2rem)] text-[#F2F2F2]">{stat.value}</span>
                  <span className="mono text-sm text-[#0057FF]">{stat.unit}</span>
                </div>
                <span className="mono-label mt-2 block text-[#F2F2F2]/40">{stat.label}</span>
              </div>
            ))}
          </div>

          <div className="flex flex-col border border-white/10 bg-[#080808]">
            <RawSignal />

            <div className="flex min-h-[220px] flex-col justify-between p-6 sm:p-8">
              <div>
                <div className="mb-4 flex items-center gap-2">
                  <span className="live-dot h-1.5 w-1.5 bg-[#00FF41]" aria-hidden="true" />
                  <span className="mono-label text-[#F2F2F2]/40">Decoded text · local model</span>
                </div>
                <p className="mono text-[clamp(0.95rem,1.9vw,1.35rem)] leading-relaxed tracking-tight text-[#F2F2F2]">
                  {typed}
                  <span className="caret ml-0.5 inline-block h-[1.1em] w-[0.5em] translate-y-[0.15em] bg-[#0057FF]" aria-hidden="true" />
                </p>
              </div>

              <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-5">
                <span className="mono-label text-[#F2F2F2]/30">Decoder v2.4 · on-device · no cloud upload</span>
                <button
                  type="button"
                  onClick={() => setRunId((n) => n + 1)}
                  className="focus-ring border border-[#F2F2F2]/25 px-5 py-2.5 mono-label text-[#F2F2F2] transition-colors duration-300 hover:border-[#0057FF] hover:bg-[#0057FF] hover:text-white"
                >
                  Re-run decode
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}