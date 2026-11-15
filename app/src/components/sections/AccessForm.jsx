import { useState } from 'react';
import SectionHeader from '@/components/SectionHeader';

const TYPES = ['Demo', 'Collaboration', 'Research', 'Clinic'];

const EMPTY = { inquiry_type: 'Demo', full_name: '', email: '', organization: '', message: '' };

export default function AccessForm() {
  const [form, setForm] = useState(EMPTY);
  const [submitted, setSubmitted] = useState(false);

  const update = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSubmitted(true);
  };

  const fieldClass =
    'w-full border-b border-white/20 bg-transparent px-1 py-3 mono text-sm text-[#F8FAFC] placeholder:text-[#F8FAFC]/25 focus:border-[#38BDF8] focus:outline-none';

  return (
    <section id="access" className="relative border-t border-white/10 bg-[#07111B] py-[clamp(64px,9vw,120px)]">
      <div className="signal-grid pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />
      <div className="relative mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="07"
          label="Initialize connection"
          title={<>Connect<br className="hidden md:block" /> with us.</>}
          intro="Have a question or want to collaborate? Tell us what you would like to explore."
        />

        <div className="mt-12 grid grid-cols-1 gap-px bg-white/10 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <div className="bg-[#0B1A28] p-6 sm:p-9">
            <p className="mono-label mb-7 border border-[#7DD3FC]/30 p-3 text-[#7DD3FC]" role="note">
              Preview only — this form does not send or store submissions.
            </p>
            <form onSubmit={submit} className="flex flex-col gap-7">
                <div>
                  <span className="mono-label text-[#F8FAFC]/40">&gt; Initialize_connection? [select]</span>
                  <div className="mt-3 grid grid-cols-2 gap-px bg-white/10 sm:grid-cols-4">
                    {TYPES.map((type) => {
                      const active = form.inquiry_type === type;
                      return (
                        <button
                          key={type}
                          type="button"
                          onClick={() => setForm((prev) => ({ ...prev, inquiry_type: type }))}
                          aria-pressed={active}
                          className={`focus-ring px-3 py-3 mono-label transition-colors duration-300 ${
                            active
                              ? 'bg-[#0369A1] text-white'
                              : 'bg-[#0B1A28] text-[#F8FAFC]/50 hover:text-[#F8FAFC]'
                          }`}
                        >
                          {type}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                  <label className="block">
                    <span className="mono-label text-[#F8FAFC]/40">Name</span>
                    <input
                      required
                      value={form.full_name}
                      onChange={update('full_name')}
                      placeholder="Alex Mercer"
                      className={`mt-2 ${fieldClass}`}
                    />
                  </label>
                  <label className="block">
                    <span className="mono-label text-[#F8FAFC]/40">Email</span>
                    <input
                      required
                      type="email"
                      value={form.email}
                      onChange={update('email')}
                      placeholder="alex@lab.org"
                      className={`mt-2 ${fieldClass}`}
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="mono-label text-[#F8FAFC]/40">Organization</span>
                  <input
                    value={form.organization}
                    onChange={update('organization')}
                    placeholder="Team, lab or clinic"
                    className={`mt-2 ${fieldClass}`}
                  />
                </label>

                <label className="block">
                  <span className="mono-label text-[#F8FAFC]/40">What do you want to test?</span>
                  <textarea
                    rows={3}
                    value={form.message}
                    onChange={update('message')}
                    placeholder="Deployment, patient group, timeline…"
                    className={`mt-2 resize-none ${fieldClass}`}
                  />
                </label>

                {submitted ? (
                  <p className="mono-label text-[#7DD3FC]" role="status">
                    Demo only: no request was sent or saved.
                  </p>
                ) : null}

                <div className="flex flex-col items-start gap-4 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
                  <span className="mono-label text-[#F8FAFC]/25">
                    Demo form · no data is transmitted
                  </span>
                  <button
                    type="submit"
                    className="focus-ring inline-flex items-center gap-3 border border-[#F8FAFC] px-6 py-3.5 mono-label text-[#F8FAFC] transition-colors duration-300 hover:bg-[#F8FAFC] hover:text-[#07111B] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Preview form
                    <span aria-hidden="true">→</span>
                  </button>
                </div>
            </form>
          </div>

          <div className="flex flex-col justify-between gap-8 bg-[#07111B] p-6 sm:p-9">
            <div>
              <span className="mono-label text-[#7DD3FC]">Direct lines</span>
              <div className="mt-5">
                <span className="mono-label block text-[#F8FAFC]/35">Questions &amp; collaborations</span>
                <a
                  href="mailto:teamtopnest@gmail.com"
                  className="focus-ring mono text-sm text-[#F8FAFC] underline decoration-white/20 underline-offset-4 transition-colors duration-300 hover:text-[#38BDF8]"
                >
                  teamtopnest@gmail.com
                </a>
              </div>
            </div>
            <p className="text-xs leading-relaxed text-[#F8FAFC]/35">
              Do not enter real personal information: this preview is not connected to a secure submission service.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
