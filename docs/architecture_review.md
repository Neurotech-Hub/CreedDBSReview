The strongest conclusion from the literature is that your current Creed device is not fundamentally battery-limited by the stimulation itself; it is architecture-limited by everything required to *support* flexible stimulation. The chronic mouse-scale systems that run for weeks to months generally get there by giving up continuous wireless control, high compliance rails, continuously active analog circuitry, or some combination of those.

Also, one important correction: the Paulat device **does support biphasic stimulation**. It uses a deliberately asymmetric, slightly charge-imbalanced biphasic waveform: approximately 96–100 µA cathodic for 60 µs followed by ~8 µA anodic for ~670 µs. It is not a conventional symmetric biphasic driver, but it is substantially closer to clinical IPG-style active recharge than a monophasic system. 

## 1. The relevant competitive landscape

The most useful comparison set is not “all rodent stimulators,” but specifically devices small enough for mice or at least demonstrating the architectural extremes you could adopt.

| Device                | Mouse compatible?                        | Power / runtime                                           | Stim architecture                                             |                  Channels | Remote configurability                             | Key lesson                                                                                                    |
| --------------------- | ---------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------- | ------------------------: | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Creed v8.1**        | Yes                                      | **3.15–3.42 mA stim**, ~2.5–3 d on 2× size-13 zinc-air (~280 mAh) | Constant-current Howland, ±5 V, DAC, analog switching; asymmetric 1:5 biphasic | 2, shared amplitude and timing | **BLE real-time**                                  | Extremely flexible, but pays mA-scale infrastructure overhead                                                 |
| **Paulat 2026 t-IPG** | **Yes**                                  | **21.3 µA @130 Hz**, ≥49 d voltage-compliant; 0.9 g       | Constant-current asymmetric biphasic; direct 3 V              |                 2 delayed | Near-field programmer / predefined paradigms       | Demonstrates that chronic mouse DBS can live in the tens-of-µA regime                                         |
| **Grotemeyer 2024**   | **Yes**                                  | ~20 µA, **52 d**                                          | Constant-current monophasic + passive discharge               |                         1 | Magnetic on/off; preprogrammed                     | ~20 µA is repeatable with simple circuitry                                                                    |
| **Fleischer 2020**    | **Yes**                                  | ~20 µA, **30 d**                                          | Constant-current monophasic; charge dissipates between pulses |                         1 | Preprogrammed; reed switch                         | Similar result using two V364 cells and no active radio                                                       |
| **de Haas 2012**      | **Yes**                                  | ≥15 d standby + 10 h active criterion                     | Biphasic, two electrode channels                              |                         2 | IR/status + programmed fixture                     | True bilateral mouse DBS was possible long before BLE, but with constrained configurability                   |
| **Alpaugh 2019**      | **Yes**                                  | ≥30 d, batteries externally accessible; 4.7 g             | Balanced positive/negative stimulation                        |                         1 | Parameters reprogrammable, but not radio-real-time | Long runtime is compatible with balanced stimulation if configuration is infrequent                           |
| **STELLA 2021**       | Rat-demonstrated; size relevant to mouse | **7.6 µA @3.1 V**, ≥12 wk tested, 126 d calculated CR1216 | Constant-current, passive charge balancing                    |                         2 | External control/monitoring; not BLE streaming     | Best architectural benchmark for ultra-low-power configurable DBS                                             |
| **Kouzani 2013**      | Described as murine; 3.27 g headmount    | ~870 µA measured, ~10–12 d                                | Constant-current, passive charge balancing                    |                         1 | Preprogrammed                                      | Even an ATtiny-era design beat Creed by ~4× simply by eliminating high-power infrastructure                   |
| **Pinnell 2018**      | Rat, but useful acute benchmark          | ~30 h continuous                                          | **2-ch charge-balanced biphasic**, 12 V compliance            |                         2 | Preprogrammed + magnet                             | High compliance + rich pulse flexibility is expensive even without BLE                                        |
| **Burton 2021**       | Rodents; rat demonstrated                | Battery-free; **9.35 mW** average during stimulation      | Biphasic constant-voltage                                     |                         — | **Real-time wireless control**                     | If the arena can provide RF power, battery life ceases to matter—but you constrain the behavioral environment |
| **Shen 2026**         | Rat, too large for mouse                 | 400 mAh Li-ion, ≥300 h                                    | Biphasic voltage output                                       |                         — | **BLE real-time**                                  | BLE flexibility is practical when you tolerate a 7.5 g battery—not a mouse-scale solution                     |

The critical architecture benchmarks for Creed are therefore **Paulat, STELLA, Grotemeyer/Fleischer**, and secondarily **Pinnell**. Paulat and STELLA show what happens when runtime is the primary objective; Pinnell shows what happens when waveform flexibility and high compliance are prioritized.

## 2. Why Creed is ~100× higher power than Paulat/STELLA

Your measured data are unusually informative:

* “Sleep”: **1.47 mA**
* BLE advertising: **1.62 mA**
* BLE connected: **1.89 mA**
* 60 µA stimulation: **3.15 mA**
* 400 µA stimulation: **3.42 mA**

So increasing programmed stimulus amplitude by **340 µA only increases battery current by 270 µA**. The remaining ~3 mA is platform overhead. 

That is the main design insight.

Your architecture requires:

**battery → 5 V boost → 3.3 V LDO → MCU/BLE**, while simultaneously generating **−5 V**, operating a dual LT6020, DAC/reference, Howland network, and analog switches. 

A reasonable decomposition from the present design is:

| Creed subsystem                                  |                                             Approx. battery cost |
| ------------------------------------------------ | ---------------------------------------------------------------: |
| MCU running rather than genuinely sleeping       |                                                      ~0.7–1.9 mA |
| BLE connected overhead                           |                                                      ~0.3–0.5 mA |
| LT6020 on ±5 V                                   |                                                      ~0.7–0.8 mA |
| MAX1853 negative rail                            |                                                      ~0.3–0.6 mA |
| AD5683 DAC (external-reference part, never powered down) |                                                     ~0.2–0.35 mA |
| Reference / misc. analog                         |                                                     ~0.05–0.1 mA |
| Howland static currents                          |                                 unknown; potentially substantial |
| Actual additional stimulation current, 60→400 µA |                                             **0.27 mA measured** |

These estimates were already consistent with your observed ~3.4 mA total. One correction from the firmware: the LT6020 line is an upper bound. v8.1 asserts the amplifier's shutdown pin between pulses; the on-window is ~150 µs settle plus the stimulating phase plus a 5× recharge phase, so the duty is ~10% at 90 µs and ~50% at 600 µs, and the averaged cost is closer to 0.1–0.4 mA. The difference falls on the awake MCU and the Howland network, which makes the rail-current measurements in §7 more important, not less. 

Paulat takes essentially the opposite design philosophy: direct ~3 V battery operation, a low-power microcontroller, no permanently active radio, no continuously running ±5 V precision analog system, and a specialized current-source/H-bridge designed specifically around one class of DBS waveform. Their ~21 µA current is therefore quite believable. 

STELLA is even more instructive: it runs the MCU mostly in a low-power mode using a **32.768 kHz clock/timer to generate stimulation**, awakening the processor only when required. At 100 µA, 130 Hz, 60 µs, it reports **7.6 µA at 3.1 V**. It also keeps compliance low—roughly **2.2–2.8 V**—because their measured electrode loads typically did not require more.

That is probably the biggest conceptual difference from Creed: **STELLA designs the electrical architecture around the load actually encountered; Creed designs it around a highly flexible ±5 V laboratory-quality source.**

---

# 3. Feature-cost matrix for Creed v9

I would use this as the basis of the architecture discussion.

| Feature / decision                     | Scientific value                                  |                                           Power cost | Size / complexity                      | Recommendation                   |
| -------------------------------------- | ------------------------------------------------- | ---------------------------------------------------: | -------------------------------------- | -------------------------------- |
| **Constant-current stimulation**       | High; reproducibility despite impedance variation |                                             Moderate | Moderate                               | **Core**                         |
| **True biphasic capability**           | High; safety + protocol flexibility               | Small if switch-based; large if dual precision rails | Moderate                               | **Core**                         |
| **Perfect symmetric biphasic**         | Useful but rarely essential                       |                                             Moderate | Moderate                               | Optional                         |
| **Asymmetric active recharge**         | Clinically relevant, efficient                    |                                                  Low | Moderate                               | **Strong candidate**             |
| **Passive recharge / electrode short** | Very low power                                    |                                             Very low | Low                                    | Consider as chronic mode         |
| **±5 V continuous rails**              | Very broad compliance                             |                                        **Very high** | High                                   | **Avoid unless necessary**       |
| **~3–4 V compliance**                  | Likely sufficient for many mouse DBS loads        |                                                  Low | Low                                    | **Default target**               |
| **Dynamic compliance boost**           | Handles unusual high-Z electrodes                 |                          Low average if normally off | Moderate                               | **Very attractive**              |
| **BLE continuously connected**         | Excellent experiment control                      |                                   **Hundreds µA–mA** | Moderate                               | Acute mode only                  |
| **BLE only when configuring**          | Same parameter flexibility before runs            |                           Tens of µA average or less | Moderate                               | **Core**                         |
| **Magnet wake / on-off**               | Simple, deterministic                             |                                                  ~µA | Very low                               | **Core**                         |
| **NFC configuration**                  | No radio standby, batteryless config possible     |                                           ~0 standby | Moderate                               | Strong candidate                 |
| **Real-time parameter update**         | Important for event-triggered experiments         |                                     Potentially high | Moderate                               | Optional architecture tier       |
| **Configure-and-run mode**             | Excellent chronic paradigm support                |                                        Extremely low | Low                                    | **Core**                         |
| **1 stim channel**                     | Simplest experiments                              |                                               Lowest | Low                                    | Too restrictive                  |
| **2 independent channels**             | Bilateral DBS / dual target                       |                                             Moderate | Moderate                               | **Core**                         |
| **4+ channels**                        | Advanced steering/multisite                       |                                                 High | High                                   | Optional                         |
| **Time-multiplexed dual channel**      | Bilateral with shared source                      |                                                  Low | Moderate                               | **Strong candidate**             |
| **Continuous DAC operation**           | Arbitrary amplitude control                       |                                          ~100–500 µA | Moderate                               | Avoid if possible                |
| **DAC programmed once then shut down** | Retains flexibility                               |                            Near-zero between changes | Moderate                               | **Strong candidate**             |
| **Resistor-defined amplitudes**        | Ultra-low-power                                   |                                              Minimal | Low                                    | Too restrictive as sole solution |
| **Hardware timer stimulation**         | Deterministic + very low MCU duty cycle           |                                         Huge savings | Firmware complexity                    | **Mandatory**                    |
| **32 kHz pulse timing**                | µA-scale MCU operation                            |                                             Very low | Resolution limited                     | Chronic mode                     |
| **HF timer only during phases**        | Fine pulse resolution                             |                                          Low average | Moderate                               | **Ideal hybrid**                 |
| **Onboard LED heartbeat**              | Convenient                                        |       Potentially catastrophic relative to µA budget | Low                                    | **Remove**                       |
| LED only after magnet/query            | Useful diagnostics                                |                                   Negligible average | Low                                    | Good                             |
| **Battery voltage measurement**        | Valuable for longitudinal experiments             |                                  Tiny if duty cycled | Low                                    | **Core**                         |
| **Onboard logging**                    | Useful diagnostic/context                         |                                       Small–moderate | Moderate                               | Optional                         |
| **Neural recording**                   | Huge research value                               |                                            **Large** | Very high                              | Separate product tier            |
| **Closed-loop DBS**                    | Huge scientific value                             |                                            **Large** | Very high                              | Separate architecture            |
| **Wireless charging**                  | Unlimited reuse                                   |                          Moderate overhead/coil mass | High                                   | Optional                         |
| **Continuous inductive power**         | Essentially unlimited duration                    |                                 Zero battery concern | Arena infrastructure                   | Niche                            |
| **Primary lithium coin cell**          | Excellent energy density / shelf life             |                                                    — | Low                                    | **Chronic default**              |
| Zinc-air/hearing aid                   | Excellent nominal capacity/weight                 |                                                    — | Air access, drying, discharge behavior | Questionable for sealed implant  |
| Rechargeable Li-ion/LiPo               | Reusable, high discharge capability               |                                                    — | Weight + charger + safety              | Acute/high-feature               |
| Silver oxide                           | Stable voltage, small sizes                       |                                                    — | Lower Wh/g than lithium                | Reasonable                       |

## 4. The architectural fork I would make explicit

I don't think Creed should try to make **one architecture simultaneously maximize chronic runtime and real-time flexibility**.

I would instead make the firmware/hardware support two fundamentally different operating states.

### Chronic mode

Target: **<50 µA total**, preferably **10–30 µA**.

Parameters are programmed, BLE disconnects entirely, HF clocks stop, and pulse timing is generated from LF hardware peripherals. The stimulation driver only consumes meaningful power during a pulse.

This would put Creed in the same class as Paulat/Fleischer/Grotemeyer, without giving up Creed's programming flexibility before stimulation starts.

A 40 mAh battery at:

* 20 µA → ~83 days theoretical
* 40 µA → ~42 days
* 100 µA → ~17 days
* 3 mA → **13 hours**

That illustrates just how valuable each 100 µA becomes at this scale.

### Interactive/acute mode

Wake BLE and the richer analog system only when needed. A few mA is acceptable for experiments lasting hours or days.

This lets you preserve the thing Creed is genuinely better at: **experimenter control**.

---

# 5. Three plausible v9 architectures

### A. **Creed Chronic**

The direct competitor to Paulat/STELLA.

3 V primary lithium cell → MCU directly, no 5 V always-on supply. MCU runs LF timer continuously and wakes only for configuration/fault handling.

One low-power current source shared between two channels, H-bridge/polarity switch for biphasic delivery, perhaps 2.5–3.5 V compliance. Passive or low-amplitude active recharge.

Configuration by magnet + BLE session or NFC; no radio outside setup.

**Target: 10–30 µA average.**

This is the architecture I would build first.

### B. **Creed General Purpose**

Same low-power base, but add **switchable boost compliance**, perhaps 6–10 V.

The high voltage rail exists only during pulses or when electrode impedance requires it. Retain a DAC, but program-and-hold or power it down between parameter changes.

BLE can wake periodically or on magnet request.

**Target: ~30–150 µA chronic**, depending stimulation load.

This seems like the best long-term product architecture.

### C. **Creed Research / Acute**

Keep much of today's philosophy: high compliance, arbitrary biphasic waveforms, real-time BLE, possibly logging/recording.

Use LiPo or rechargeable lithium instead of optimizing for tiny primary batteries.

**Target runtime: hours–days, not weeks.**

Trying to force this architecture onto a hearing-aid battery is what creates the current mismatch.

---

# 6. The key question about waveform support

I would avoid framing the next design decision as “biphasic versus low power.”

That is not what the literature shows.

STELLA is charge balanced at **7.6 µA**.
Paulat produces an actively generated asymmetric biphasic waveform at **~21 µA**. 
Pinnell generates true two-channel symmetric biphasic pulses, but its high 12 V compliance and general-purpose architecture reduce runtime to ~30 hours.

The costly feature is therefore not biphasic stimulation by itself. It is:

**high compliance + continuously biased precision analog circuitry + arbitrary waveform flexibility + continuously awake MCU/radio.**

That distinction should drive the entire redesign.

---

## 7. Before designing v9, I would make six measurements on v8.1

Your existing notes already identify the right measurement points.  I would prioritize them in this order:

1. **3.3 V rail current** with BLE off and firmware forced into genuine EM2/EM3.
2. **+5 V rail current during stimulation**.
3. **MAX1853 input current** independently.
4. **LT6020 ±5 V supply current**.
5. **DAC and LT6656 reference current** (the AD5683 on the BOM is the external-reference variant; there is no internal reference to disable).
6. Total battery current versus **load impedance**, e.g. 1, 5, 10, 20, 30, 50 kΩ.

That last experiment is especially important. If typical in-vivo mouse electrodes never require more than ~2–3 V compliance—as STELLA found in its rodent preparations—then the strongest argument for the current ±5 V architecture largely disappears.

The architecture conversation I would have next is therefore not “how do we shave 20% off Creed?” It is **which capabilities justify moving us from a ~20 µA-class stimulator toward a ~3,000 µA-class stimulator?** Once each feature has that cost attached to it, I think the correct v9 architecture will become fairly obvious.
