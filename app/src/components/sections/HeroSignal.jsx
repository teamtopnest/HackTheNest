import { Image } from '@/components/ui/image';
import { ArrowDown } from 'lucide-react';

const HERO_IMAGE =
  'https://media.base44.com/images/public/6af8ddbb4d9fa9ed989e6fc8/3ae352ac9_generated_4eeaeda2.png';

function Letters({ text, offset = 0 }) {
  return text.split('').map((ch, i) =>
    ch === ' ' ? (
      <span key={`sp-${i}`} className="inline-block w-[0.26em]" />
    ) : (
      <span
        key={`l-${i}`}
        className="hero-letter"
        style={{ animationDelay: `${0.08 + 0.045 * (i + offset)}s` }}
      >
        {ch}
      </span>
    )
  );
}

export default function HeroSignal() {
  return (
    <section className="hero-root hero-anim" aria-label="NeuronVision — brain to text">
      <div className="hero-media">
        <Image
          src={HERO_IMAGE}
          alt="Macro view of a G.tech EEG electrode resting against a temple"
          className="h-full w-full object-cover"
          fittingType="fill"
        />
      </div>
      <div className="hero-scrim" aria-hidden="true" />

      <div className="relative mx-auto w-full max-w-[1100px] text-center">
        <div className="hero-eyebrow mb-6 flex items-center justify-center gap-3">
          <span className="live-dot h-1.5 w-1.5 bg-[#00FF41]" aria-hidden="true" />
          <span className="mono-label text-[#00FF41]">Channel status: active [8/8]</span>
          <span className="mono-label text-[#F8FAFC]/30" aria-hidden="true">
            /
          </span>
          <span className="mono-label text-[#7DD3FC]">Signal division</span>
        </div>

        <h1 className="display text-[clamp(2.2rem,min(8.6vw,13vh),6.6rem)] text-[#F8FAFC]">
          <span className="block">
            <Letters text="THOUGHT." />
          </span>
          <span className="mt-1 block text-[#F8FAFC]/65">
            <Letters text="TRANSCRIBED." offset={9} />
          </span>
        </h1>

        <p className="hero-body mx-auto mt-7 max-w-[34rem] text-[clamp(1.0625rem,1.6vw,1.25rem)] leading-relaxed text-[#F8FAFC]/80">
          Eight G.tech EEG channels. Clear, editable text in under 5 seconds.
          No implants. No keyboard.
        </p>

        <div className="hero-cta mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a
            href="#access"
            className="focus-ring group inline-flex min-h-14 items-center justify-center gap-3 border border-[#38BDF8] bg-[#0369A1] px-9 py-[1.125rem] font-mono text-[0.75rem] uppercase tracking-[0.2em] text-[#F8FAFC] transition-colors duration-300 hover:bg-[#075985]"
          >
            Connect with us
            <span aria-hidden="true" className="transition-transform duration-300 group-hover:translate-x-1">
              →
            </span>
          </a>
          <a
            href="#stream"
            className="focus-ring inline-flex items-center justify-center gap-2 px-2 py-4 mono-label text-[#F8FAFC]/60 transition-colors duration-300 hover:text-[#F8FAFC]"
          >
            See the decode
            <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        </div>
      </div>

      <div className="absolute bottom-6 left-[clamp(20px,5vw,64px)] hidden md:block">
        <span className="mono-label text-[#F8FAFC]/30">G.tech unicorn · 250 hz · 24-bit</span>
      </div>
      <div className="absolute bottom-6 right-[clamp(20px,5vw,64px)] hidden md:block">
        <span className="mono-label text-[#F8FAFC]/30">01 / Signal genesis</span>
      </div>
    </section>
  );
}
