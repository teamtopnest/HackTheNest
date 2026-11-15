import numpy as np
import gpype as gp


def _filter_node():
    node = gp.Bandpass(f_lo=0.5, f_hi=30.0, order=2, phase="causal")
    port_in = gp.Constants.Defaults.PORT_IN
    node.setup(
        {port_in: np.zeros((1, 8))},
        {
            port_in: {
                gp.Constants.Keys.SAMPLING_RATE: 250,
                gp.Constants.Keys.CHANNEL_COUNT: 8,
                gp.Constants.Keys.FRAME_SIZE: 25,
                gp.IPort.Configuration.Keys.TIMING: gp.Constants.Timing.SYNC,
            }
        },
    )
    return node


def _amplitude(signal, frequency_hz, sample_rate_hz):
    time = np.arange(signal.size) / sample_rate_hz
    sine = np.sin(2 * np.pi * frequency_hz * time)
    cosine = np.cos(2 * np.pi * frequency_hz * time)
    return 2 * np.hypot(np.dot(signal, sine), np.dot(signal, cosine)) / signal.size


def test_bandpass_retains_10hz_and_attenuates_60hz_with_state_across_blocks():
    sample_rate_hz = 250
    time = np.arange(sample_rate_hz * 8) / sample_rate_hz
    signal = np.sin(2 * np.pi * 10 * time) + np.sin(2 * np.pi * 60 * time)
    samples = np.repeat(signal[:, None], 8, axis=1)
    port_in = gp.Constants.Defaults.PORT_IN
    port_out = gp.Constants.Defaults.PORT_OUT

    continuous = _filter_node().step({port_in: samples})[port_out]
    block_filter = _filter_node()
    block_outputs = [
        block_filter.step({port_in: samples[start : start + 25]})[port_out]
        for start in range(0, samples.shape[0], 25)
    ]
    chunked = np.vstack(block_outputs)

    assert np.allclose(continuous, chunked, atol=1e-12)
    settled = continuous[sample_rate_hz * 4 :, 0]
    assert _amplitude(settled, 10, sample_rate_hz) > 0.9
    assert _amplitude(settled, 60, sample_rate_hz) < 0.4


def test_bandpass_drift_rejection_and_half_power_cutoffs():
    sample_rate_hz = 250
    time = np.arange(sample_rate_hz * 40) / sample_rate_hz
    frequencies = [0.1, 0.5, 10, 30, 50, 60]
    signal = sum(np.sin(2 * np.pi * frequency * time) for frequency in frequencies)
    samples = np.repeat(signal[:, None], 8, axis=1)
    output = _filter_node().step({gp.Constants.Defaults.PORT_IN: samples})[
        gp.Constants.Defaults.PORT_OUT
    ]
    settled = output[sample_rate_hz * 20 :, 0]
    assert _amplitude(settled, 0.1, sample_rate_hz) < 0.06
    assert 0.65 < _amplitude(settled, 0.5, sample_rate_hz) < 0.8
    assert _amplitude(settled, 10, sample_rate_hz) > 0.95
    assert 0.65 < _amplitude(settled, 30, sample_rate_hz) < 0.8
    assert _amplitude(settled, 50, sample_rate_hz) < 0.3
    assert _amplitude(settled, 60, sample_rate_hz) < 0.2
