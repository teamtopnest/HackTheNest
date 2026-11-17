# NeuronVision

NeuronVision is TopNest Group’s assistive brain-computer interface for [HackTheNest 2026](https://github.com/teamtopnest/HackTheNest). It helps a person who cannot rely on speech ask for what they need. A g.tec EEG headset watches for the P300 response to a flashing choice, and the interface turns that choice into a request: help, pain, movement, a drink, or a call to someone nearby.

The public site is [neuronvision.us](https://neuronvision.us) or  [neuronvision.web.app](https://neuronvision.web.app/)

This is an assistive research prototype, not a medical device.

## What we do

A person attends to one item on a phrase board. The attended flash produces a detectable scalp signal. NeuronVision records that signal on the computer beside the headset, shows the traces, and scores attended flashes with a shrunk linear discriminant model trained on real Unicorn recordings.

The phrase board is organized around care: food, drink, movement, pain, help, family, and friends. The website explains the system and gives partners a way to request a pilot.

## What works

- The public site is hosted at [neuronvision.us](https://neuronvision.us), with the same build on the Firebase addresses.
- The acquisition page can select a Unicorn Hybrid Black, BCI Core-4, BCI Core-8, or g.Nautilus, scan for a paired headset, check the connection, and collect filtered EEG on the local computer.
- Live traces stream over a WebSocket after a causal 0.5–30 Hz bandpass. MongoDB storage is optional.
- The care menu covers food, drink, movement, pain, help, family, and friends, and each category opens into smaller requests.
- A demo mode runs without a headset. It flashes the menu, labels the attended choice, and draws the average P300 waveform from a synthetic signal.
- The setup flow includes an electrode-alignment guide, a contact check illustration, and a stimulus-timing diagram.
- The offline decoder scores the five bundled Unicorn recordings with shrunk LDA and reports how well an attended flash separates from an ignored one.
- Tests for the headset API, the filter, storage, and the decoder run without Bluetooth hardware.

## Where we can optimize

- Save each flashed phrase with its EEG sample index, then train the existing decoder on that session so a selected request is measured rather than simulated.
- Stop a selection early when one choice is already far ahead, instead of flashing a fixed number of rounds.
- Order the next board from the last request, so pain leads to a body location and help leads to a person to call.
- Keep the first screen short: yes, no, help, stop, and pain. Leave spelling for names the menu does not contain.
- Score raw headset samples with the decoder’s own filter. The live stream is already filtered, and running both filters would change the signal the model was trained on.
- Let a caregiver edit the menu for one person, including family names and daily routines.
- Give the headset stream and the recording API separate ports, and require authentication before a browser can open the stream.
- Map channel numbers to the 10–20 montage only after the headset manual confirms that mapping.

## What we want to achieve

A person should be able to make an urgent request in one selection, without spelling it letter by letter and without an implant. The work list above is how that request becomes a measured result and how the board stays short enough to use at the bedside.

## Repository

The React site lives in `app/`. The Python acquisition service and the P300 decoder live in `backend/`. The headset service stays on the paired computer. Firebase hosts the website only.

Setup and commands are in [backend/README.md](backend/README.md) and [app/Frontend.md](app/Frontend.md).

## License

TopNest’s source code is released under the [MIT License](LICENSE).

That license does not cover g.tec software, device drivers, g.Pype, or the supplied EEG recordings. Those remain under their own terms.
