import { useState } from 'react';
import { base44 } from '@/api/base44Client';
import SectionHeader from '@/components/SectionHeader';

const TYPES = ['Investor', 'Partner', 'Research', 'Clinic'];

const EMPTY = { inquiry_type: 'Investor', full_name: '', email: '', organization: '', message: '' };

export default function AccessForm() {
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const update = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    setStatus('sending');
    try {
      await base44.entities.AccessRequest.create({
        inquiry_type: form.inquiry_type,
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        organization: form.organization.trim(),
        message: form.message.trim(),
        status: 'new',
      });
      setStatus('sent');
      setForm(EMPTY);
    } catch (err) {
      setStatus('idle');
      setError(err?.message || 'Transmission failed. Try again.');
    }
  };

  const fieldClass =
    'w-full border-b border-white/20 bg-transparent px-1 py-3 mono text-sm text-[#F2F2F2] placeholder:text-[#F2F2F2]/25 focus:border-[#0057FF] focus:outline-none';

  return (
    <section id="access" className="relative border-t border-white/10 bg-[#050505] py-[clamp(64px,9vw,120px)]">
      <div className="signal-grid pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />
      <div className="relative mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)]">
        <SectionHeader
          index="09"
          label="Initialize connection"
          title={<>Open the<br className="hidden md:block" /> brief.</>}
          intro="Tell us who you are and what you want to test. Investor briefs, pilot hardware and dataset access all enter through this form."
        />

        <div className="mt-12 grid grid-cols-1 gap-px bg-white/10 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <div className="bg-[#080808] p-6 sm:p-9">
            {status === 'sent' ? (
              <div className="flex min-h-[380px] flex-col justify-center">
                <span className="mono-label text-[#00FF41]">Transmission complete</span>
                <p className="mono mt-5 text-lg leading-relaxed text-[#F2F2F2]">
                  &gt; REQUEST_LOGGED_
                  <span className="caret ml-0.5 inline-block h-[1em] w-[0.5em] translate-y-[0.12em] bg-[#0057FF]" aria-hidden="true" />
                </p>
                <p className="mt-4 max-w-sm text-sm leading-relaxed text-[#F2F2F2]/55">
                  Your details are in the queue. Expect a reply within two business days with the brief
                  and next steps.
                </p>
                <button
                  type="button"
                  onClick={() => setStatus('idle')}
                  className="focus-ring mt-8 w-fit border border-[#F2F2F2]/25 px-5 py-2.5 mono-label text-[#F2F2F2] transition-colors duration-300 hover:border-[#0057FF] hover:bg-[#0057FF] hover:text-white"
                >
                  Send another
                </button>
              </div>
            ) : (
              <form onSubmit={submit} className="flex flex-col gap-7">
                <div>
                  <span className="mono-label text-[#F2F2F2]/40">&gt; Initialize_connection? [select]</span>
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
                              ? 'bg-[#0057FF] text-white'
                              : 'bg-[#080808] text-[#F2F2F2]/50 hover:text-[#F2F2F2]'
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
                    <span className="mono-label text-[#F2F2F2]/40">Name</span>
                    <input
                      required
                      value={form.full_name}
                      onChange={update('full_name')}
                      placeholder="Alex Mercer"
                      className={`mt-2 ${fieldClass}`}
                    />
                  </label>
                  <label className="block">
                    <span className="mono-label text-[#F2F2F2]/40">Email</span>
                    <input
                      required
                      type="email"
                      value={form.email}
                      onChange={update('email')}
                      placeholder="alex@fund.com"
                      className={`mt-2 ${fieldClass}`}
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="mono-label text-[#F2F2F2]/40">Organization</span>
                  <input
                    value={form.organization}
                    onChange={update('organization')}
                    placeholder="Fund, lab or clinic"
                    className={`mt-2 ${fieldClass}`}
                  />
                </label>

                <label className="block">
                  <span className="mono-label text-[#F2F2F2]/40">What do you want to test?</span>
                  <textarea
                    rows={3}
                    value={form.message}
                    onChange={update('message')}
                    placeholder="Deployment, patient group, timeline…"
                    className={`mt-2 resize-none ${fieldClass}`}
                  />
                </label>

                {error ? (
                  <p className="mono-label text-[#FF5A5A]" role="alert">
                    {error}
                  </p>
                ) : null}

                <div className="flex flex-col items-start gap-4 border-t border-white/10 pt-6 sm:flex-row sm:items-center sm:justify-between">
                  <span className="mono-label text-[#F2F2F2]/25">
                    {status === 'sending' ? 'Transmitting…' : 'Encrypted · reviewed by founders'}
                  </span>
                  <button
                    type="submit"
                    disabled={status === 'sending'}
                    className="focus-ring inline-flex items-center gap-3 border border-[#F2F2F2] px-6 py-3.5 mono-label text-[#F2F2F2] transition-colors duration-300 hover:bg-[#F2F2F2] hover:text-[#050505] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {status === 'sending' ? 'Sending' : 'Transmit request'}
                    <span aria-hidden="true">→</span>
                  </button>
                </div>
              </form>
            )}
          </div>

          <div className="flex flex-col justify-between gap-8 bg-[#050505] p-6 sm:p-9">
            <div>
              <span className="mono-label text-[#C5A059]">Direct lines</span>
              <ul className="mt-5 space-y-5">
                <li>
                  <span className="mono-label block text-[#F2F2F2]/35">Investor brief</span>
                  <a
                    href="mailto:invest@eegneurotec.com"
                    className="focus-ring mono text-sm text-[#F2F2F2] underline decoration-white/20 underline-offset-4 transition-colors duration-300 hover:text-[#0057FF]"
                  >
                    invest@eegneurotec.com
                  </a>
                </li>
                <li>
                  <span className="mono-label block text-[#F2F2F2]/35">Partnerships</span>
                  <a
                    href="mailto:partners@eegneurotec.com"
                    className="focus-ring mono text-sm text-[#F2F2F2] underline decoration-white/20 underline-offset-4 transition-colors duration-300 hover:text-[#0057FF]"
                  >
                    partners@eegneurotec.com
                  </a>
                </li>
              </ul>
            </div>
            <p className="text-xs leading-relaxed text-[#F2F2F2]/35">
              We do not sell or share submitted details. Requests are read by the founding team only.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}