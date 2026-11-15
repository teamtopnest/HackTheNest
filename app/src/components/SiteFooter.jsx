export default function SiteFooter() {
  return (
    <footer className="border-t border-white/10 bg-[#050505]">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 px-[clamp(20px,5vw,64px)] py-8 sm:flex-row sm:items-center sm:justify-between">
        <a href="#top" className="focus-ring mono-label w-fit text-[#F2F2F2]">
          EEG <span className="text-[#0057FF]">/</span> Neurotec
        </a>
        <p className="mono-label text-[0.5625rem] text-[#F2F2F2]/30">
          © {new Date().getFullYear()} EEG Neurotec
        </p>
        <a
          href="mailto:partners@eegneurotec.com"
          className="focus-ring mono-label w-fit text-[0.5625rem] text-[#F2F2F2]/45 transition-colors hover:text-[#F2F2F2]"
        >
          Contact
        </a>
      </div>
    </footer>
  );
}
