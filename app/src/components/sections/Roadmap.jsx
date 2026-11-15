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
];

const DOT = {
  done: 'bg-[#00FF41] border-[#00FF41]',
  active: 'bg-[#0369A1] border-[#38BDF8] live-dot',
  next: 'bg-transparent border-white/25',
};

const TEXT = {
  done: 'text-[#00FF41]',
  active: 'text-[#38BDF8]',
  next: 'text-[#F8FAFC]/35',
};

export default function Roadmap() {
  return (
    <section id="roadmap" className="relative border-t border-white/10 bg-[#07111B] py-[clamp(64px,9vw,120px)]">
      <div className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="06"
          label="Roadmap"
          title={<>What comes<br className="hidden md:block" /> next.</>}
          intro="Three milestones from prototype to clinical validation. Each builds on the same eight-channel platform."
        />

        <ol className="mt-12 grid grid-cols-1 gap-px bg-white/10 md:grid-cols-3">
          {PHASES.map((phase) => (
            <li key={phase.id} className="relative bg-[#07111B] p-6 sm:p-8">
              <div className="flex items-center justify-between">
                <span className="mono-label text-[#F8FAFC]/30">{phase.id}</span>
                <span className={`mono-label ${TEXT[phase.state]}`}>{phase.window}</span>
              </div>
              <span className={`mt-6 block h-2 w-2 rounded-full border ${DOT[phase.state]}`} aria-hidden="true" />
              <h3 className="mt-4 font-heading text-xl font-semibold leading-tight tracking-tight text-[#F8FAFC]">
                {phase.title}
              </h3>
              <p className="mt-2 text-base leading-relaxed text-[#F8FAFC]/50">{phase.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
