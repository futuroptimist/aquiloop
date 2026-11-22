# SST + LED Phase 0 experiment

**Start with USB only. Do not connect the SST level signal, a sensor-supply
monitor, or any SST circuit to an ESP32 pin. Do not connect a pump.** The
earlier divider recipes are not approved wiring, even if a meter shows less
than 3.2 V. The existing sketch compiled, but this repository does not yet
record physical qualification for the SST interface.

## Beginner quick start: no external wiring

**You need:** An ESP32-S3-DevKitC-1-N8R8, a USB data cable, a computer, and a
dry, nonconductive work surface. Keep the session away from the aquarium and
do not open or modify any power supply. No breadboard, external LED, water,
sensor power supply, or pump is needed for this session.

1. Leave the ESP32 USB unplugged and the sensor supply off and unplugged. If
   connected from an earlier experiment, remove external wires only after both
   supplies are disconnected. Keep the header pins empty for this session.
2. Photograph the markings on the board and module. Record the board revision,
   module name and memory marking. **N8R8 identifies memory, not the board
   revision.** Match the board to the Espressif guide and schematic linked in
   the [design's board notes](../../../../docs/design/aquarium-auto-top-off.md#firmware-and-physical-evidence).
   Confirm the N8R8 variant (8 MB flash and 8 MB octal PSRAM) separately from
   the board revision. If the variant, revision, or USB-to-UART connector is
   different or uncertain, stop at the inventory. Do not guess a pin, port,
   or upload setting.
3. If you have the SST, record its exact part number and the supply label in
   your notes. Keep both unpowered. This is an inventory, not a shopping list
   or a wiring check.
4. If the board and USB-to-UART port match the guide, follow the
   [board-only upload steps below](#arduino-ide-2x-setup-and-upload).
   Use only USB power. No sensor, jumper, LED or common-ground wire should be
   attached. If you already completed this lesson on the same documented
   board and setup, keep that result instead of repeating it.
5. Open Serial Monitor at **115200 baud**, reset the bare board, and look for
   `Aquiloop SST + LED Phase 0`. Repeat for three successful upload/reset
   cycles if recording the 0a gate. The pin has no signal attached: ignore any
   WET/DRY text. It cannot tell you anything about water or a sensor.

**Finish:** Keep the revision, USB port, sketch revision, and banner results.
Mark the board-only check passed only if the expected banner appeared each
time; otherwise record the step as pending. Unplug USB when done. Both
supplies, all sensor wires and the pump remain disconnected. Board-only RGB
success is a separate result, not permission to wire a sensor.

## Stop before connecting either SST input

The [electrical qualification gate](../../../../docs/design/aquarium-auto-top-off.md#electrical-qualification-gate---before-any-gpio-connection)
applies to **every** SST-related junction, including a divider intended to
monitor the sensor's 5 V supply. It applies to GPIO3, GPIO4 and any other pin,
whether read digitally or as an analog input. GPIO3 is sampled at reset for
a chip setting; don't use it as a default spare analog pin.

A meter shows a steady voltage; it may miss brief spikes. Backfeed means
the sensor circuit can send current into an ESP32 that is supposed to be off.
A preferred plug-in order does not prevent an accidental unplug or power
loss. The next step is a reviewed interface and disconnected test plan, not
a live hookup. If you cannot confirm the limits or do not have the instruments
or help to check them, **stop here**. Do not try it on the ESP32 to find out.

The proposed sensor rail is regulated **5 V**; the future pump rail is separate
**12 V**. Never connect raw sensor output to a GPIO, run this SST at 3.3 V, or
reuse the three-resistor divider at 12 V. Do not tie bench +5 V to the board's
5 V pin while USB powers it. Keep electronics dry. Any later approved wet
test uses a separate freshwater vessel and wets only the optical tip; it
does not take place in the aquarium. No actuator belongs in Phase 0.

## Future SST parts: planning only

- Reuse the verified ESP32-S3-DevKitC-1-N8R8, data USB cable and computer.
- One SEN-13835 / LLC200D3SH-LLPK1, regulated 5 V sensor supply,
  breadboard/leads, defined ground/reference and strain relief.
- This is not a purchase or assembly list. Numeric resistor values below
  describe an unqualified analysis candidate only.
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

## Electrical learning checklist (review only)

This is background for a qualified review, not an assembly procedure.

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

## Existing sketch: USB-only upload setup

These settings preserve the previously compiled configuration. Board-only
upload/serial checks must keep all external circuits disconnected; disregard
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
   **Flash Mode: QIO 80MHz**, **PSRAM: OPI PSRAM**,
   **Upload Mode: UART0 / Hardware CDC**, and **USB CDC On Boot: Disabled**.
   These values are for the N8R8 board using its USB-to-UART connector.
   Disabling CDC on boot sends the sketch's serial output to that connector.
5. Select the serial port belonging to the ESP32 USB-to-UART connection and
   click Upload. If upload fails, confirm that the cable carries data, reselect
   the port, and use Espressif's BOOT/reset sequence: hold BOOT, press and
   release RESET, release BOOT, then retry upload.
6. If upload succeeds but the monitor is blank, confirm the same USB-to-UART
   port is selected and the monitor is set to **115200 baud**. If **USB CDC On
   Boot** was enabled, disable it and upload again before reopening the monitor.
   Press RESET without holding BOOT to see the banner. If it still does not
   appear, record the check as pending. Keep all external wiring disconnected.

## Conditional physical procedure and pending record

**Not ready to run.** After the electrical gate passes, use the reviewed interface/wiring record,
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
