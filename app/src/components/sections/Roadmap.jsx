import SectionHeader from '@/components/SectionHeader';

const PHASES = [
  {
    id: '01',
    window: 'Complete',
    title: 'Eight-channel prototype',
    body: 'Bench unit reading all eight electrodes at 250 Hz with a live decode window. Verified on twelve volunteers.',
    state: 'done',
  },
  {
    id: '02',
    window: 'Now',
    title: 'Closed pilot',
    body: 'Ten users, six weeks of daily use. Target: 96% word accuracy and a two-minute setup with no gel.',
    state: 'active',
  },
  {
    id: '03',
    window: 'Next 12 months',
    title: 'Clinical validation',
    body: 'Partner sites in neurology and rehabilitation run the device against their own typing baselines.',
    state: 'next',
  },
  {
    id: '04',
    window: 'Beyond',
    title: 'Licensed SDK',
    body: 'The decoder ships as a licensable SDK for assistive and industrial text-entry products.',
    state: 'next',
  },
];

const DOT = {
  done: 'bg-[#00FF41] border-[#00FF41]',
  active: 'bg-[#0057FF] border-[#0057FF] live-dot',
  next: 'bg-transparent border-white/25',
};

const TEXT = {
  done: 'text-[#00FF41]',
  active: 'text-[#0057FF]',
  next: 'text-[#F2F2F2]/35',
};

export default function Roadmap() {
  return (
    <section id="roadmap" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="07"
          label="Roadmap"
          title={<>Where the round<br className="hidden md:block" /> takes us.</>}
          intro="Four phases, each with a milestone an investor can check. Nothing in the plan depends on inventing new sensor physics."
        />

        <ol className="mt-12 grid grid-cols-1 gap-px bg-white/10 md:grid-cols-2 xl:grid-cols-4">
          {PHASES.map((phase) => (
            <li key={phase.id} className="relative bg-[#050505] p-6 sm:p-8">
              <div className="flex items-center justify-between">
                <span className="mono-label text-[#F2F2F2]/30">{phase.id}</span>
                <span className={`mono-label ${TEXT[phase.state]}`}>{phase.window}</span>
              </div>
              <span className={`mt-6 block h-2 w-2 rounded-full border ${DOT[phase.state]}`} aria-hidden="true" />
              <h3 className="mt-4 font-heading text-lg font-semibold leading-tight tracking-tight text-[#F2F2F2]">
                {phase.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-[#F2F2F2]/50">{phase.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}