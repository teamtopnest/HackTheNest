import SectionHeader from '@/components/SectionHeader';

const STEPS = [
  {
    id: '01',
    title: 'Acquire',
    body: 'Eight dry electrodes capture broadband cortical activity at 250 Hz, streamed over BLE with hardware-synced timestamps.',
  },
  {
    id: '02',
    title: 'Denoise',
    body: 'Line noise, blink and jaw artifacts are removed on-device with a 12 ms causal filter — no round trip to a server.',
  },
  {
    id: '03',
    title: 'Decode',
    body: 'Band-power features across the language network feed a compact classifier that maps neural intent onto phoneme sequences.',
  },
  {
    id: '04',
    title: 'Emit',
    body: 'A language model constrains the output into readable words, then writes into any text field through the SDK.',
  },
];

export default function Pipeline() {
  return (
    <section id="pipeline" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="05"
          label="The pipeline"
          title={<>Four stages,<br className="hidden md:block" /> all local.</>}
          intro="Every stage runs on the paired device. Nothing leaves the headset unless the user asks it to — the whole loop closes in 38 ms."
        />

        <div className="mt-12 grid grid-cols-1 gap-px bg-white/10 md:grid-cols-2 xl:grid-cols-4">
          {STEPS.map((step) => (
            <div key={step.id} className="group relative bg-[#050505] p-6 sm:p-8">
              <span className="absolute left-0 top-0 h-px w-0 bg-[#0057FF] transition-all duration-500 group-hover:w-full" aria-hidden="true" />
              <span className="mono-label text-[#0057FF]">{step.id}</span>
              <h3 className="mt-6 font-heading text-2xl font-semibold tracking-tight text-[#F2F2F2]">
                {step.title}
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#F2F2F2]/55">{step.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}