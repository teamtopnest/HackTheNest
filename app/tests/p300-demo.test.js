import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createDemoExperiment } from '../src/lib/p300-demo.js';
import { COMMUNICATION_MENU, getFlashingRounds } from '../src/lib/communication-menu.js';

function seeded(seed) {
  return () => {
    seed = (1664525 * seed + 1013904223) >>> 0;
    return seed / 2 ** 32;
  };
}

test('demo produces varied channels without flashing before it is started', () => {
  const demo = createDemoExperiment(['Food', 'Drink'], 4, 250, seeded(1));
  const first = demo.nextFrame();
  assert.equal(first.samples.length, 25);
  assert.ok(first.samples.every((row) => row.length === 4));
  assert.notDeepEqual(first.samples.map((row) => row[0]), first.samples.map((row) => row[1]));
  for (let i = 0; i < 20; i++) assert.equal(demo.nextFrame().highlighted, null);
});

test('demo scores four balanced rounds from stimulus-linked synthetic samples', () => {
  const items = ['Food', 'Drink', 'Move', 'Pain', 'Help', 'Family', 'Friends', 'Other'];
  for (let seed = 1; seed <= 10; seed++) {
    const demo = createDemoExperiment(items, 8, 250, seeded(seed));
    demo.start();
    const flashes = new Set();
    let result;
    for (let i = 0; i < 400; i++) {
      result = demo.nextFrame();
      if (result.highlighted) flashes.add(result.highlighted);
      if (result.complete) break;
    }
    assert.equal(result.complete, true);
    assert.equal(result.scored, items.length * 4);
    assert.deepEqual([...flashes].sort(), [...items].sort());
    assert.ok(items.every((item) => result.evidence[item].count === 4));
    assert.equal(result.evidence[demo.target].positive, 4);
    assert.equal(result.decision, demo.target);
    assert.equal(demo.nextFrame().complete, false);
  }
});

test('averaged target epoch shows a clear P300 and every flash emits a marker', () => {
  const items = ['Food', 'Drink', 'Move', 'Pain', 'Help', 'Family', 'Friends', 'Other'];
  for (let seed = 1; seed <= 10; seed++) {
    const demo = createDemoExperiment(items, 8, 250, seeded(seed));
    demo.start();
    const markers = [];
    let result;
    for (let i = 0; i < 400 && !result?.complete; i++) {
      result = demo.nextFrame();
      markers.push(...result.markers);
    }
    assert.equal(markers.length, items.length * 4);
    assert.equal(markers.filter((m) => m.target).length, 4);
    assert.ok(markers.every((m) => m.target === (m.item === demo.target)));
    const peak = (wave) => Math.max(...wave.slice(Math.round(0.25 * 250), Math.round(0.5 * 250)));
    const targetPeak = peak(result.averages[demo.target].wave);
    const otherPeak = Math.max(...items.filter((i) => i !== demo.target).map((i) => peak(result.averages[i].wave)));
    assert.ok(result.averages[demo.target].count === 4);
    assert.ok(targetPeak > 8 && targetPeak > otherPeak * 2, `seed ${seed}: ${targetPeak} vs ${otherPeak}`);
    const targetChannels = result.averages[demo.target].channels;
    assert.equal(targetChannels.length, 8);
    for (const wave of targetChannels) {
      assert.equal(wave.length, 175);
      assert.ok(wave.every(Number.isFinite));
      assert.ok(peak(wave) > 10, `seed ${seed}: electrode peak ${peak(wave)}`);
    }
    assert.notDeepEqual(targetChannels[0], targetChannels[1]);
    for (let k = 0; k < result.averages[demo.target].wave.length; k++) {
      const channelMean = targetChannels.reduce((sum, wave) => sum + wave[k], 0) / 8;
      assert.ok(Math.abs(channelMean - result.averages[demo.target].wave[k]) < 1e-10);
    }
  }
});

test('stopping a demonstration prevents future flashes', () => {
  const demo = createDemoExperiment(['Food', 'Drink'], 4, 500, seeded(1));
  demo.start();
  for (let i = 0; i < 5; i++) demo.nextFrame();
  demo.stop();
  for (let i = 0; i < 20; i++) assert.equal(demo.nextFrame().highlighted, null);
});

test('every communication category has three levels and an Other option in each menu', () => {
  const menus = [COMMUNICATION_MENU];
  for (const category of COMMUNICATION_MENU.children.filter((item) => item.children)) {
    menus.push(category);
    for (const group of category.children.filter((item) => item.children)) {
      menus.push(group);
      assert.ok(group.children.length > 1);
      assert.ok(group.children.every((item) => !item.children));
      assert.equal(getFlashingRounds(group), 5);
    }
    assert.equal(getFlashingRounds(category), 4);
  }
  for (const menu of menus) {
    assert.ok(menu.children.some((item) => item.label === 'Other'));
    assert.equal(new Set(menu.children.map((item) => item.label)).size, menu.children.length);
    assert.ok(menu.children.length <= 8);
  }
  const move = COMMUNICATION_MENU.children.find((item) => item.label === 'Move');
  const outside = move.children.find((item) => item.label === 'Outside');
  assert.equal(outside.children.find((item) => item.label === 'Home').children, undefined);
});

test('final-level choices wait for five balanced rounds, not four', () => {
  const food = COMMUNICATION_MENU.children.find((item) => item.label === 'Food');
  const fastFood = food.children.find((item) => item.label === 'Fast food');
  const items = fastFood.children.map((item) => item.label);
  for (const [channels, rate] of [[4, 250], [8, 500]]) {
    const demo = createDemoExperiment(items, channels, rate, seeded(1), getFlashingRounds(fastFood));
    demo.start();
    let result;
    let checkedFourthRound = false;
    for (let i = 0; i < 300; i++) {
      result = demo.nextFrame();
      if (result.scored === items.length * 4) {
        assert.equal(result.complete, false);
        checkedFourthRound = true;
      }
      if (result.complete) break;
    }
    assert.ok(checkedFourthRound);
    assert.equal(result.complete, true);
    assert.equal(result.scored, items.length * 5);
    assert.ok(items.every((item) => result.evidence[item].count === 5));
    assert.equal(result.evidence[demo.target].positive, 5);
    assert.equal(result.decision, demo.target);
    assert.equal(result.averages[demo.target].channels.length, channels);
  }
});
