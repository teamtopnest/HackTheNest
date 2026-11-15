import { Link } from 'react-router-dom';

const LINKS = [
  { label: 'Channels', href: '#channels' },
  { label: 'Decode', href: '#stream' },
  { label: 'Hardware', href: '#hardware' },
  { label: 'Roadmap', href: '#roadmap' },
];

export default function SiteNav() {
  return (
    <header className="absolute inset-x-0 top-0 z-10 border-b border-white/10 bg-[#050505]/75 backdrop-blur-sm">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-6 px-[clamp(20px,5vw,64px)] py-4">
        <a href="#top" className="focus-ring mono-label whitespace-nowrap text-[#F2F2F2]">
          EEG <span className="text-[#0057FF]">/</span> Neurotec
        </a>
        <nav aria-label="Main navigation" className="hidden items-center gap-6 md:flex">
          {LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="focus-ring mono-label text-[0.6rem] text-[#F2F2F2]/50 transition-colors hover:text-[#F2F2F2]"
            >
              {link.label}
            </a>
          ))}
          <Link
            to="/acquisition"
            className="focus-ring mono-label text-[0.6rem] text-[#0057FF] transition-colors hover:text-white"
          >
            Start acquisition
          </Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link to="/acquisition" className="focus-ring mono-label text-[0.55rem] text-[#F2F2F2] md:hidden">
            Start acquisition
          </Link>
          <a
            href="#access"
            className="focus-ring border border-white/30 px-3 py-2 mono-label text-[0.6rem] text-[#F2F2F2] transition-colors hover:border-[#0057FF] hover:bg-[#0057FF]"
          >
            Get in touch
          </a>
        </div>
      </div>
    </header>
  );
}
