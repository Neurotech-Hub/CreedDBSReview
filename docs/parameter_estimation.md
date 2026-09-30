The whole firmware range is safe on this hardware, with two catches. Pulse widths below about 120 µs aren't actually produced, and the frequency you set is not the frequency you get, because the stimulation period is rounded down to a whole millisecond.

| Parameter | Suggested value | Range the hardware can deliver | Firmware limits today |
|---|---|---|---|
| Pulse width P | 120–150 µs | about 120–600 µs, in steps of about 30 µs | 90–600 µs |
| Frequency (continuous) | 125 Hz (exact) or 130 Hz (really about 143 Hz) | about 83–167 Hz, in only 7 distinct steps | 80–160 Hz |
| Burst period | 30 s (current default) | at least the burst duration; up to hours | 1 ms–1 h |
| Intra-burst frequency | same as continuous | same as continuous | 80–160 Hz |
| Burst duration | 10 s (current default, 33% duty cycle) | at least 2 intra-burst periods (about 15 ms or more) | 1 ms–120 s |

## Where these numbers come from

**Timer resolution.** All pulse timing uses the sleeptimer, which runs off the 32.768 kHz low-frequency oscillator. One tick is about 30.5 µs, so every width is rounded to that step.

**Pulse width floor.** The firmware subtracts a measured fixed overhead of 117 µs from P:

```514:517:app.c
	uint32_t nonzero_pulse_duration =
		(pulse_duration > STIM_OFFSET_US) ? (pulse_duration - STIM_OFFSET_US) : 0;
	uint32_t pulse_duration_ticks = getPulseDurationTicks(
		nonzero_pulse_duration);
```

Any P of 117 µs or less gets clamped to zero timer ticks, so the real pulse is roughly the overhead itself (about 117 µs). That makes the firmware minimum of 90 µs misleading. The common 60–90 µs mouse DBS pulse widths can't be produced with this timing approach.

**Pulse width ceiling.** Each pulse takes about 6·P plus 250 µs from start to finish:
- a 150 µs op-amp wake wait,
- a 30 µs switch settle,
- the DAC write over 1 MHz SPI,
- the stimulation phase P,
- a 5·P charge-balance phase (`CHARGE_BALANCE_RATIO 5`),
- a 30 µs settle before disconnecting.

At P = 600 µs that's about 3.85 ms, which fits inside the shortest period (6 ms). So 600 µs is safe at every allowed frequency, and roughly 900 µs would still fit at 167 Hz.

**Frequency quantization.** This one matters most:

```589:590:app.c
		sl_sleeptimer_start_periodic_timer(&timer_stimulation,
										   sl_sleeptimer_ms_to_tick(1000 / frequency),
```

`1000 / frequency` is integer division, so the period is always a whole number of milliseconds (rounded down). Across 80–160 Hz you only get 7 actual frequencies:

| Requested F | Period | Actual frequency |
|---|---|---|
| 80–83 | 12 ms | 83.3 Hz |
| 84–90 | 11 ms | 90.9 Hz |
| 91–100 | 10 ms | 100 Hz |
| 101–111 | 9 ms | 111.1 Hz |
| 112–125 | 8 ms | 125 Hz |
| 126–142 | 7 ms | 142.9 Hz |
| 143–160 | 6 ms | 166.7 Hz |

The standard 130 Hz DBS setting therefore runs at about 143 Hz. If you need an exact rate, use 100 or 125 Hz. Burst mode (the `IF` parameter) has the same behavior. The hardware itself could go much faster than 167 Hz, but the op-amp and switch waits (about 210 µs per pulse) run inside the timer interrupt, and the code comments say longer waits there already dropped BLE connections. I'd stay at or below about 200 Hz.

**Burst timing.**
- The periodic timer fires its first pulse one full intra-burst period after each burst starts, not at the start itself. The number of pulses per burst is roughly the burst duration divided by the intra-burst period, rounded down. A burst shorter than one period (about 7 ms at "130 Hz") delivers no pulses at all.
- When a burst ends, a pulse already in progress still finishes, including its charge balance. That can run up to about 3.9 ms past the nominal end.
- Burst duration is automatically capped at the burst period. Long periods are fine: an hour-long period is about 118 million ticks, well within the 32-bit timer.
- For power, burst mode is where you actually save battery. The analog stimulation chain costs about 1.3 mA of fixed overhead whenever it's active, while stimulation amplitude only adds about 0.27 mA (per `docs/mousestim_current_architecture.md`).

If you want the firmware to match what the hardware really does, the obvious changes are raising the minimum P to about 120 µs and computing the period in ticks instead of whole milliseconds. I'm in Ask mode, so I haven't changed anything; switch to Agent mode if you'd like me to make those edits.