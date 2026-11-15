import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Activity, ArrowLeft, ArrowRight, Bluetooth, Check, ChevronRight, Radio, RefreshCw, ShieldAlert, Square } from 'lucide-react';
import { AlertDialog, AlertDialogAction, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import core4Image from '../assets/headsets/core-4.png';
import hybridBlackImage from '../assets/headsets/hybrid-black.png';
import core8Image from '../assets/headsets/core-8.png';
import nautilusProImage from '../assets/headsets/nautilus-pro.png';
import nautilusResearchImage from '../assets/headsets/nautilus-research.png';
import { createDemoExperiment, DEMO_CHANNEL_LABELS } from '../lib/p300-demo';
import { COMMUNICATION_MENU, getFlashingRounds, getMenuPath } from '../lib/communication-menu';
import Calibration from '../components/Calibration';

const API_URL = (import.meta.env.VITE_EEG_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const CLOUD_SPEECH = Boolean(import.meta.env.VITE_EEG_SPEECH_API_URL);
const SPEECH_API_URL = (import.meta.env.VITE_EEG_SPEECH_API_URL || API_URL).replace(/\/$/, '');
const HEADSETS = [
  { id: 'core-4', name: 'BCI Core-4', family: 'Unicorn series', channels: '4 EEG channels', connection: 'Bluetooth Low Energy', image: core4Image },
  { id: 'hybrid-black', name: 'Hybrid Black', family: 'Unicorn series', channels: '8 EEG channels', connection: 'Bluetooth', image: hybridBlackImage },
  { id: 'core-8', name: 'BCI Core-8', family: 'Unicorn series', channels: '8 EEG channels', connection: 'Bluetooth Low Energy', image: core8Image },
  { id: 'nautilus-pro', name: 'g.Nautilus PRO Flexible', family: 'g.Nautilus series', channels: 'Device-reported channels', connection: 'g.tec Device Service', image: nautilusProImage },
  { id: 'nautilus-research', name: 'g.Nautilus RESEARCH', family: 'g.Nautilus series', channels: 'Device-reported channels', connection: 'g.tec Device Service', image: nautilusResearchImage },
];

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error('Cannot reach the local acquisition service. Start the backend on this computer.');
  }
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'The request could not be completed.');
  return body;
}

function Trace({ samples, index, markers = [], endIndex = 0, samplingRate = 250 }) {
  const values = samples.map((sample) => sample[index]);
  const max = Math.max(10, ...values.map((value) => Math.abs(value)));
  const span = Math.max(1, values.length - 1);
  const first = endIndex - values.length;
  const toX = (sampleIndex) => ((sampleIndex - first) / span) * 300;
  const points = values.map((value, i) => `${values.length < 2 ? 0 : (i / span) * 300},${32 - (value / max) * 27}`).join(' ');
  return (
    <svg viewBox="0 0 300 64" preserveAspectRatio="none" className="h-12 w-full" aria-hidden="true">
      {markers.map((marker) => marker.target && (
        <rect key={`w${marker.index}`} x={toX(marker.index + 0.25 * samplingRate)} y="0" width={(0.25 * samplingRate / span) * 300} height="64" fill="rgba(0,255,135,.18)" />
      ))}
      <path d="M0 32H300" stroke="rgba(255,255,255,.1)" strokeWidth="1" />
      {markers.map((marker) => (
        <line key={marker.index} x1={toX(marker.index)} x2={toX(marker.index)} y1="0" y2="64" stroke={marker.target ? '#00FF87' : 'rgba(255,255,255,.5)'} strokeWidth={marker.target ? 2 : 1} strokeDasharray={marker.target ? undefined : '2 3'} vectorEffect="non-scaling-stroke" />
      ))}
      {points && <polyline points={points} fill="none" stroke="#5487ff" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />}
    </svg>
  );
}

const ERP_COLORS = ['#38e890', '#95ed43', '#f4d84a', '#39cbd5', '#698bff', '#ff7777', '#ae72ff', '#f35daf'];

function ErpGraph({ item, average }) {
  const channels = average?.channels || [];
  const toX = (seconds) => 40 + (seconds / 0.7) * 330;
  const toY = (value) => 120 - value * 2.5;
  return (
    <svg viewBox="0 0 390 220" className="erp-graph mt-2 w-full" role="img" aria-label={`${item}: ${channels.length} electrode averages from ${average?.count || 0} flashes`}>
      <rect x={toX(0.25)} y="20" width={toX(0.5) - toX(0.25)} height="150" fill="rgba(0,255,135,.06)" />
      {[-20, 0, 20, 40].map((value) => (
        <g key={value}>
          <line x1="40" x2="370" y1={toY(value)} y2={toY(value)} stroke={value === 0 ? '#64748b' : '#ffffff15'} />
          <text x="33" y={toY(value) + 5} textAnchor="end" fontSize="16" fill="#8e99ac">{value}</text>
        </g>
      ))}
      {[0, 0.35, 0.7].map((time) => (
        <g key={time}>
          <line x1={toX(time)} x2={toX(time)} y1="20" y2="170" stroke="#ffffff15" />
          <text x={toX(time)} y="188" textAnchor="middle" fontSize="16" fill="#8e99ac">{time}</text>
        </g>
      ))}
      {channels.map((wave, channel) => (
        <polyline key={channel} data-electrode={channel} points={wave.map((value, i) => `${40 + (i / Math.max(1, wave.length - 1)) * 330},${toY(value)}`).join(' ')} fill="none" stroke={ERP_COLORS[channel % ERP_COLORS.length]} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      ))}
      <text x="205" y="214" textAnchor="middle" fontSize="16" fill="#8e99ac">Time after flash (s)</text>
      <text x="8" y="14" fontSize="16" fill="#8e99ac">µV</text>
      <text x={toX(0.25) + 5} y="36" fontSize="16" fill="#38e890">P300</text>
    </svg>
  );
}

function SignalPanel({ device, samples, lastFrame, demoTarget, markers, endIndex }) {
  const fitChannels = device.channel_count <= 8;
  return (
    <section aria-label="Electrode signals" style={{ '--signal-rows': device.channel_count }} className={`min-w-0 border border-white/10 bg-[#080a0f] lg:sticky lg:top-0 ${fitChannels ? 'signal-panel-fit' : 'lg:max-h-[calc(100dvh-72px)] lg:overflow-y-auto'}`}>
      <div className="sticky top-0 z-[1] shrink-0 border-b border-white/10 bg-[#080a0f] px-3 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="mono-label text-[#00FF87]"><span className="live-dot mr-2 inline-block h-1.5 w-1.5 rounded-full bg-[#00FF87]" />{device.simulated ? 'Simulated signal' : 'Live signal'}</p>
            <p className="mt-2 text-xs text-white/45">{device.channel_count} channels · {device.sampling_rate_hz} Hz · {device.unit}</p>
          </div>
          <Activity size={20} className="text-[#38BDF8]" aria-hidden="true" />
        </div>
        <p className="mt-3 text-xs text-white/40">{device.simulated ? 'Synthetic demo data' : 'Filtered 0.5–30 Hz'} · auto-scaled traces</p>
        {device.simulated && demoTarget && <p className="mt-3 text-xs text-amber-200">Simulated attended item: <strong>{demoTarget}</strong></p>}
        {device.simulated && (
          <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.65rem] text-white/45">
            <span className="flex items-center gap-1.5"><span className="inline-block h-3 border-l border-dashed border-white/40" /> Flash</span>
            <span className="flex items-center gap-1.5"><span className="inline-block h-3 border-l border-[#00FF87]" /><span className="inline-block h-3 w-3 bg-[#00FF87]/20" /> Attended flash · P300 window</span>
          </p>
        )}
      </div>
      <div className="signal-rows divide-y divide-white/10">
        {device.channel_indices.map((channel, index) => (
          <div key={channel} className="signal-row min-w-0 px-3 py-2">
            <div className="flex shrink-0 justify-between gap-2 mono-label text-[0.55rem] text-white/50">
              <span>EEG {channel + 1}{device.channel_labels && ` · ${device.channel_labels[index]}`}</span>
              <span>{samples.length ? `${samples[samples.length - 1][index].toFixed(1)} ${device.unit}` : 'Waiting'}</span>
            </div>
            <Trace samples={samples} index={index} markers={device.simulated ? markers : []} endIndex={endIndex} samplingRate={device.sampling_rate_hz} />
          </div>
        ))}
      </div>
      <div className="shrink-0 border-t border-white/10 px-3 py-3 text-[0.65rem] leading-relaxed text-white/40">
        {device.simulated ? 'Synthetic channels follow the reference montage.' : `Viewer buffer drops: ${lastFrame?.dropped_blocks_total ?? 0}. Channel numbers are not electrode locations.`}
      </div>
    </section>
  );
}

export default function Acquisition() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [model, setModel] = useState('hybrid-black');
  const [samplingRate, setSamplingRate] = useState(250);
  const [devices, setDevices] = useState([]);
  const [serial, setSerial] = useState('');
  const [checked, setChecked] = useState(null);
  const [demo, setDemo] = useState(false);
  const [phase, setPhase] = useState('idle');
  const [error, setError] = useState('');
  const [connectionError, setConnectionError] = useState('');
  const [samples, setSamples] = useState([]);
  const [lastFrame, setLastFrame] = useState(null);
  const [menu, setMenu] = useState(COMMUNICATION_MENU);
  const [demoTarget, setDemoTarget] = useState(null);
  const [highlighted, setHighlighted] = useState(null);
  const [flashing, setFlashing] = useState(false);
  const [demoProgress, setDemoProgress] = useState(0);
  const [demoEvidence, setDemoEvidence] = useState({});
  const [demoResult, setDemoResult] = useState(null);
  const [resultSeconds, setResultSeconds] = useState(0);
  const [markers, setMarkers] = useState([]);
  const [endIndex, setEndIndex] = useState(0);
  const [demoAverages, setDemoAverages] = useState({});
  const [speechEnabled, setSpeechEnabled] = useState(true);
  const [speechError, setSpeechError] = useState('');
  const [speechToken, setSpeechToken] = useState('');
  const socketRef = useRef(null);
  const demoTimerRef = useRef(null);
  const demoExperimentRef = useRef(null);
  const enteringWorkspaceRef = useRef(false);
  const speechAudioRef = useRef(null);
  const speechAbortRef = useRef(null);
  const speechUrlRef = useRef(null);
  const spokenResultRef = useRef(null);
  const selected = HEADSETS.find((headset) => headset.id === model);
  const nautilus = model.startsWith('nautilus');
  const busy = ['scanning', 'checking', 'starting', 'stopping'].includes(phase);
  const collecting = phase === 'collecting' || phase === 'stopping';
  const selection = { model, serial, sampling_rate_hz: samplingRate };
  const menuItems = menu.children.map((item) => item.label);
  const flashingRounds = getFlashingRounds(menu);

  useEffect(() => () => {
    if (socketRef.current) socketRef.current.close();
    if (demoTimerRef.current) clearInterval(demoTimerRef.current);
    if (speechAbortRef.current) speechAbortRef.current.abort();
    if (speechUrlRef.current) URL.revokeObjectURL(speechUrlRef.current);
  }, []);

  function cancelSpeech() {
    if (speechAbortRef.current) speechAbortRef.current.abort();
    speechAbortRef.current = null;
    if (speechAudioRef.current) {
      speechAudioRef.current.pause();
      speechAudioRef.current.removeAttribute('src');
      speechAudioRef.current.load();
    }
    if (speechUrlRef.current) URL.revokeObjectURL(speechUrlRef.current);
    speechUrlRef.current = null;
  }

  function retrySpeech() {
    speechAudioRef.current?.play().then(() => setSpeechError('')).catch(() => setSpeechError('Playback failed. Check your audio settings.'));
  }

  function selectModel(id) {
    setModel(id);
    setSamplingRate(250);
    setDevices([]);
    setSerial('');
    setChecked(null);
    setError('');
  }

  async function scan() {
    setPhase('scanning');
    setError('');
    setChecked(null);
    setSerial('');
    setDevices([]);
    try {
      const result = await request(`/api/headsets/${model}/devices`);
      setDevices(result.devices);
      if (result.devices.length === 1) setSerial(result.devices[0].serial);
      if (!result.devices.length) setConnectionError('No headset found. Check power, pairing, drivers and try scanning again.');
    } catch (err) {
      setConnectionError(err.message);
    } finally {
      setPhase('idle');
    }
  }

  async function checkDevice() {
    setPhase('checking');
    setError('');
    setChecked(null);
    try {
      const result = await request('/api/headsets/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selection),
      });
      setChecked(result.device);
    } catch (err) {
      setConnectionError(err.message);
    } finally {
      setPhase('idle');
    }
  }

  function collect(useDemo = demo) {
    setPhase('starting');
    setError('');
    setSamples([]);
    setLastFrame(null);
    if (useDemo) {
      setDemo(true);
      const channelCount = model === 'core-4' ? 4 : 8;
      const device = {
        model: selected.name,
        channel_count: channelCount,
        channel_indices: Array.from({ length: channelCount }, (_, index) => index),
        sampling_rate_hz: samplingRate,
        unit: 'uV',
        simulated: true,
        ...(channelCount === DEMO_CHANNEL_LABELS.length && { channel_labels: DEMO_CHANNEL_LABELS }),
      };
      demoExperimentRef.current = createDemoExperiment(COMMUNICATION_MENU.children.map((item) => item.label), channelCount, samplingRate);
      setMenu(COMMUNICATION_MENU);
      setDemoTarget(null);
      setHighlighted(null);
      setFlashing(false);
      setDemoProgress(0);
      setDemoEvidence({});
      setDemoResult(null);
      setMarkers([]);
      setDemoAverages({});
      setChecked(device);
      enteringWorkspaceRef.current = true;
      setPhase('collecting');
      demoTimerRef.current = setInterval(() => {
        const result = demoExperimentRef.current.nextFrame();
        setSamples((previous) => [...previous, ...result.samples].slice(-samplingRate * 2));
        setEndIndex(result.endIndex);
        setMarkers((previous) => [...previous, ...result.markers].filter((marker) => marker.index > result.endIndex - samplingRate * 2));
        setDemoAverages(result.averages);
        setHighlighted(result.highlighted);
        setDemoProgress(result.scored);
        setDemoEvidence(result.evidence);
        if (result.complete) {
          setFlashing(false);
          setDemoResult({ choice: result.decision });
        }
      }, 100);
      return;
    }
    const url = new URL(`${API_URL}/ws/eeg`);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(url);
    socketRef.current = socket;
    let stopped = false;
    let reportedError = false;
    let started = false;
    socket.onopen = () => socket.send(JSON.stringify({ action: 'start', ...selection }));
    socket.onmessage = (event) => {
      let frame;
      try {
        frame = JSON.parse(event.data);
      } catch {
        reportedError = true;
        setError('The acquisition service returned an invalid message.');
        socket.close();
        return;
      }
      if (frame.type === 'started') {
        started = true;
        setChecked(frame);
        enteringWorkspaceRef.current = true;
        setPhase('collecting');
      } else if (frame.type === 'eeg') {
        if (!Array.isArray(frame.samples) || frame.samples.some((row) =>
          !Array.isArray(row) || row.length !== frame.channel_count || row.some((value) => !Number.isFinite(value)))) {
          reportedError = true;
          setError('Invalid EEG data received. Collection has been stopped.');
          socket.close();
          return;
        }
        setSamples((previous) => [...previous, ...frame.samples].slice(-frame.sampling_rate_hz * 2));
        setLastFrame(frame);
      } else if (frame.type === 'error') {
        reportedError = true;
        setError(frame.message || 'Acquisition failed.');
        socket.close();
      } else if (frame.type === 'stopped') {
        stopped = true;
        socket.close();
      }
    };
    socket.onerror = () => {
      reportedError = true;
      setError('WebSocket connection failed. Check that the local backend is running.');
    };
    socket.onclose = () => {
      if (socketRef.current === socket) socketRef.current = null;
      enteringWorkspaceRef.current = false;
      setPhase('idle');
      setChecked(null);
      if (started) navigate('/acquisition');
      if (!stopped && !reportedError) setError('The stream disconnected. Check the headset and scan again.');
    };
  }

  function stop() {
    cancelSpeech();
    setSpeechError('');
    if (demoTimerRef.current) {
      clearInterval(demoTimerRef.current);
      demoTimerRef.current = null;
      demoExperimentRef.current = null;
      enteringWorkspaceRef.current = false;
      setFlashing(false);
      setDemoResult(null);
      setDemoTarget(null);
      setHighlighted(null);
      setPhase('idle');
      setChecked(null);
      navigate('/acquisition');
      return;
    }
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      setPhase('stopping');
      socket.send(JSON.stringify({ action: 'stop' }));
    }
  }

  function resetDemoSignals(nextMenu) {
    setMenu(nextMenu);
    setDemoProgress(0);
    setDemoEvidence({});
    setDemoAverages({});
    setMarkers([]);
    setSamples([]);
    setEndIndex(0);
    setHighlighted(null);
    setDemoTarget(null);
  }

  function changeMenu(nextMenu, flash = false) {
    if (!checked.simulated) {
      setMenu(nextMenu);
      return;
    }
    const experiment = createDemoExperiment(nextMenu.children.map((item) => item.label), checked.channel_count, checked.sampling_rate_hz, Math.random, getFlashingRounds(nextMenu));
    demoExperimentRef.current = experiment;
    if (flash) experiment.start();
    resetDemoSignals(nextMenu);
    setDemoTarget(flash ? experiment.target : null);
    setFlashing(flash);
  }

  function stopDemoFlashing() {
    demoExperimentRef.current.stop();
    setFlashing(false);
    setHighlighted(null);
    setDemoTarget(null);
    setDemoProgress(0);
  }

  useEffect(() => {
    if (!demoResult || phase !== 'collecting' || pathname !== '/acquisition/workspace') return;
    const chosen = menu.children.find((item) => item.label === demoResult.choice);
    const finalChoice = chosen && !chosen.children;
    const seconds = finalChoice ? 25 : 5;
    const deadline = Date.now() + seconds * 1000;
    setResultSeconds(seconds);
    const countdown = setInterval(() => setResultSeconds(Math.max(0, Math.ceil((deadline - Date.now()) / 1000))), 250);
    const advance = setTimeout(() => {
      setDemoResult(null);
      if (finalChoice) {
        changeMenu(COMMUNICATION_MENU);
      } else {
        changeMenu(chosen || menu, true);
      }
    }, seconds * 1000);
    return () => {
      clearInterval(countdown);
      clearTimeout(advance);
    };
  }, [demoResult, phase, pathname, menu, checked]);

  useEffect(() => {
    if (!speechEnabled || !checked?.simulated || !demoResult?.choice || phase !== 'collecting' || pathname !== '/acquisition/workspace' || spokenResultRef.current === demoResult) return;
    if (CLOUD_SPEECH && !speechToken.trim()) {
      setSpeechError('Enter the cloud demo speech access token before starting flashing.');
      return;
    }
    const menuPath = getMenuPath(COMMUNICATION_MENU, menu);
    const choiceIndex = menu.children.findIndex((item) => item.label === demoResult.choice);
    if (!menuPath || choiceIndex < 0) {
      setSpeechError('Could not identify the demo selection for speech.');
      return;
    }
    spokenResultRef.current = demoResult;
    cancelSpeech();
    setSpeechError('');
    const controller = new AbortController();
    speechAbortRef.current = controller;
    async function speak() {
      try {
        const response = await fetch(`${SPEECH_API_URL}/api/demo/speech`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(CLOUD_SPEECH && { Authorization: `Bearer ${speechToken.trim()}` }),
          },
          body: JSON.stringify({ path: [...menuPath, choiceIndex] }),
          signal: controller.signal,
        });
        if (!response.ok) {
          const body = await response.json();
          throw new Error(typeof body.detail === 'string' ? body.detail : 'Demo speech could not be generated.');
        }
        const audio = await response.blob();
        if (controller.signal.aborted) return;
        const player = speechAudioRef.current;
        if (!player) return;
        speechUrlRef.current = URL.createObjectURL(audio);
        player.src = speechUrlRef.current;
        try {
          await player.play();
        } catch {
          if (!controller.signal.aborted) setSpeechError('Automatic playback was blocked. Select Play speech to hear it.');
        }
      } catch (err) {
        if (!controller.signal.aborted) setSpeechError(err.message || 'Demo speech failed. Check the backend connection.');
      }
    }
    speak();
  }, [demoResult, speechEnabled, checked, menu, phase, pathname, speechToken]);

  useEffect(() => {
    if (phase === 'collecting' && pathname === '/acquisition/workspace') {
      enteringWorkspaceRef.current = false;
    } else if (phase === 'collecting' && enteringWorkspaceRef.current) {
      navigate('/acquisition/workspace');
    } else if (phase === 'collecting') {
      stop();
    } else if (pathname === '/acquisition/workspace' && !collecting && phase !== 'starting') {
      navigate('/acquisition', { replace: true });
    } else if (phase === 'starting' && pathname !== '/acquisition/calibration' && socketRef.current) {
      socketRef.current.close();
    }
  }, [pathname, collecting, phase, navigate]);

  return (
    <div className="min-h-screen bg-[#07111B] text-[#F8FAFC]">
      <header className="flex h-[72px] items-center justify-between border-b border-white/10 px-[clamp(20px,4vw,48px)]">
        <Link to="/" className="focus-ring mono-label text-white">NeuronVision</Link>
        <Link to="/" className="focus-ring flex items-center gap-2 text-xs text-white/50 hover:text-white"><ArrowLeft size={14} /> Back to home</Link>
      </header>

      {collecting && checked ? (
        <main className={`grid min-h-[calc(100vh-72px)] items-start ${checked.simulated ? 'lg:grid-cols-[minmax(0,2fr)_minmax(0,5fr)_minmax(0,3fr)]' : 'lg:grid-cols-[minmax(0,1fr)_minmax(0,4fr)]'}`}>
          <SignalPanel device={checked} samples={samples} lastFrame={lastFrame} demoTarget={demoTarget} markers={markers} endIndex={endIndex} />
          <section aria-label="Communication menu" className="flex min-w-0 flex-col px-6 py-8 xl:px-8">
            <div className="flex flex-wrap items-start justify-between gap-5">
              <div>
                <p className="mono-label text-[#38BDF8]">{checked.simulated ? 'Demo mode' : 'Acquisition'} / {checked.model}</p>
                <h1 className="mt-4 font-heading text-3xl font-semibold tracking-tight sm:text-4xl">Signal workspace</h1>
                {!checked.simulated && <p className="mt-3 max-w-xl text-sm leading-6 text-white/50">Live filtered EEG is being recorded. This workspace is an interface preview, not a communication or medical device.</p>}
              </div>
              <button onClick={stop} disabled={phase === 'stopping'} className="focus-ring flex items-center gap-2 border border-white/25 px-4 py-3 mono-label text-[0.6rem] hover:border-white disabled:opacity-50">
                <Square size={13} /> {phase === 'stopping' ? 'Stopping' : 'Stop collection'}
              </button>
            </div>
            {!checked.simulated && (
              <div className="mt-8 flex gap-3 border border-amber-400/30 bg-amber-400/5 p-4 text-sm leading-6 text-amber-100/80">
                <ShieldAlert className="mt-1 shrink-0" size={18} />
                <p><strong>P300 decoding is not active.</strong> Stimulus timing, calibration and decision thresholds have not been validated. Do not rely on this preview for communication or emergency requests.</p>
              </div>
            )}
            {checked.simulated && (
              <div className="mt-8 flex flex-wrap items-center gap-5 border border-white/15 p-4">
                <button type="button" onClick={flashing ? stopDemoFlashing : () => changeMenu(menu, true)} className="focus-ring border border-[#7dd3fc] px-5 py-3 text-sm text-white hover:bg-[#075985]/20">
                  {flashing ? 'Stop flashing' : 'Start flashing'}
                </button>
                <div className="min-w-[180px] flex-1">
                  <div className="flex justify-between text-xs text-white/55"><span>Flashes · {flashingRounds} rounds</span><span>{demoProgress} / {menuItems.length * flashingRounds}</span></div>
                  <div className="mt-2 h-1.5 bg-white/10"><div className="h-full bg-[#0369A1] transition-all" style={{ width: `${(demoProgress / (menuItems.length * flashingRounds)) * 100}%` }} /></div>
                </div>
                <p className="w-full text-[0.65rem] text-white/35">Flashing stimulus—stop if uncomfortable.</p>
                <button type="button" onClick={() => { cancelSpeech(); setSpeechError(''); setSpeechEnabled(!speechEnabled); }} aria-pressed={speechEnabled} className="focus-ring border border-white/25 px-4 py-2 text-sm text-white hover:border-white">
                  {speechEnabled ? 'Disable demo speech' : 'Enable demo speech'}
                </button>
                {speechEnabled && <p className="text-xs text-white/50">Synthetic menu phrases are sent to ElevenLabs for speech.</p>}
                {CLOUD_SPEECH && speechEnabled && (
                  <label className="w-full text-xs text-white/65">
                    Cloud demo speech access token
                    <input type="password" autoComplete="off" value={speechToken} onChange={(event) => { cancelSpeech(); setSpeechToken(event.target.value); setSpeechError(''); }} className="focus-ring mt-2 block w-full border border-white/20 bg-transparent p-3 text-white" />
                    <span className="mt-2 block text-white/40">Use the server's EEG_DEMO_TOKEN, not the ElevenLabs API key. Kept in memory only.</span>
                  </label>
                )}
              </div>
            )}
            {error && <p role="alert" className="mt-4 text-sm text-red-300">{error}</p>}
            {speechEnabled && checked.simulated && (
              <>
                <audio ref={speechAudioRef} hidden />
                {speechError && !demoResult && (
                  <div className="mt-4">
                    <p role="alert" className="text-sm text-red-300">{speechError}</p>
                    {speechUrlRef.current && <button type="button" className="focus-ring mt-2 border border-white/25 px-4 py-2 text-sm" onClick={retrySpeech}>Play speech</button>}
                  </div>
                )}
              </>
            )}
            <div className="mt-10 flex items-end justify-between border-b border-white/10 pb-4">
              <div><p className="mono-label text-white/35">{checked.simulated ? 'P300 speller' : 'Manual menu preview'}</p><h2 className="mt-2 font-heading text-2xl">{menu === COMMUNICATION_MENU ? 'What would you like to communicate?' : menu.label}</h2></div>
              {menu !== COMMUNICATION_MENU && <button disabled={flashing} className="focus-ring text-xs text-white/55 hover:text-white disabled:opacity-30" onClick={() => changeMenu(COMMUNICATION_MENU)}>Back to start</button>}
            </div>
            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {menu.children.map((node) => {
                const item = node.label;
                const lit = highlighted === item;
                const evidence = demoEvidence[item];
                return (
                  <button key={item} disabled={flashing} onClick={() => node.children && changeMenu(node)} className={`focus-ring flex min-h-[140px] flex-col border p-5 text-left transition-colors duration-75 ${lit ? 'border-[#bae6fd] bg-[#0369A1] text-white' : 'border-white/10 bg-white/[0.02] hover:border-[#38BDF8]'}`}>
                    <span className="flex items-center justify-between gap-2 font-heading text-2xl font-semibold">{item}{node.children && <ChevronRight size={18} className={lit ? 'text-white' : 'text-white/30'} />}</span>
                    {checked.simulated && (
                      <>
                        <div className="mt-auto pt-3">
                          <div className="flex gap-1" aria-hidden="true">
                            {Array.from({ length: flashingRounds }, (_, n) => <span key={n} className={`h-1.5 flex-1 ${n < (evidence?.positive || 0) ? (lit ? 'bg-white' : 'bg-[#00FF87]') : 'bg-white/15'}`} />)}
                          </div>
                          <p className={`mt-2 text-[0.65rem] ${lit ? 'text-white/80' : 'text-white/45'}`}>{evidence?.positive || 0} / {flashingRounds} P300 hits · {demoAverages[item]?.count || 0} {demoAverages[item]?.count === 1 ? 'flash' : 'flashes'} averaged</p>
                        </div>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
            {!checked.simulated && <p className="mt-4 text-xs text-white/35">Buttons are manually controlled; they do not represent decoded EEG choices.</p>}
          </section>
          {checked.simulated && (
            <section aria-labelledby="erp-heading" style={{ '--erp-rows': Math.ceil(menuItems.length / 2) }} className="erp-panel min-w-0 border border-white/10 bg-[#080a0f] lg:sticky lg:top-0">
              <div className="shrink-0 border-b border-white/10 bg-[#080a0f] p-3">
                <h2 id="erp-heading" className="font-heading text-lg font-semibold">Averaged responses by item</h2>
                <p className="mt-2 text-xs text-white/45">Electrode averages · shared amplitude scale</p>
                <div className="mt-3 flex flex-wrap gap-x-3 gap-y-2 text-xs">
                  {checked.channel_indices.map((channel, index) => (
                    <span key={channel} className="flex items-center gap-2 text-white/65"><span className="h-0.5 w-5" style={{ backgroundColor: ERP_COLORS[index % ERP_COLORS.length] }} />{checked.channel_labels?.[index] || `EEG ${channel + 1}`}</span>
                  ))}
                </div>
              </div>
              <div className="erp-grid grid gap-3 p-3 sm:grid-cols-2">
                {menuItems.map((item) => (
                  <figure key={item} className="min-w-0 border border-white/10 bg-[#080a0f] p-2">
                    <figcaption className="flex shrink-0 flex-wrap items-center justify-between gap-x-2 gap-y-1">
                      <span className="font-heading text-sm font-semibold">{item}</span>
                      <span className="text-[0.6rem] text-white/45">{demoAverages[item]?.count || 0} / {flashingRounds}</span>
                    </figcaption>
                    <ErpGraph item={item} average={demoAverages[item]} />
                  </figure>
                ))}
              </div>
            </section>
          )}
        </main>
      ) : pathname === '/acquisition/calibration' ? (
        <Calibration
          key={`${selected.name}-${demo}-${Boolean(checked)}`}
          model={selected.name}
          demo={demo}
          checked={checked}
          busy={busy}
          error={error}
          onBack={() => navigate('/acquisition')}
          onDemo={() => collect(true)}
          onPreview={() => collect(false)}
        />
      ) : (
        <main className="mx-auto max-w-[1400px] px-[clamp(20px,5vw,64px)] pb-20 pt-12 sm:pt-20">
          <div className="max-w-3xl">
            <p className="mono-label text-[#38BDF8]">01 / Device setup</p>
            <h1 className="mt-5 font-heading text-4xl font-semibold tracking-tight sm:text-6xl">Start acquisition<span className="text-[#38BDF8]">.</span></h1>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-white/50 sm:text-base">Choose your headset, check its connection, and start collecting filtered EEG. The acquisition service must run on the computer connected to the headset.</p>
          </div>
          <div className="mt-12 grid gap-10 lg:grid-cols-[minmax(0,1.7fr)_minmax(300px,1fr)]">
            <section>
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <h2 className="mono-label text-white/65">Select a headset</h2>
                <span className="mono-label text-[0.55rem] text-white/30">05 models</span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {HEADSETS.map((headset) => (
                  <button
                    key={headset.id}
                    type="button"
                    disabled={busy}
                    onClick={() => selectModel(headset.id)}
                    aria-pressed={model === headset.id}
                    className={`focus-ring overflow-hidden border bg-white p-5 text-left text-[#111] transition-colors disabled:opacity-50 ${model === headset.id ? 'border-[#38BDF8] ring-2 ring-[#38BDF8]' : 'border-white hover:border-[#38BDF8]'}`}
                  >
                    <span className="flex justify-between mono-label text-[0.55rem] text-black/50">{headset.family}{model === headset.id && <Check size={16} className="text-[#38BDF8]" />}</span>
                    <img src={headset.image} alt="" className="mx-auto mt-3 h-40 w-full object-contain" />
                    <span className="mt-4 block font-heading text-lg font-semibold">{headset.name}</span>
                    <span className="mt-2 block text-xs text-black/55">{headset.channels} · {headset.connection}</span>
                  </button>
                ))}
              </div>
              <p className="mt-4 text-xs leading-5 text-white/35">Core and g.Nautilus adapters are experimental and require hardware validation. g.Nautilus variants are user-selected, not independently identified.</p>
            </section>
            <section className="h-fit border border-white/10 bg-[#0a0a0b] p-6 sm:p-8">
              <p className="mono-label text-[#38BDF8]">02 / Connection</p>
              <h2 className="mt-4 font-heading text-xl font-semibold">Connect your device</h2>
              <button type="button" disabled={busy} aria-pressed={demo} onClick={() => { setDemo(!demo); setChecked(null); setError(''); }} className={`focus-ring mt-5 w-full border px-4 py-3 text-sm disabled:opacity-50 ${demo ? 'border-[#38BDF8] bg-[#0369A1]/15 text-white' : 'border-white/20 text-white hover:border-white'}`}>
                {demo ? 'Demo mode on — switch off' : 'Demo mode'}
              </button>
              {demo && <p role="status" className="mt-3 text-xs leading-5 text-amber-200">Demo mode bypasses the headset and shows synthetic data only. Demo speech sends synthetic menu phrases to ElevenLabs unless disabled.</p>}
              <div className="mt-5 flex gap-3 border border-white/10 bg-white/[0.02] p-4">
                {nautilus ? <Radio size={18} className="mt-0.5 shrink-0 text-[#5785ff]" /> : <Bluetooth size={18} className="mt-0.5 shrink-0 text-[#5785ff]" />}
                <p className="text-xs leading-6 text-white/55">{nautilus ? 'Power on your headset and connect its base station and g.tec Device Service on this computer.' : 'Turn on Bluetooth, pair the headset in Windows if required, and power it on.'}</p>
              </div>
              {nautilus && (
                <label className="mt-5 block text-xs text-white/55">Sampling rate
                  <select value={samplingRate} disabled={busy} onChange={(event) => { setSamplingRate(Number(event.target.value)); setChecked(null); }} className="focus-ring mt-2 w-full border border-white/15 bg-[#111] p-3 text-sm text-white">
                    <option value={250}>250 Hz</option><option value={500}>500 Hz</option>
                  </select>
                </label>
              )}
              <button disabled={busy || demo} onClick={scan} className="focus-ring mt-5 flex w-full items-center justify-between border border-white/20 px-4 py-3 text-sm hover:border-white disabled:opacity-50">
                {phase === 'scanning' ? 'Scanning…' : `Find ${selected.name}`} <RefreshCw size={15} />
              </button>
              {devices.length > 0 && (
                <label className="mt-5 block text-xs text-white/55">Available device
                  <select value={serial} disabled={busy} onChange={(event) => { setSerial(event.target.value); setChecked(null); }} className="focus-ring mt-2 w-full border border-white/15 bg-[#111] p-3 text-sm text-white">
                    <option value="">Select a serial number</option>
                    {devices.map((device) => <option key={device.serial} value={device.serial}>{device.serial}</option>)}
                  </select>
                </label>
              )}
              <button disabled={!serial || busy || demo} onClick={checkDevice} className="focus-ring mt-4 w-full border border-white/20 px-4 py-3 text-sm hover:border-white disabled:cursor-not-allowed disabled:opacity-35">
                {phase === 'checking' ? 'Checking connection…' : 'Check connection'}
              </button>
              {checked && <p role="status" className="mt-4 flex gap-2 text-xs leading-5 text-[#00FF87]"><Check size={15} className="shrink-0" /> Device check passed. The connection will reopen when collection starts.</p>}
              {error && <p role="alert" className="mt-4 text-xs leading-5 text-red-300">{error}</p>}
              <button disabled={(!checked && !demo) || busy} onClick={() => navigate('/acquisition/calibration')} className="focus-ring mt-6 flex w-full items-center justify-between bg-[#0369A1] px-4 py-4 mono-label text-[0.6rem] text-white hover:bg-[#075985] disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-white/30">
                Collect data <ArrowRight size={16} />
              </button>
              <p className="mt-3 text-xs text-white/45">Next: calibration and synchronization guidance.</p>
              <p className="mt-4 text-xs leading-5 text-white/35">{demo ? 'Demo uses 4 channels for Core-4 and 8 for other models; g.Nautilus channel counts are illustrative.' : 'Collection requires MongoDB. Closing this page stops a session started here.'} No decoded decisions are produced.</p>
            </section>
          </div>
        </main>
      )}
      <AlertDialog open={Boolean(connectionError)} onOpenChange={(open) => { if (!open) setConnectionError(''); }}>
        <AlertDialogContent className="max-w-[calc(100%-2rem)] border-white/15 bg-[#111] text-white sm:max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>Headset connection failed</AlertDialogTitle>
            <AlertDialogDescription className="text-white/65">{connectionError}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction className="bg-[#0369A1] text-white hover:bg-[#075985]">OK</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <AlertDialog open={Boolean(demoResult)}>
        <AlertDialogContent onEscapeKeyDown={(event) => event.preventDefault()} className="max-w-[calc(100%-2rem)] border-white/15 bg-[#111] text-white sm:max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>{demoResult?.choice ? `You’ve chosen ${demoResult.choice}` : 'No clear choice'}</AlertDialogTitle>
            <AlertDialogDescription className="text-white/65">
              {demoResult?.choice
                ? `${menu.children.find((item) => item.label === demoResult.choice)?.children ? 'Opening the next menu' : 'Returning to the main menu'} in ${resultSeconds}s.`
                : `The evidence was inconclusive. Restarting this menu in ${resultSeconds}s.`}
            </AlertDialogDescription>
            {speechError && <p role="alert" className="text-sm text-red-300">{speechError}</p>}
            {speechEnabled && speechError && speechUrlRef.current && (
              <button type="button" className="focus-ring border border-white/25 px-4 py-2 text-sm" onClick={retrySpeech}>Play speech</button>
            )}
          </AlertDialogHeader>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
