# SST + LED Phase 0 experiment

This is the practical entry point for the supervised **Phase 0 — SST
water-detection hello world**. The authoritative rationale and phase plan are in
the [auto-top-off design](../../../../docs/design/aquarium-auto-top-off.md#81-phase-0--sst-water-detection-hello-world).

The experiment reads a SparkFun SST sensor on GPIO4, lights an external LED on
GPIO5 when the tip is wet, and reports the initial state and later changes over
serial. It deliberately has no pump, relay, MOSFET, Wi-Fi, metrics, enclosure,
aquarium installation, or other sensor. It is not production control logic.

## Safety and scope

Phase 0 is a supervised, low-energy, dry-bench experiment. Use a separate clean
cup of fresh water, **not the aquarium**, and let only the SST optical prism tip
contact water. Keep the ESP32, breadboard, USB cable, bench supply, wire exit,
connector, and every exposed conductor dry. Wear eye protection if available.
Turn power off before rewiring.

The ESP32 GPIO absolute maximum is 3.6 V. Do not power the SST from 3.3 V; that
is below its documented 4.5–15.4 V operating range. Its 5 V-class push-pull
output must pass through the documented divider and must never connect directly
to a GPIO. Do not connect bench +5 V to the ESP32 5 V pin while USB powers the
board. No pump or other actuator may be connected.

Passing this experiment does not authorize unattended operation or aquarium
installation. There is no independent high-water cutoff, and Phase 0 cannot
distinguish water from a disconnected or unpowered sensor. No enclosure or
structural component is needed, so Phase 0 creates no OpenSCAD or STL files;
PLA/OpenSCAD requirements begin when later phases add structural components.

## Bill of materials

### Required

- 1 × Espressif ESP32-S3-DevKitC-1-N8R8.
- 1 × SparkFun SST Liquid Level Sensor, `SEN-13835` /
  `LLC200D3SH-LLPK1`.
- 1 × solderless breadboard.
- Suitable jumper wires or test leads.
- 1 × data-capable Micro-USB/Micro-B cable for the board's USB-to-UART port.
- 1 × regulated bench power supply.
- 3 × 10 kΩ, ¼ W, 5% resistors: one upper divider resistor and two in
  series for the 20 kΩ lower resistance.
- 1 × 330 Ω, ¼ W, 5% resistor.
- 1 × ordinary external LED.
- 1 × clean cup containing fresh water.

A 10 kΩ four-band resistor is brown-black-orange, typically with a gold
tolerance band. A 330 Ω four-band resistor is orange-orange-brown, typically
with a gold tolerance band. Resistor orientation does not matter. The LED anode
is normally the longer lead; its cathode is normally the shorter lead and
corresponds to the package's flat side. Confirm uncertain parts with a meter or
data sheet rather than relying only on appearance. No capacitor is required.

### Recommended, not required

- Digital multimeter.
- Eye protection.
- Lint-free cloth for drying the optical tip.

## Exact wiring

Make these connections with USB disconnected and the bench output OFF:

1. Plan to power the ESP32-S3 through its USB-to-UART Micro-B connector with the
   data-capable cable.
2. Configure the SST bench supply for exactly 5.00 V.
3. Set a modest current limit of approximately 50 mA.
4. Connect SST red to bench +5.00 V.
5. Connect SST blue to bench ground.
6. Connect bench ground to an ESP32 pin labeled GND to establish a common
   reference.
7. Connect SST green to one end of a 10 kΩ resistor.
8. Connect the other end of that resistor to a junction node.
9. Connect the junction to the ESP32 header pin labeled GPIO4.
10. From the junction, connect two 10 kΩ resistors in series to ground; together
    they are the 20 kΩ lower divider resistance.
11. Connect GPIO5 through the 330 Ω resistor to the LED anode.
12. Connect the LED cathode to ground.
13. Do not connect bench +5 V to the ESP32 5 V pin while USB powers the board.
14. Never connect the raw SST green output directly to an ESP32 GPIO.

```text
Bench +5.00 V ---------------- SST red

Bench GND -------------------- SST blue
    |
    +------------------------- ESP32 GND
    |
    +------------------------- LED cathode

SST green ---- 10 kΩ ----+---- GPIO4
                         |
                       10 kΩ
                         |
                       10 kΩ
                         |
                        GND

GPIO5 ---- 330 Ω ---- LED anode
```

GPIO5 sources current through the 330 Ω resistor and LED to common ground.
GPIO4 is only the divider junction; use the header labels and do not infer GPIOs
by counting physical pin positions.

## Why the divider is required

The upper resistance is 10 kΩ and the lower resistance is 20 kΩ:

```text
Vgpio = Vsensor_out × 20 kΩ / (10 kΩ + 20 kΩ)
```

A nominal 5.00 V sensor HIGH becomes approximately 3.33 V. Allowing for the
sensor output range, approximately 2.67–3.33 V is expected at GPIO4 when dry.
A sensor LOW of at most approximately 0.5 V becomes at most approximately
0.33 V. This protects the 3.3 V ESP32 input from the sensor's 5 V-class
push-pull output.

The 20 kΩ lower resistance also pulls GPIO4 LOW if the SST is disconnected or
unpowered. Thus sensor-off appears as WET and turns the LED on. This is
conservative for future pump safety, but in Phase 0 it is only a
fault-conservative electrical state, not proof that water is present.

## Arduino IDE 2.x setup and upload

1. Install Arduino IDE 2.x.
2. In **Preferences > Additional Boards Manager URLs**, add
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
3. Open Boards Manager, find `esp32` by Espressif Systems, and install version
   **3.3.8**. Pinning the core makes this procedure reproducible.
4. Open `sst_led.ino` from this directory.
5. Select board **ESP32S3 Dev Module** and set:
   - Flash Size: **8 MB**
   - Partition Scheme: **8M with spiffs**
   - Flash Mode: **QIO 80MHz**
   - PSRAM: **OPI PSRAM**
   - Upload Mode: **UART0 / Hardware CDC**
6. Connect the board's USB-to-UART Micro-B port with the data-capable cable.
7. Select the serial port belonging to that USB-to-UART connection.
8. Leave sensor power OFF, click **Upload**, and wait for completion.
9. If upload fails, verify the data cable and port, then use Espressif's
   BOOT/reset sequence: hold BOOT, press and release RESET, release BOOT, and
   retry the upload; press RESET afterward to run.
10. Open Serial Monitor at **115200 baud** and press RESET so both the banner and
    initial state are visible.

The sketch uses only the official Arduino-ESP32 core; no third-party library is
needed.

## Bring-up and test procedure

1. Place the breadboard, ESP32, supply, and exposed wiring on a dry surface away
   from the aquarium.
2. Leave USB disconnected and the bench-supply output OFF while wiring.
3. Set the supply to 5.00 V and approximately a 50 mA current limit, keeping its
   output OFF.
4. Identify header labels GPIO4, GPIO5, and GND; do not count physical header
   positions.
5. Build and inspect the 10 kΩ/20 kΩ divider exactly as shown.
6. Build and inspect the GPIO5, 330 Ω, LED, and ground circuit.
7. Connect bench ground to ESP32 GND and the LED cathode ground.
8. Connect SST red, blue, and green last.
9. If a multimeter is available, verify resistor values and check for an
   accidental +5 V-to-ground short before power is applied.
10. Connect ESP32 USB while leaving the sensor supply OFF.
11. Install Arduino-ESP32 3.3.8 and upload with the settings above.
12. Open Serial Monitor at 115200 baud.
13. Press RESET so the startup banner and initial reading appear.
14. With sensor power OFF, verify GPIO4 LOW/WET and LED ON. This is the
    fault-conservative pull-down state, not evidence of water.
15. Turn on the 5.00 V sensor supply with the optical tip dry.
16. Verify GPIO4 HIGH/DRY, LED OFF, and the matching serial transition.
17. If a meter is available, measure GPIO4 relative to common ground. Expect
    approximately 2.67–3.33 V dry; stop immediately if it exceeds 3.6 V.
18. Touch or dip only the optical prism tip into the fresh-water cup. Do not
    immerse the wire exit, connector, breadboard, or electronics.
19. Verify GPIO4 LOW/WET, LED ON, and the matching serial transition.
20. If a meter is available, verify approximately 0–0.33 V at GPIO4 while wet.
21. Remove the sensor and gently blot the optical tip dry with a lint-free cloth.
22. Verify return to GPIO4 HIGH/DRY and LED OFF.
23. Repeat at least five wet/dry cycles and record every result below.
24. Turn the bench output OFF before changing or disconnecting wiring.
25. Disconnect USB, dry the sensor, empty the cup, and store electronics dry.

## Expected behavior

The sensor polarity is inverted relative to the word "wet": HIGH means DRY and
LOW means WET. The LED output is HIGH/ON for wet and LOW/OFF for dry. The sketch
polls about every 50 ms and prints only the banner, initial state, and changes:

```text
Aquiloop SST + LED Phase 0
GPIO4: LOW -> WET; GPIO5 LED: ON
GPIO4: HIGH -> DRY; GPIO5 LED: OFF
```

It may print the HIGH line first if the powered sensor is already dry. Repeated
unchanged samples produce no messages.

## Troubleshooting

- **No serial port appears:** use the USB-to-UART Micro-B connector, confirm the
  cable carries data, try another USB port/cable, and check host drivers/device
  enumeration.
- **Upload fails:** select `ESP32S3 Dev Module` and the correct port, recheck all
  listed flash/PSRAM/upload settings, close other serial programs, and use the
  BOOT/reset sequence above.
- **No serial text appears:** select 115200 baud, press RESET after opening
  Serial Monitor, and confirm the monitor uses the same USB-to-UART port.
- **LED never turns on:** sensor-off should produce LOW/WET. Check GPIO5, the
  330 Ω value (orange-orange-brown), common ground, breadboard continuity, and
  reversed LED polarity.
- **LED is always on:** GPIO4 is LOW. Check that sensor power is on, red is at
  +5.00 V, blue is ground, green reaches the upper 10 kΩ, and common ground is
  present. A lost/disconnected sensor intentionally appears wet.
- **LED behavior is inverted:** verify LED cathode goes to ground and firmware
  is unchanged; SST HIGH means dry/LED OFF, while LOW means wet/LED ON.
- **GPIO4 is above 3.6 V:** turn the bench output OFF immediately. Do not
  continue until the raw green wire is isolated from GPIO4 and the 10 kΩ upper
  plus two-series-10 kΩ lower divider is corrected and verified.
- **Sensor changes state when powered but not when dipped:** dip only the prism
  sufficiently to contact fresh water; inspect for dirt/scratches and confirm
  SST red/blue/green were not interchanged. Do not immerse the wire exit.
- **Sensor remains wet after removal:** a droplet can remain on the optical tip;
  gently blot it with a lint-free cloth and retest.
- **State is noisy or changes rapidly:** keep leads short and secure, verify the
  50 mA-limited 5.00 V supply and common ground, inspect loose breadboard
  contacts, and clean/dry the tip. Phase 0 intentionally adds no capacitor or
  software debounce; stop if transitions remain unexplained.
- **Missing common ground:** the reading may float or be wrong even though both
  supplies work. Connect bench ground to an ESP32 GND pin.
- **Incorrect resistor values:** power off and measure them; 10 kΩ is
  brown-black-orange and 330 Ω is orange-orange-brown, normally with gold
  tolerance bands. Ensure the lower leg is two 10 kΩ resistors in series, not
  parallel.
- **Sensor wire error:** power off, then restore red to +5.00 V, blue to bench
  ground, and green only to the divider's upper 10 kΩ. Never guess or hot-swap.

## Shutdown

Turn the bench-supply output OFF before touching wiring. Disconnect USB, blot
the optical tip dry, empty the separate test cup, inspect for droplets, and
store the sensor and electronics dry.

## Validation record

**Physical validation: PENDING.** A person must complete this table; no physical
result is claimed by the repository.

| Test | Expected GPIO4 | Expected interpretation | Expected LED | Observed result | Pass/fail | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Sensor supply OFF | LOW | WET (fault-conservative, not proof of water) | ON |  |  |  |
| Sensor powered and dry | HIGH, about 2.67–3.33 V | DRY | OFF |  |  |  |
| Sensor tip wet | LOW, about 0–0.33 V | WET | ON |  |  |  |
| Sensor removed and blotted dry | HIGH | DRY | OFF |  |  |  |
| Five repeated wet/dry cycles | Alternating HIGH/LOW without unexpected transitions | Alternating DRY/WET | Alternating OFF/ON |  |  |  |
