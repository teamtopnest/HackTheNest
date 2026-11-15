import SectionHeader from '@/components/SectionHeader';
import { Image } from '@/components/ui/image';

const HEAD_IMAGE =
  'https://media.base44.com/images/public/6af8ddbb4d9fa9ed989e6fc8/d046d90f5_generated_bcc4be63.png';

const SPECS = [
  { label: 'Channels', value: '8', detail: 'Fp1 · Fp2 · C3 · C4 · P7 · P8 · O1 · O2' },
  { label: 'Sampling rate', value: '250', detail: 'Hz per channel, hardware clocked' },
  { label: 'ADC resolution', value: '24', detail: 'bit, 0.5 µV noise floor' },
  { label: 'Wireless link', value: 'BLE 5.2', detail: 'Paired to host in under 3 s' },
  { label: 'Battery', value: '12 h', detail: 'Continuous acquisition, USB-C charge' },
  { label: 'Mass', value: '128 g', detail: 'Dry electrodes, no gel required' },
];

export default function HardwareSpec() {
  return (
    <section id="hardware" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="04"
          label="The hardware"
          title={<>G.tech Unicorn,<br className="hidden md:block" /> made clinical.</>}
          intro="We build on the G.tech 8-channel platform — a validated, off-the-shelf sensor board — then harden it for language work: dry electrodes, sub-3-second pairing, and a mount that survives a full day of recording."
        />

        <div className="mt-12 grid grid-cols-1 items-stretch gap-px bg-white/10 lg:grid-cols-2">
          <div className="relative min-h-[320px] overflow-hidden bg-[#080808] lg:min-h-[520px]">
            <Image
              src={HEAD_IMAGE}
              alt="G.tech eight-channel EEG headset with gold electrode nodes"
              className="h-full w-full object-cover"
              fittingType="fill"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#050505] via-transparent to-transparent" aria-hidden="true" />
            <div className="absolute bottom-5 left-5 flex items-center gap-3">
              <span className="live-dot h-1.5 w-1.5 bg-[#00FF41]" aria-hidden="true" />
              <span className="mono-label text-[#F2F2F2]/75">Unit 007 · bench-verified</span>
            </div>
          </div>

          <div className="bg-[#050505] p-6 sm:p-9">
            <div className="flex items-baseline justify-between border-b border-white/10 pb-4">
              <span className="mono-label text-[#F2F2F2]/40">Specification</span>
              <span className="mono-label text-[#0057FF]">Rev. 2.4</span>
            </div>
            <dl className="mt-2">
              {SPECS.map((spec) => (
                <div
                  key={spec.label}
                  className="grid grid-cols-[1fr_auto] items-baseline gap-4 border-b border-white/10 py-4 last:border-b-0"
                >
                  <div>
                    <dt className="mono-label text-[#F2F2F2]/45">{spec.label}</dt>
                    <dd className="mt-1 text-sm leading-relaxed text-[#F2F2F2]/55">{spec.detail}</dd>
                  </div>
                  <dd className="display whitespace-nowrap text-2xl text-[#F2F2F2] sm:text-3xl">
                    {spec.value}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </section>
  );
}