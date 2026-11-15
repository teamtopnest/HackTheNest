const DEFAULT_ROUNDS = 4;
export const EPOCH_SECONDS = 0.7;
// Synthetic P300 scaling for the reference montage Fz, Cz, P3, Pz, P4, PO7, PO8, Oz (parietal maximum).
const MONTAGE_WEIGHTS = [0.6, 0.8, 0.9, 1, 0.9, 0.8, 0.8, 0.7];
export const DEMO_CHANNEL_LABELS = ['Fz', 'Cz', 'P3', 'Pz', 'P4', 'PO7', 'PO8', 'Oz'];

function gaussian(time, center, width) {
  return Math.exp(-0.5 * ((time - center) / width) ** 2);
}

function shuffled(items, random) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export function createDemoExperiment(items, channelCount, samplingRate, random = Math.random, rounds = DEFAULT_ROUNDS) {
  const target = items[Math.floor(random() * items.length)];
  const order = Array.from({ length: rounds }, () => shuffled(items, random)).flat();
  const noise = Array(channelCount).fill(0);
  const phases = Array.from({ length: channelCount }, () => random() * Math.PI * 2);
  const amplitudes = Array.from({ length: channelCount }, () => 2 + random() * 3);
  const weights = channelCount === MONTAGE_WEIGHTS.length
    ? MONTAGE_WEIGHTS
    : Array.from({ length: channelCount }, (_, c) => 0.6 + 0.4 * c / Math.max(1, channelCount - 1));
  const epochLength = Math.round(samplingRate * EPOCH_SECONDS);
  const scores = Object.fromEntries(items.map((item) => [item, { count: 0, sum: 0, positive: 0 }]));
  const sums = Object.fromEntries(items.map((item) => [item, new Float64Array(epochLength)]));
  const channelSums = Object.fromEntries(items.map((item) => [
    item, Array.from({ length: channelCount }, () => new Float64Array(epochLength)),
  ]));
  let averages = Object.fromEntries(items.map((item) => [item, { count: 0, wave: [], channels: [] }]));
  const baseline = [];
  const baselineRows = [];
  let sampleIndex = 0;
  let nextOnset = Math.round(samplingRate * 0.2);
  let orderIndex = 0;
  let event = null;
  let running = false;

  function nextFrame() {
    const count = samplingRate / 10;
    const frame = [];
    const markers = [];
    let decision = null;
    let complete = false;
    if (running && !event && orderIndex < order.length && sampleIndex >= nextOnset) {
      const base = baseline.length ? baseline.reduce((a, b) => a + b, 0) / baseline.length : 0;
      const item = order[orderIndex++];
      event = {
        item, onset: sampleIndex, base, total: 0, samples: 0,
        wave: new Float64Array(epochLength),
        channelBase: Array.from({ length: channelCount }, (_, channel) => baselineRows.length
          ? baselineRows.reduce((sum, row) => sum + row[channel], 0) / baselineRows.length : 0),
        channels: Array.from({ length: channelCount }, () => new Float64Array(epochLength)),
        // Trial-to-trial latency jitter (+/-30 ms) and amplitude variability, as in real single trials.
        latency: 0.33 + (random() - 0.5) * 0.06,
        gain: 0.8 + random() * 0.4,
      };
      markers.push({ index: sampleIndex, item, target: item === target });
    }

    for (let i = 0; i < count; i++) {
      const time = sampleIndex / samplingRate;
      const offset = event ? sampleIndex - event.onset : -1;
      const elapsed = offset / samplingRate;
      const row = noise.map((value, channel) => {
        noise[channel] = value * 0.94 + (random() - 0.5) * 2.4;
        const rhythm = amplitudes[channel] * Math.sin(2 * Math.PI * (8 + channel * 0.21) * time + phases[channel])
          + 2.5 * Math.sin(2 * Math.PI * (1.1 + channel * 0.09) * time + phases[channel] / 2);
        const evoked = elapsed >= 0 && elapsed < EPOCH_SECONDS
          ? -3 * gaussian(elapsed, 0.11, 0.035)
            + (event.item === target ? 26 * event.gain * gaussian(elapsed, event.latency, 0.08) : 0)
            - 2 * gaussian(elapsed, 0.6, 0.06)
          : 0;
        return rhythm + noise[channel] + evoked * weights[channel];
      });
      frame.push(row);
      const average = row.reduce((sum, value) => sum + value, 0) / channelCount;
      if (event && offset < epochLength) {
        event.wave[offset] = average - event.base;
        row.forEach((value, channel) => {
          event.channels[channel][offset] = value - event.channelBase[channel];
        });
      }
      if (event && elapsed >= 0.25 && elapsed < 0.5) {
        event.total += average;
        event.samples++;
      }
      baseline.push(average);
      baselineRows.push(row);
      if (baseline.length > samplingRate / 10) {
        baseline.shift();
        baselineRows.shift();
      }
      sampleIndex++;
    }

    const highlighted = event && sampleIndex - event.onset <= samplingRate * 0.2 ? event.item : null;
    if (event && sampleIndex - event.onset >= epochLength) {
      const score = event.total / event.samples - event.base;
      const entry = scores[event.item];
      entry.sum += score;
      entry.count++;
      if (score > 1) entry.positive++;
      const sum = sums[event.item];
      for (let k = 0; k < epochLength; k++) sum[k] += event.wave[k];
      const channels = channelSums[event.item].map((channelSum, channel) => {
        for (let k = 0; k < epochLength; k++) channelSum[k] += event.channels[channel][k];
        return Array.from(channelSum, (value) => value / entry.count);
      });
      averages = {
        ...averages,
        [event.item]: { count: entry.count, wave: Array.from(sum, (v) => v / entry.count), channels },
      };
      event = null;
      nextOnset += samplingRate;
      if (orderIndex === order.length) {
        running = false;
        complete = true;
        const ranked = items.map((item) => ({
          item, mean: scores[item].sum / scores[item].count, positive: scores[item].positive,
        })).sort((a, b) => b.mean - a.mean);
        decision = ranked[0].positive >= rounds && ranked[0].mean - ranked[1].mean > 1
          ? ranked[0].item : null;
      }
    }
    return {
      samples: frame,
      markers,
      endIndex: sampleIndex,
      highlighted,
      scored: Object.values(scores).reduce((sum, score) => sum + score.count, 0),
      total: order.length,
      evidence: Object.fromEntries(items.map((item) => [item, { ...scores[item] }])),
      averages,
      complete,
      decision,
    };
  }

  function start() {
    running = true;
    nextOnset = sampleIndex + Math.round(samplingRate * 0.2);
  }

  function stop() {
    running = false;
    event = null;
  }

  return { target, nextFrame, start, stop };
}