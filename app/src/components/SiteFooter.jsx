export default function SiteFooter() {
  return (
    <footer className="border-t border-white/10 bg-[#07111B]">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 px-[clamp(20px,5vw,64px)] py-8 sm:flex-row sm:items-center sm:justify-between">
        <a href="#top" className="focus-ring mono-label w-fit text-[#F8FAFC]">
          NeuronVision
        </a>
        <p className="mono-label text-[0.5625rem] text-[#F8FAFC]/30">
          © {new Date().getFullYear()} NeuronVision
        </p>
        <a
          href="mailto:teamtopnest@gmail.com"
          className="focus-ring mono-label w-fit text-[0.5625rem] text-[#F8FAFC]/45 transition-colors hover:text-[#F8FAFC]"
        >
          Contact
        </a>
      </div>
    </footer>
  );
}
