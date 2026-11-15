import { useState } from 'react';
import SectionHeader from '@/components/SectionHeader';

const CHANNELS = [
  { id: 'Fp1', region: 'Left frontal pole', band: 'Theta', uv: 18.4, impedance: 3.1, snr: 22.6, seed: 1 },
  { id: 'Fp2', region: 'Right frontal pole', band: 'Beta', uv: 14.9, impedance: 2.8, snr: 24.1, seed: 2 },
  { id: 'C3', region: 'Left motor cortex', band: 'Mu', uv: 26.2, impedance: 2.2, snr: 31.4, seed: 3 },
  { id: 'C4', region: 'Right motor cortex', band: 'Mu', uv: 24.7, impedance: 2.4, snr: 30.2, seed: 4 },
  { id: 'P7', region: 'Left parietal', band: 'Alpha', uv: 11.3, impedance: 3.6, snr: 19.8, seed: 5 },
  { id: 'P8', region: 'Right parietal', band: 'Alpha', uv: 12.6, impedance: 3.4, snr: 20.5, seed: 6 },
  { id: 'O1', region: 'Left occipital', band: 'Alpha', uv: 9.8, impedance: 3.9, snr: 17.2, seed: 7 },
  { id: 'O2', region: 'Right occipital', band: 'Alpha', uv: 10.4, impedance: 3.7, snr: 18.4, seed: 8 },
];

function wavePath(seed, width = 240, height = 40, points = 72) {
  let d = '';
  for (let i = 0; i <= points; i += 1) {
    const x = (i / points) * width;
    const t = i / points;
    const y =
      height / 2 +
      Math.sin(t * 19 + seed) * height * 0.2 +
      Math.sin(t * 43 + seed * 2.3) * height * 0.12 +
      Math.sin(t * 7 + seed) * height * 0.08;
    d += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)} `;
  }
  return d;
}

export default function ChannelTopology() {
  const [activeId, setActiveId] = useState('C3');
  const active = CHANNELS.find((c) => c.id === activeId) ?? CHANNELS[0];

  return (
    <section id="channels" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="02"
          label="The eight-channel topology"
          title={<>Eight nodes.<br className="hidden md:block" /> One sentence.</>}
          intro="A standard 10-20 montage covers the frontal, motor and parietal language areas — the smallest headset that still hears a full phrase."
        />

        <div className="mt-12 grid grid-cols-1 gap-px border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
          {CHANNELS.map((channel) => {
            const isActive = channel.id === activeId;
            return (
              <button
                key={channel.id}
                type="button"
                onClick={() => setActiveId(channel.id)}
                aria-pressed={isActive}
                className={`focus-ring group relative flex flex-col gap-4 p-5 text-left transition-colors duration-300 ${
                  isActive ? 'bg-[#0A0E1A]' : 'bg-[#050505] hover:bg-[#080808]'
                }`}
              >
                <span
                  className={`absolute inset-x-0 top-0 h-px transition-colors duration-300 ${
                    isActive ? 'bg-[#0057FF]' : 'bg-transparent'
                  }`}
                  aria-hidden="true"
                />
                <div className="flex items-start justify-between">
                  <div>
                    <span className="mono text-lg font-medium text-[#F2F2F2]">{channel.id}</span>
                    <p className="mono-label mt-1 text-[0.625rem] text-[#F2F2F2]/40">{channel.region}</p>
                  </div>
                  <span
                    className={`mono-label text-[0.5625rem] ${
                      isActive ? 'text-[#0057FF]' : 'text-[#F2F2F2]/30'
                    }`}
                  >
                    {channel.band}
                  </span>
                </div>

                <svg viewBox="0 0 240 40" className="h-10 w-full" aria-hidden="true">
                  <path
                    d={wavePath(channel.seed)}
                    fill="none"
                    stroke={isActive ? '#0057FF' : 'rgba(242,242,242,0.28)'}
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                </svg>

                <div className="flex items-baseline justify-between border-t border-white/10 pt-3">
                  <span className="mono text-sm text-[#F2F2F2]/85">
                    {channel.uv.toFixed(1)}
                    <span className="ml-1 text-[0.625rem] text-[#F2F2F2]/40">µV</span>
                  </span>
                  <span className="mono-label text-[0.5625rem] text-[#F2F2F2]/30">
                    {channel.impedance.toFixed(1)} kΩ
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        <div className="mt-6 flex flex-col gap-6 border border-white/10 p-6 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <span className="mono-label text-[#F2F2F2]/40">Selected node</span>
            <span className="mono text-xl text-[#F2F2F2]">{active.id}</span>
            <span className="mono-label text-[#C5A059]">{active.region}</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-10 gap-y-3">
            <div>
              <span className="mono-label block text-[#F2F2F2]/35">Signal</span>
              <span className="mono text-sm text-[#00FF41]">+{active.uv.toFixed(1)} µV</span>
            </div>
            <div>
              <span className="mono-label block text-[#F2F2F2]/35">SNR</span>
              <span className="mono text-sm text-[#F2F2F2]/80">{active.snr.toFixed(1)} dB</span>
            </div>
            <div>
              <span className="mono-label block text-[#F2F2F2]/35">Impedance</span>
              <span className="mono text-sm text-[#F2F2F2]/80">{active.impedance.toFixed(1)} kΩ</span>
            </div>
          </div>
        </div>

        <p className="mono-label mt-4 text-[0.5625rem] text-[#F2F2F2]/25">
          Sample readout — connect a G.tech Unicorn to stream your own signal
        </p>
      </div>
    </section>
  );
}