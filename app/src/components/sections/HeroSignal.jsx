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
    <section className="hero-root hero-anim" aria-label="EEG Neurotec — brain to text">
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
          <span className="mono-label text-[#F2F2F2]/30" aria-hidden="true">
            /
          </span>
          <span className="mono-label text-[#C5A059]">Signal division</span>
        </div>

        <h1 className="display text-[clamp(2.2rem,min(8.6vw,13vh),6.6rem)] text-[#F2F2F2]">
          <span className="block">
            <Letters text="THOUGHT." />
          </span>
          <span className="mt-1 block text-[#F2F2F2]/65">
            <Letters text="TRANSCRIBED." offset={9} />
          </span>
        </h1>

        <p className="hero-body mx-auto mt-7 max-w-[34rem] text-[clamp(0.95rem,1.4vw,1.0625rem)] leading-relaxed text-[#F2F2F2]/80">
          Eight channels of G.tech cortical signal, decoded into clean, editable text.
          No implants, no keyboard — just the raw electrical intent of speech, written
          down in under forty milliseconds.
        </p>

        <div className="hero-cta mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a
            href="#access"
            className="focus-ring group inline-flex items-center justify-center gap-3 border border-[#F2F2F2] bg-transparent px-8 py-4 mono-label text-[#F2F2F2] transition-colors duration-300 hover:bg-[#F2F2F2] hover:text-[#050505]"
          >
            Request the investor brief
            <span aria-hidden="true" className="transition-transform duration-300 group-hover:translate-x-1">
              →
            </span>
          </a>
          <a
            href="#stream"
            className="focus-ring inline-flex items-center justify-center gap-2 px-2 py-4 mono-label text-[#F2F2F2]/60 transition-colors duration-300 hover:text-[#F2F2F2]"
          >
            See the decode
            <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        </div>
      </div>

      <div className="absolute bottom-6 left-[clamp(20px,5vw,64px)] hidden md:block">
        <span className="mono-label text-[#F2F2F2]/30">G.tech unicorn · 250 hz · 24-bit</span>
      </div>
      <div className="absolute bottom-6 right-[clamp(20px,5vw,64px)] hidden md:block">
        <span className="mono-label text-[#F2F2F2]/30">01 / Signal genesis</span>
      </div>
    </section>
  );
}