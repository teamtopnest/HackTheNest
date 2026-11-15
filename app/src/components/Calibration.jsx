import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Loader2, RotateCcw, ShieldAlert } from 'lucide-react';
import alignmentImage from '../assets/calibration/alignment-10-20.png';

const REFERENCE_CHANNELS = ['Fz', 'Cz', 'P3', 'Pz', 'P4', 'PO7', 'PO8', 'Oz'];

function AlignmentFigure() {
  return (
    <figure className="bg-white p-4 text-[#151a24]">
      <img
        src={alignmentImage}
        alt="International 10–20 electrode map viewed from above, nose at the top. Fz, Cz, P3, Pz, P4, PO7, PO8 and Oz are highlighted in black and listed as channels 1 to 8."
        className="mx-auto w-full max-w-[560px]"
      />
      <figcaption className="mt-3 text-xs leading-5 text-[#41516c]">Reference montage: 1 Fz, 2 Cz, 3 P3, 4 Pz, 5 P4, 6 PO7, 7 PO8, 8 Oz. Confirm it against the selected headset’s manual—this app does not verify electrode positions or channel mapping.</figcaption>
    </figure>
  );
}

function CalibrationVisual() {
  const contact = [0.35, 0.25, 0.5, 0.3, 0.45, 0.7, 0.4, 0.3];
  return (
    <figure className="bg-white p-4 text-[#151a24]">
      <svg viewBox="0 0 420 260" role="img" aria-labelledby="cal-title cal-desc" className="w-full">
        <title id="cal-title">Illustration of a signal and contact check</title>
        <desc id="cal-desc">Each reference channel has a contact bar compared with an example acceptance line, and a short baseline trace checked for flat lines, clipping and mains noise.</desc>
        <text x="10" y="16" fontSize="11" fontWeight="700" fill="#41516c">CONTACT (example)</text>
        <text x="200" y="16" fontSize="11" fontWeight="700" fill="#41516c">BASELINE</text>
        <line x1="150" y1="22" x2="150" y2="250" stroke="#d97706" strokeDasharray="4 4" />
        <text x="152" y="252" fontSize="9" fill="#b45309">limit</text>
        {REFERENCE_CHANNELS.map((ch, i) => {
          const y = 34 + i * 27;
          const good = contact[i] < 0.6;
          const path = Array.from({ length: 50 }, (_, k) => {
            const x = 200 + k * 4.2;
            const v = Math.sin(k * 0.55 + i) * 5 + Math.sin(k * 1.7 + i * 2) * 2.5;
            return `${k ? 'L' : 'M'}${x.toFixed(1)} ${(y + 6 + v).toFixed(1)}`;
          }).join(' ');
          return (
            <g key={ch}>
              <text x="10" y={y + 10} fontSize="11" fontWeight="600" fill="#1b263b">{ch}</text>
              <rect x="44" y={y} width="150" height="12" fill="#eef2f9" />
              <rect x="44" y={y} width={150 * contact[i]} height="12" fill={good ? '#38bdf8' : '#d97706'} />
              <path d={path} fill="none" stroke="#1b263b" strokeWidth="1.2" />
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#41516c]">Illustration only, not live values. Use the manufacturer’s impedance tool and acceptance criteria.</figcaption>
    </figure>
  );
}

function SyncVisual() {
  return (
    <figure className="bg-white p-4 text-[#151a24]">
      <svg viewBox="0 0 420 230" role="img" aria-labelledby="sync-title sync-desc" className="w-full">
        <title id="sync-title">Illustration of stimulus-to-EEG synchronization</title>
        <desc id="sync-desc">Three timelines: the software flash command, the photodiode-measured screen onset a few milliseconds later, and the EEG trigger marker recorded with samples. The delay between command and onset is the latency to measure, and its change across a session is the drift.</desc>
        {[['Flash command', 40], ['Photodiode onset', 105], ['EEG marker', 170]].map(([label, y]) => (
          <g key={label}>
            <text x="8" y={y - 12} fontSize="11" fontWeight="700" fill="#41516c">{label.toUpperCase()}</text>
            <line x1="8" y1={y + 20} x2="412" y2={y + 20} stroke="#cbd5e1" />
          </g>
        ))}
        {[140, 290].map((x, i) => (
          <g key={x}>
            <rect x={x} y="40" width="40" height="20" fill="#38bdf8" />
            <rect x={x + 22 + i * 6} y="105" width="40" height="20" fill="#1b263b" />
            <line x1={x + 22 + i * 6} y1="170" x2={x + 22 + i * 6} y2="190" stroke="#d97706" strokeWidth="3" />
            {Array.from({ length: 16 }, (_, k) => <circle key={k} cx={x - 8 + k * 6} cy="190" r="1.6" fill="#64748b" />)}
            <path d={`M${x} 88 H${x + 22 + i * 6}`} stroke="#d97706" strokeWidth="2" markerEnd="url(#arrow)" />
            <text x={x} y="78" fontSize="10" fill="#b45309">{i ? 'Δt + drift' : 'Δt latency'}</text>
            <line x1={x} y1="60" x2={x} y2="190" stroke="#94a3b8" strokeDasharray="3 4" />
          </g>
        ))}
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10z" fill="#d97706" /></marker>
        </defs>
        <text x="8" y="222" fontSize="10" fill="#41516c">Dots = EEG samples. Align epochs to the measured onset, not the command.</text>
      </svg>
      <figcaption className="mt-2 text-xs leading-5 text-[#41516c]">Illustration only. Real synchronization requires a hardware trigger or photodiode recorded with the EEG.</figcaption>
    </figure>
  );
}

const STATUS_TEXT = {
  idle: 'Not started',
  running: 'Running (simulated)…',
  ready: 'Awaiting operator confirmation',
  done: 'Confirmed by operator',
};

function Step({ number, title, status, children }) {
  const done = status === 'done';
  return (
    <section className={`border p-6 sm:p-8 ${done ? 'border-emerald-400/40 bg-emerald-400/[0.04]' : 'border-white/10 bg-white/[0.02]'}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="mono-label text-[#7dd3fc]">{number} / {title}</p>
        <span role="status" className={`flex items-center gap-1 border px-2 py-1 text-[0.65rem] ${done ? 'border-emerald-400/40 text-emerald-200' : 'border-amber-400/30 text-amber-200'}`}>
          {done && <Check size={12} />}{STATUS_TEXT[status]}
        </span>
      </div>
      {children}
    </section>
  );
}

const primary = 'focus-ring flex items-center gap-2 bg-[#0369A1] px-4 py-3 text-sm text-white hover:bg-[#075985] disabled:cursor-not-allowed disabled:opacity-40';
const secondary = 'focus-ring flex items-center gap-2 border border-white/25 px-4 py-3 text-sm text-white hover:border-white disabled:cursor-not-allowed disabled:opacity-40';

function RunControls({ name, status, demo, onRun, onComplete, onReset }) {
  return (
    <div className="mt-6 border-t border-white/10 pt-5">
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={onRun} disabled={status === 'running' || status === 'done'} className={secondary}>
          {status === 'running' && <Loader2 className="animate-spin" size={14} />}Run {name}
        </button>
        <button type="button" onClick={onComplete} disabled={status !== 'ready'} className={primary}><Check size={14} /> {name} completed</button>
        {status === 'done' && <button type="button" onClick={onReset} className="focus-ring flex items-center gap-2 px-2 text-xs text-white/55 hover:text-white"><RotateCcw size={13} /> Redo</button>}
      </div>
      <p className="mt-3 text-xs leading-5 text-white/45">
        {demo
          ? `Demo: “Run” plays a simulated procedure. No headset is measured.`
          : `No measurement API is connected. “Run” starts the manual procedure above; complete it with the manufacturer’s tools, then confirm.`}
        {' '}“Completed” records an operator confirmation, not a verified result.
      </p>
    </div>
  );
}

export default function Calibration({ model, demo, checked, busy, error, onBack, onDemo, onPreview }) {
  const [alignment, setAlignment] = useState('idle');
  const [calibration, setCalibration] = useState('idle');
  const [sync, setSync] = useState('idle');
  const timers = useRef([]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  function run(setter) {
    if (!demo) {
      setter('ready');
      return;
    }
    setter('running');
    timers.current.push(setTimeout(() => setter('ready'), 2000));
  }

  const completed = [alignment, calibration, sync].filter((s) => s === 'done').length;
  const allDone = completed === 3;
  const canContinue = allDone && !busy && (demo || checked);

  return (
    <main className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)] pb-20 pt-12 sm:pt-16">
      <button type="button" onClick={onBack} disabled={busy} className="focus-ring flex items-center gap-2 text-xs text-white/55 hover:text-white disabled:opacity-40"><ArrowLeft size={14} /> Back to device setup</button>
      <div className="mt-8 max-w-3xl">
        <p className="mono-label text-[#38BDF8]">02 / Calibration and synchronization</p>
        <h1 className="mt-4 font-heading text-4xl font-semibold tracking-tight sm:text-5xl">Prepare your headset<span className="text-[#38BDF8]">.</span></h1>
        <p className="mt-4 text-sm leading-7 text-white/55">Selected: {model}{demo && ' (demo)'}. Complete all three steps to open the workspace.</p>
      </div>
      <div className="mt-8 flex gap-3 border border-amber-400/30 bg-amber-400/5 p-4 text-sm leading-6 text-amber-100/80">
        <ShieldAlert className="mt-1 shrink-0" size={18} />
        <p><strong>Operator checklist—not an automated calibration.</strong> This app cannot measure electrode placement or impedance, verify signal quality, or synchronize stimuli with EEG. Confirmations are recorded on the operator’s word. Real P300 decoding remains disabled.</p>
      </div>

      <div className="mt-8 grid gap-5">
        <Step number="01" title="Physical alignment and cap fitting" status={alignment}>
          <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(280px,560px)_1fr]">
            <AlignmentFigure />
            <div className="text-sm leading-7 text-white/65">
              <p>Follow the device manufacturer’s fitting instructions. A qualified operator should:</p>
              <ol className="mt-3 list-decimal space-y-2 pl-5">
                <li>Identify the nasion, inion and left and right preauricular points. Measure according to the 10–20 protocol.</li>
                <li>Center the cap so Cz sits at the midpoint of nasion–inion and left–right ear distances. Check that Fz, Cz, Pz and Oz follow the midline.</li>
                <li>Check P3/P4 and PO7/PO8 are symmetric left and right. Fit the cap securely without discomfort.</li>
                <li>Confirm each electrode, reference and ground against the headset’s actual montage. Part hair and prepare contacts only as the manufacturer directs.</li>
              </ol>
              <a href="https://mentalab.com/mastering-the-10-20-system-for-accurate-eeg-electrode-placement/" target="_blank" rel="noreferrer" className="mt-4 inline-block text-[#8aabff] underline underline-offset-4">Read about the 10–20 system</a>
              <div className="mt-6 flex flex-wrap gap-3 border-t border-white/10 pt-5">
                <button type="button" onClick={() => setAlignment(alignment === 'done' ? 'idle' : 'done')} aria-pressed={alignment === 'done'} className={alignment === 'done' ? secondary : primary}>
                  {alignment === 'done' ? <><RotateCcw size={14} /> Undo alignment check</> : <><Check size={14} /> Mark alignment as good</>}
                </button>
              </div>
            </div>
          </div>
        </Step>

        <Step number="02" title="Signal and impedance calibration" status={calibration}>
          <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(280px,480px)_1fr]">
            <CalibrationVisual />
            <div>
              <ol className="list-decimal space-y-2 pl-5 text-sm leading-7 text-white/65">
                <li>Check power, sensor contact and reference/ground according to the device instructions.</li>
                <li>If the device supports impedance measurement, use the manufacturer’s tool and acceptance criteria. A trace or successful device check is not an impedance test.</li>
                <li>Inspect a resting baseline for flat or disconnected channels, clipping, movement and mains interference. Fix contacts before recording.</li>
              </ol>
              <RunControls name="Calibration" status={calibration} demo={demo} onRun={() => run(setCalibration)} onComplete={() => setCalibration('done')} onReset={() => setCalibration('idle')} />
            </div>
          </div>
        </Step>

        <Step number="03" title="Hardware and stimulus synchronization" status={sync}>
          <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(280px,480px)_1fr]">
            <SyncVisual />
            <div>
              <ol className="list-decimal space-y-2 pl-5 text-sm leading-7 text-white/65">
                <li>Attach a supported hardware trigger or a photodiode to the display, and record it alongside the EEG.</li>
                <li>Flash a test target repeatedly; measure the delay (Δt) from command to actual onset and its jitter.</li>
                <li>Repeat at the end of the session to check clock drift. Align epochs to measured onsets, not browser timestamps.</li>
              </ol>
              <RunControls name="Synchronization" status={sync} demo={demo} onRun={() => run(setSync)} onComplete={() => setSync('done')} onReset={() => setSync('idle')} />
            </div>
          </div>
        </Step>
      </div>

      <div className="mt-8 border border-white/10 bg-[#0a0a0b] p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-heading text-xl font-semibold">Continue to the workspace</h2>
          <p className="mono-label text-[0.6rem] text-white/55">{completed} / 3 steps completed</p>
        </div>
        <div className="mt-4 h-1 bg-white/10" aria-hidden="true"><div className="h-full bg-[#0369A1] transition-all" style={{ width: `${(completed / 3) * 100}%` }} /></div>
        {error && <p role="alert" className="mt-3 text-sm text-red-300">{error}</p>}
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button type="button" onClick={demo ? onDemo : onPreview} disabled={!canContinue} className="focus-ring flex items-center gap-3 bg-[#0369A1] px-5 py-4 mono-label text-[0.6rem] text-white hover:bg-[#075985] disabled:cursor-not-allowed disabled:opacity-40">
            {busy ? 'Starting…' : demo ? 'Open demo workspace' : 'Start live EEG preview'} <ArrowRight size={16} />
          </button>
          {demo && <button type="button" onClick={onDemo} disabled={busy} className="focus-ring text-xs text-white/55 underline underline-offset-4 hover:text-white disabled:opacity-40">Skip checks (demo only)</button>}
        </div>
        <p className="mt-4 text-xs leading-5 text-white/45">
          {!allDone && 'Complete alignment, calibration and synchronization to continue. '}
          {demo
            ? 'Demo shows synthetic data only; it does not connect a headset or save to MongoDB.'
            : `Live preview records to MongoDB. Operator confirmations do not make it suitable for P300 decisions.${checked ? '' : ' Return to device setup and check a headset first.'}`}
        </p>
      </div>
    </main>
  );
}
