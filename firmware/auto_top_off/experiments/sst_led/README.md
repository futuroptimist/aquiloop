# SST + LED Phase 0 experiment

This is the practical entry point for the experiment. The [Phase 0 section of the authoritative design](../../../../docs/design/aquarium-auto-top-off.md#81-phase-0--sst-water-detection-hello-world) contains the governing design and phase plan.

## Phase 0 — SST water-detection hello world

**Status: firmware compile validation passed; all physical validation is pending.**
Phase 0 is a supervised, low-energy, dry-bench experiment. It proves only a
protected binary SST input, an external LED, and change-only serial reporting.
It has no pump, relay, MOSFET, other sensor, Wi-Fi, metrics, enclosure, or
aquarium installation. Passing it does not authorize unattended operation or
aquarium installation.

Use a separate cup of water, not the aquarium. Only the SST optical prism tip
may contact water. Keep the ESP32, breadboard, USB cable, bench supply, and all
exposed conductors dry; wear eye protection if available and turn power off
before rewiring. No pump or other actuator may be connected. There is no
independent high-water cutoff, and this experiment cannot distinguish water
from disconnected wiring or lost sensor power. No enclosure or structural part
is needed, so Phase 0 creates no OpenSCAD or STL files; the PLA/OpenSCAD
requirements begin when later phases add structural components.

### Required hardware

- 1 × Espressif ESP32-S3-DevKitC-1-N8R8.
- 1 × SparkFun SST Liquid Level Sensor, `SEN-13835` /
  `LLC200D3SH-LLPK1`.
- 1 × solderless breadboard and suitable jumper wires or test leads.
- 1 × data-capable Micro-USB/Micro-B cable for the board's USB-to-UART port.
- 1 × regulated bench power supply.
- 3 × 10 kΩ, ¼ W, 5% resistors: one upper-divider resistor and two in series
  for the 20 kΩ lower-divider resistance. Their four-band code is
  brown-black-orange, typically followed by a gold tolerance band.
- 1 × 330 Ω, ¼ W, 5% resistor. Its four-band code is orange-orange-brown,
  typically followed by a gold tolerance band.
- 1 × ordinary external LED.
- 1 × clean cup containing fresh water.

Resistor orientation does not matter. The LED anode is normally its longer
lead; the cathode is normally its shorter lead and corresponds to the package's
flat side. Recommended but not required: a digital multimeter, eye protection,
and a lint-free cloth for drying the sensor tip. No capacitor is required for
this minimal experiment.

### Exact circuit

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

1. Power the ESP32-S3 through its USB-to-UART Micro-B connector with the
   data-capable cable.
2. Set the bench supply to exactly 5.00 V with an approximately 50 mA current
   limit, and use it to power only the SST.
3. Connect SST red to bench +5.00 V and SST blue to bench ground.
4. Connect bench ground to an ESP32 pin labeled GND, establishing a common
   reference, and to the LED cathode.
5. Connect SST green through one 10 kΩ resistor to a junction node.
6. Connect the junction to the ESP32 header pin labeled GPIO4.
7. From that junction, connect two 10 kΩ resistors in series to ground; these
   are the 20 kΩ lower-divider resistance and external pull-down.
8. Connect GPIO5 through the 330 Ω resistor to the LED anode.
9. Do **not** connect bench +5 V to the ESP32 5 V pin while USB powers the board.
10. Never connect the raw green SST output directly to an ESP32 GPIO.

The SST is a 5 V-class push-pull source. The upper resistance is 10 kΩ and the
lower resistance is 20 kΩ:

`Vgpio = Vsensor_out × 20 kΩ / (10 kΩ + 20 kΩ)`

Thus a nominal 5.00 V sensor HIGH becomes approximately 3.33 V. Allowing for
the sensor output range, expect approximately 2.67–3.33 V when dry. A sensor
LOW of at most approximately 0.5 V becomes at most approximately 0.33 V. The
divider protects the 3.3 V ESP32 input from the output; the GPIO absolute
maximum is 3.6 V. The SST must not be powered from 3.3 V, which is below its
documented operating range, and its output must always pass through the
divider.

The 20 kΩ lower resistance also pulls GPIO4 LOW when the SST is disconnected or
unpowered. Consequently, disconnected/unpowered reads as WET and illuminates
the LED. This is conservative for future pump safety, but Phase 0 cannot tell
actual water from a power or wiring failure.

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

### Bring-up and test procedure

1. Put the breadboard, ESP32, supply, and exposed wiring on a dry surface away
   from the aquarium.
2. Leave USB disconnected and the bench-supply output OFF while wiring.
3. Configure 5.00 V and an approximately 50 mA limit with the output still OFF.
4. Identify header labels GPIO4, GPIO5, and GND; do not count physical pin
   positions, because board layouts and viewing direction can mislead.
5. Build and inspect the 10 kΩ/20 kΩ voltage divider.
6. Build and inspect the GPIO5–330 Ω–LED circuit, including LED polarity.
7. Connect the common bench/ESP32/LED ground.
8. Connect the red, blue, and green SST wires last.
9. If available, use a multimeter to verify resistor values and that +5 V is
   not accidentally shorted to ground.
10. Connect USB while leaving SST power OFF.
11. Install core 3.3.8, configure the IDE, and upload the sketch as above.
12. Open Serial Monitor at 115200 baud.
13. Press RESET after opening Serial Monitor to see the banner and initial state.
14. With SST power OFF, verify GPIO4 LOW/WET and LED ON. This is a
    fault-conservative electrical state, not proof that water is present.
15. Turn on the 5.00 V SST supply with its optical tip dry.
16. Verify GPIO4 HIGH/DRY, LED OFF, and the corresponding serial transition.
17. If available, measure GPIO4 to common ground: expect 2.67–3.33 V dry. Stop
    immediately and turn power off if it exceeds 3.6 V.
18. Touch or dip only the optical prism tip into the fresh-water cup. Never
    immerse its wire exit, connector, breadboard, or electronics.
19. Verify GPIO4 LOW/WET, LED ON, and the serial transition.
20. If available, verify approximately 0–0.33 V at GPIO4 while wet.
21. Remove the SST and gently blot only the optical tip dry.
22. Verify return to GPIO4 HIGH/DRY and LED OFF.
23. Repeat at least five wet/dry cycles and record every result below.
24. Turn the bench-supply output OFF before changing or disconnecting wiring.
25. Disconnect USB, dry the sensor, empty the cup, and store electronics dry.

Expected output contains the initial state and transitions only (aside from the
startup banner); steady polling does not repeat lines:

```text
Aquiloop SST + LED Phase 0
GPIO4: LOW -> WET; GPIO5 LED: ON
GPIO4: HIGH -> DRY; GPIO5 LED: OFF
```

### Troubleshooting

| Symptom | Checks and action |
| --- | --- |
| No serial port appears | Use the USB-to-UART connector and a known data cable; try another USB port, inspect the connector, and install any host driver required for the board's USB bridge. |
| Upload fails | Select the correct port and settings, close programs using the port, and retry the BOOT/reset sequence above. |
| No serial text appears | Set 115200 baud, open the correct port, and press RESET; the sketch prints steady states only once. |
| LED never turns on | Test with SST power OFF; check GPIO5, the 330 Ω value, common ground, and a reversed LED (short cathode/flat side belongs at ground). |
| LED is always on | Dry/blot the tip, confirm SST has 5.00 V and common ground, and inspect the green-wire divider; an unpowered/disconnected SST intentionally reads WET. |
| LED behavior is inverted | Confirm GPIO4 is the divider junction, GPIO5 drives the anode, and LOW means WET while HIGH means DRY; do not reverse this in firmware. |
| GPIO4 is above 3.6 V | Turn both supplies off immediately. Do not continue until one 10 kΩ upper and two series 10 kΩ lower resistors, their connections, and meter reference are corrected. Never bypass the divider. |
| State changes on power-up but not when dipped | Verify red/blue/green wire functions, use fresh water, clean the prism, dip only the optical tip, and check for a sound 5.00 V supply. |
| SST remains WET after removal | A retained droplet can keep the optical tip wet; gently blot it with a lint-free cloth. |
| State is noisy or rapidly changing | Stabilize the tip at the test boundary, check loose leads, common ground, supply current limiting, resistor junctions, and moisture near electronics. The small sketch intentionally adds no debounce beyond 50 ms polling. |
| Results are implausible | Power off and verify the 10 kΩ brown-black-orange and 330 Ω orange-orange-brown values, LED polarity, shared ground, and SST red = +5 V, blue = ground, green = output. Do not troubleshoot by swapping powered wires. |

### Validation record

**Physical validation is pending.** A person must complete this table; no
physical observations have been claimed.

| Test | Expected GPIO4 | Expected interpretation | Expected LED | Observed result | Pass/fail | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Sensor supply OFF | LOW | WET (fault-conservative) | ON |  |  |  |
| Sensor powered and dry | HIGH; 2.67–3.33 V if measured | DRY | OFF |  |  |  |
| Sensor tip wet | LOW; 0–0.33 V if measured | WET | ON |  |  |  |
| Sensor removed and blotted dry | HIGH | DRY | OFF |  |  |  |
| Five repeated wet/dry cycles | Alternating HIGH/LOW without unexpected transitions | DRY/WET | OFF/ON |  |  |  |

### Exit criteria

- The sketch compiles for the ESP32-S3 N8R8 configuration.
- Dry produces HIGH/DRY and LED OFF; wet produces LOW/WET and LED ON.
- SST power OFF produces the documented conservative LOW/WET state.
- A person records at least five cycles without unexpected transitions.
- GPIO4 never exceeds 3.6 V when measured, if a multimeter is available.
- Wiring and observations are recorded.

All physical criteria remain pending until the table is completed. Phase 0's
estimated hardware range is **$45–$75**, including the reusable ESP32 and SST.
Phase 1 builds on this verified protected input path and adds pump driving and
the first supervised top-off behavior; it is not part of this experiment.
