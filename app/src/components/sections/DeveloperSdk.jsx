import { useState } from 'react';
import SectionHeader from '@/components/SectionHeader';
import { Check, Copy } from 'lucide-react';

const SNIPPET = `import { Neurotec } from '@eeg-neurotec/sdk';

// pair a G.tech 8-channel headset
const link = await Neurotec.connect({
  channels: 8,
  rate: 250,
  filter: 'causal',
});

// stream decoded phrases into any field
link.on('phrase', ({ text, confidence }) => {
  if (confidence > 0.9) output.value = text;
});`;

export default function DeveloperSdk() {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(SNIPPET);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <section id="sdk" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="08"
          label="Developer surface"
          title={<>Twelve lines<br className="hidden md:block" /> to first text.</>}
          intro="Pair, subscribe, render. The SDK handles pairing, filtering and model loading so your team only writes the interface."
        />

        <div className="mt-12 grid grid-cols-1 gap-px bg-white/10 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="relative bg-[#080808]">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 bg-[#0057FF]" aria-hidden="true" />
                <span className="mono-label text-[#F2F2F2]/45">decode.js</span>
              </div>
              <button
                type="button"
                onClick={copy}
                className="focus-ring inline-flex items-center gap-2 px-2 py-1 mono-label text-[#F2F2F2]/55 transition-colors duration-300 hover:text-[#F2F2F2]"
              >
                {copied ? <Check className="h-3 w-3" aria-hidden="true" /> : <Copy className="h-3 w-3" aria-hidden="true" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <pre className="overflow-x-auto px-5 py-6 text-[0.78rem] leading-relaxed text-[#F2F2F2]/80">
              <code className="mono">{SNIPPET}</code>
            </pre>
          </div>

          <div className="flex flex-col divide-y divide-white/10 bg-[#050505]">
            {[
              { label: 'Runtime', value: 'JavaScript · Python · Swift' },
              { label: 'Transport', value: 'BLE 5.2 / USB-C' },
              { label: 'License', value: 'Commercial, per seat' },
              { label: 'Access', value: 'Partner program only' },
            ].map((row) => (
              <div key={row.label} className="flex items-baseline justify-between gap-4 px-6 py-5">
                <span className="mono-label text-[#F2F2F2]/35">{row.label}</span>
                <span className="mono text-right text-xs text-[#F2F2F2]/80">{row.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}