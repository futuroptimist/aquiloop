# SST + LED Phase 0 experiment

The [authoritative learning plan](../../../../docs/design/aquarium-auto-top-off.md#81-phase-0--sst-water-detection-hello-world)
now separates board/USB/serial, onboard RGB, protected SST bucket indication,
and external LED/resistor learning. Later steps add a parametric hang-on-back
mount, two sensors with adjustable spacing and a pretend-pump LED, supervised
calibrated pumping, then observability. Each step has its own BoM and pass gate.

**Status: existing sketch compile validation passed; electrical qualification
and all physical validation remain pending.** This PR changes documentation
only. The sketch drives GPIO5 external LED from GPIO4 digital input; it does
not implement onboard RGB, two sensors, pump control or fault diagnosis.

## Stop before connecting the SST input

The previous assembly recipe is withdrawn. Read and complete the
[electrical qualification gate](../../../../docs/design/aquarium-auto-top-off.md#electrical-qualification-gate---before-any-gpio-connection)
before any SST/interface connection to an ESP32 GPIO. Initial interface-node
measurements use an isolated MCU input and an appropriate representative load.
Verify exact board/module revision and manufacturer schematic before GPIO or
RGB instructions; N8R8 does not identify the board revision.

The proposed sensor rail is regulated **5 V**; the future pump rail is separate
**12 V**. Never connect raw sensor output to a GPIO, run this SST at 3.3 V, or
reuse the three-resistor divider at 12 V. Do not connect bench +5 V to the
ESP32 5 V pin while USB powers it. Keep all electronics dry, use a separate
freshwater cup/bucket, and isolate all power before rewiring. Only the optical
tip contacts water. No actuator or aquarium installation belongs in Phase 0.

## Smallest SST BoM still includes protection

- Reuse the verified ESP32-S3-DevKitC-1-N8R8, data USB cable and computer.
- One SEN-13835 / LLC200D3SH-LLPK1, regulated 5 V sensor supply,
  breadboard/leads, defined ground/reference and strain relief.
- **Mandatory per SST channel:** complete qualified voltage-interface and
  power-off-protection package, selection pending. The existing candidate has
  three 10 kohm, 1/4 W, +/-5% resistors (10 kohm upper; two series resistors
  forming 20 kohm lower/pull-down). They alone are **unqualified**. Retain them
  in the candidate BoM until a manufacturer-supported replacement is reviewed;
  added/replacement protection parts require explicit ratings and quantities.
- Meter and appropriate transient-measurement access are required; freshwater
  test vessel and lint-free cloth are reused.
- Only the optional external indicator adds one LED and **one separate
  330 ohm, 1/4 W, +/-5% current-limiting resistor**. Its omission does not remove
  any SST protection. An onboard-RGB-only SST test still needs the full package.

No new protection part or wiring recipe is selected here. Actual BoMs are in
this README and the design document; the design's future bom.csv is not present.

## Electrical learning checklist

1. Read the part-specific SST output limits and ESP32-S3 GPIO DC table linked
   in the authoritative gate, not a generic sensor or power-pin maximum.
2. Reproduce worst-case resistor and rail calculations. At exact 5.00/3.30 V,
   kmin = 19/29.5 and kmax = 21/30.5 give dry 2.57627-3.44262 V and wet at most
   0.34426 V under the stated output assumptions. HIGH minimum is 0.75 x VDD;
   upper input bound is VDD + 0.3 V. Dry-HIGH margin is only 0.10127 V.
   At 5 V +/-5% with exact 3.3 V, dry minimum can be 2.41525 V and maximum
   3.61475 V: both corners fail. A fixed 3.6 V check is not qualification.
3. Before GPIO connection, record actual rails, output/load limits, resistor
   tolerances, noise, overshoot and measurement uncertainty; establish and
   verify positive margins for the real installation envelope.
4. Independently qualify both power orders, loss of either rail and backfeed
   behavior using manufacturer evidence. A divider/pull-down and manual power
   order do not establish safe behavior when the MCU is off but sensor is on.
   Unknown injection or powered-off limits keep the input disconnected.
5. Only after the gate is reviewed and passed may a later physical experiment
   use the approved wiring and record wet/dry results. No such result exists yet.

## Existing external-LED sketch setup

These settings preserve the previously compiled configuration. Board-only
upload/serial checks may leave all external circuits disconnected; disregard
floating-input sensor text. The onboard RGB lesson needs a separate future
revision-specific example. Do not treat this sketch as the two-sensor lesson.
That future lesson uses the [two-SST pump permission contract](../../../../docs/design/aquarium-auto-top-off.md#two-sst-pump-permission-and-transition-contract)
and its acceptance tests: start only on debounced both-dry, stop at lower wet,
and stop/latch on either upper-wet pair. Its pretend-pump LED means command ON;
this existing sketch's LED means WET. Neither firmware nor physical results for
that lesson are supplied here.

### Arduino IDE 2.x setup and upload

1. Install Arduino IDE 2.x.
2. In **Preferences > Additional Boards Manager URLs**, add
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
3. In Boards Manager, install `esp32` by Espressif Systems and select version
   **3.3.8** for this reproducible environment.
4. Open `sst_led.ino`, then select **ESP32S3 Dev Module** and these Tools values:
   **Flash Size: 8 MB**, **Partition Scheme: 8M with spiffs**,
   **Flash Mode: QIO 80MHz**, **PSRAM: OPI PSRAM**, and
   **Upload Mode: UART0 / Hardware CDC**.
5. Select the serial port belonging to the ESP32 USB-to-UART connection and
   click Upload. If upload fails, confirm that the cable carries data, reselect
   the port, and use Espressif's BOOT/reset sequence: hold BOOT, press and
   release RESET, release BOOT, then retry upload.


## Conditional physical procedure and pending record

After the electrical gate passes, use the reviewed interface/wiring record,
with board GPIO assignments verified, to repeat the dry/wet/blotted-dry cycle
at least five times. Capture serial at 115200 baud, voltage envelope and LED
state. With the existing sketch, HIGH means DRY/LED off and LOW means WET/LED
on. Serial prints a banner, initial state, then transitions only; polling is
50 ms without debounce. No analog voltage validity is measured by this sketch.

A disconnected output with an intact lower pull-down reads WET. Sensor-power
loss is also expected LOW only if the unpowered sensor output permits the bias;
verify this separately. Neither state proves water presence. A broken ground
or lower divider leg is a different fault. Never short the SST output directly
to either rail to simulate a fault. Retained droplets can keep the tip wet;
gently blot it dry rather than changing firmware polarity.

| Test | Required evidence | Observed result | Pass/fail |
| --- | --- | --- | --- |
| Board/USB/serial | Actual revision, port, three successful reset/upload banners | Pending | Pending |
| Onboard RGB (future example) | Five red/green/blue/off cycles on verified revision | Pending | Pending |
| Electrical gate before GPIO | Reviewed limits, worst-case worksheet, measured envelope and power-off/backfeed evidence | Pending | Pending |
| Dry powered sensor | HIGH/DRY; qualified voltage margin; external LED off if fitted | Pending | Pending |
| Wet tip | LOW/WET; qualified voltage margin; external LED on if fitted | Pending | Pending |
| Five wet/dry/blotted cycles | Serial/indicator agreement and no unexplained transitions | Pending | Pending |
| Output disconnected, lower leg intact | LOW/WET ambiguity explicitly recorded | Pending | Pending |
| Approved power-loss/order tests | Both rail-loss cases safe electrically; interpretations recorded | Pending | Pending |

On noisy, implausible or out-of-envelope results, isolate power and return to
the electrical gate. Do not debug by swapping live wires or bypassing protection.
On upload/serial failure, check data cable, selected USB-to-UART port, core and
settings above; steady states intentionally do not repeat serial lines.

Exit requires the preserved compile evidence, reviewed electrical qualification,
and every applicable physical row recorded as passed. Future RGB/two-sensor
firmware requires its own validation; none is inferred from the existing build.
Phase 1 remains supervised and adds the separate first-pump gate. Independent
overflow, source-low, leak protection and containment must pass before any
unattended-use consideration.
