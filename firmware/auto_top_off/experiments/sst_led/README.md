# SST water-detection hello world

This is the practical entry point for the supervised Phase 0 experiment. It
reads a SparkFun SST optical liquid-level sensor on GPIO4, lights an external
LED on GPIO5 when the sensor reports wet, and prints the initial state and later
changes. The [authoritative Phase 0 design](../../../../docs/design/aquarium-auto-top-off.md#81-phase-0--sst-water-detection-hello-world)
contains the same circuit, procedure, safety limits, and phase exit criteria.

## Scope and safety

Phase 0 is a supervised, low-energy, dry-bench experiment. Use a separate cup
of fresh water, **not the aquarium**. Only the SST optical prism tip may contact
water. Keep the ESP32, breadboard, USB cable, bench supply, exposed conductors,
wire exit, and connector dry. Wear eye protection if available and turn power
off before rewiring.

The ESP32 GPIO absolute maximum is 3.6 V. Never connect the raw sensor output to
a GPIO: it must pass through the divider below. Do not power the SST from 3.3 V;
that is below its documented operating range. Do not connect bench +5 V to the
ESP32 5 V pin while USB powers the board.

No pump, relay, MOSFET, other actuator, Wi-Fi, metrics, other sensor, enclosure,
or aquarium installation is part of this experiment. It has no independent
high-water cutoff and cannot distinguish water from disconnected wiring or
lost sensor power. Passing it does not authorize unattended operation or an
aquarium installation. No structural component is needed, so Phase 0 creates
no OpenSCAD or STL files; PLA/OpenSCAD requirements start when later phases add
structural components.

## Bill of materials

Required:

- 1 × Espressif ESP32-S3-DevKitC-1-N8R8.
- 1 × SparkFun SST Liquid Level Sensor, `SEN-13835` /
  `LLC200D3SH-LLPK1`.
- 1 × solderless breadboard.
- Suitable jumper wires or test leads.
- 1 × data-capable Micro-USB/Micro-B cable for the board's USB-to-UART port.
- 1 × regulated bench power supply.
- 3 × 10 kΩ, ¼ W, 5% resistors: one upper-divider resistor and two in
  series for the 20 kΩ lower resistance.
- 1 × 330 Ω, ¼ W, 5% resistor.
- 1 × ordinary external LED.
- 1 × clean cup containing fresh water.

A 10 kΩ four-band resistor is brown-black-orange, typically with a gold
tolerance band. A 330 Ω four-band resistor is orange-orange-brown, typically
with a gold tolerance band. Resistor orientation does not matter. The LED anode
is normally the longer lead; its cathode is normally shorter and corresponds
to the package's flat side.

Recommended, but not required: a digital multimeter, eye protection, and a
lint-free cloth for drying the sensor tip. No capacitor is required.

## Wiring

Wire only with USB disconnected and the bench output OFF:

1. Plan to power the ESP32 through its USB-to-UART Micro-B connector with the
   data-capable cable.
2. Set the bench supply to exactly 5.00 V for the SST sensor.
3. Set its current limit to approximately 50 mA.
4. Connect SST red to bench +5.00 V.
5. Connect SST blue to bench ground.
6. Connect bench ground to an ESP32 pin labeled GND.
7. Connect SST green to one end of a 10 kΩ resistor.
8. Connect the resistor's other end to a junction node.
9. Connect that node to the ESP32 header pin labeled GPIO4.
10. From the same node, connect two 10 kΩ resistors in series to ground; these
    make the 20 kΩ lower-divider resistance.
11. Connect GPIO5 through the 330 Ω resistor to the LED anode.
12. Connect the LED cathode to ground.
13. Do not connect bench +5 V to the ESP32 5 V pin while USB powers the board.
14. Never connect the raw green SST output directly to an ESP32 GPIO.

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

### Why the divider is required

The upper resistance is 10 kΩ and the lower resistance is 20 kΩ:

`Vgpio = Vsensor_out × 20 kΩ / (10 kΩ + 20 kΩ)`

A nominal 5.00 V sensor HIGH becomes approximately 3.33 V. Allowing for the
sensor output range, expect approximately 2.67–3.33 V while dry. A sensor LOW
of at most approximately 0.5 V becomes at most approximately 0.33 V. This
protects the 3.3 V input from the SST's 5 V-class push-pull output.

The 20 kΩ lower resistance also pulls GPIO4 LOW when the SST is disconnected or
unpowered. Thus sensor-off appears as WET and turns the LED on. That is
conservative for future pump safety, but Phase 0 cannot tell real water from a
sensor-power or wiring failure.

## Arduino IDE 2.x setup and upload

1. Install Arduino IDE 2.x.
2. In **Preferences**, add this Additional Boards Manager URL:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
3. In Boards Manager, install `esp32` by Espressif Systems and select version
   **3.3.8** for this reproducible environment.
4. Open `sst_led.ino` and select **ESP32S3 Dev Module**.
5. Set **Flash Size** to **8 MB**.
6. Set **Partition Scheme** to **8M with spiffs**.
7. Set **Flash Mode** to **QIO 80MHz**.
8. Set **PSRAM** to **OPI PSRAM**.
9. Set **Upload Mode** to **UART0 / Hardware CDC**.
10. Connect the USB-to-UART Micro-B port and select its serial port.
11. Click **Upload**. If it fails, confirm the cable carries data and the port is
    correct, then use the BOOT/reset download sequence described by Espressif:
    hold BOOT, press and release reset, release BOOT, and retry upload.

## Bring-up and test procedure

1. Put the breadboard, ESP32, supply, and all exposed wiring on a dry surface
   away from the aquarium.
2. Leave USB disconnected and the bench output OFF while wiring.
3. Configure 5.00 V and approximately a 50 mA current limit, output still OFF.
4. Identify header labels GPIO4, GPIO5, and GND; do **not** count physical pin
   positions because board variants and orientation make that error-prone.
5. Build and inspect the 10 kΩ/20 kΩ voltage divider.
6. Build and inspect the GPIO5, 330 Ω, and LED circuit.
7. Connect the common bench/ESP32/LED ground.
8. Connect the sensor red, blue, and green wires last.
9. If a multimeter is available, verify resistor values and check that +5 V is
   not accidentally shorted to ground before power is applied.
10. Connect ESP32 USB while leaving the sensor supply OFF.
11. Install and upload the sketch with the Arduino procedure above.
12. Open Serial Monitor at 115200 baud.
13. Press reset after opening Serial Monitor to see the banner and initial state.
14. With sensor power OFF, verify GPIO4 LOW/WET and LED ON. This is a
    fault-conservative electrical state, **not proof that water is present**.
15. Turn on the 5.00 V sensor supply while keeping the optical tip dry.
16. Verify GPIO4 HIGH/DRY, LED OFF, and the matching serial message.
17. If available, measure GPIO4 to common ground: expect 2.67–3.33 V dry. Stop
    immediately and turn power off if it exceeds 3.6 V.
18. Touch or dip only the optical prism tip into fresh water. Do not immerse the
    wire exit, connector, breadboard, or electronics.
19. Verify GPIO4 LOW/WET, LED ON, and the matching serial message.
20. If available, verify approximately 0–0.33 V at GPIO4 while wet.
21. Remove the sensor and gently blot only the optical tip dry.
22. Verify HIGH/DRY and LED OFF return.
23. Repeat at least five wet/dry cycles and record every result below.
24. Turn the bench output OFF before changing or disconnecting wiring.
25. Disconnect USB, dry the sensor, empty the cup, and store electronics dry.

## Expected behavior

The sketch polls approximately every 50 ms. It prints a startup banner, its
initial reading, and transitions only. HIGH means DRY and LED LOW/OFF; LOW means
WET and LED HIGH/ON. Typical output is:

```text
Aquiloop SST + LED Phase 0
GPIO4: LOW -> WET; GPIO5 LED: ON
GPIO4: HIGH -> DRY; GPIO5 LED: OFF
```

## Troubleshooting

- **No serial port appears:** use the USB-to-UART connector, try a known
  data-capable cable and another USB port, and check OS USB/serial permissions.
- **Upload fails:** select the correct ESP32S3 board and port, recheck all menu
  settings, disconnect anything loading GPIOs, and try the BOOT/reset sequence.
- **No serial text appears:** choose 115200 baud and press reset after opening
  Serial Monitor; verify the upload succeeded and the correct port is open.
- **LED never turns on:** test sensor-OFF first, check GPIO5 and the 330 Ω value,
  common ground, and LED polarity; the longer anode faces GPIO5.
- **LED is always on:** the input is LOW; check sensor power, common ground,
  red/blue/green wire identity, tip droplets, and the divider junction.
- **LED behavior is inverted:** verify the LED goes from GPIO5 through 330 Ω to
  anode and cathode to ground; do not reverse the SST wet/dry interpretation.
- **GPIO4 is above 3.6 V:** turn both supplies off immediately. Do not continue
  until the upper 10 kΩ and two-series-10 kΩ lower divider are corrected.
- **Sensor changes when powered but not when dipped:** dip only the optical prism
  far enough to cover its sensing faces; confirm fresh water is clean and the
  sensor wires are red = +5 V, blue = ground, green = output.
- **Sensor remains wet after removal:** a retained droplet can cause LOW; gently
  blot the optical tip with a lint-free cloth and retest.
- **Noisy or rapidly changing state:** keep leads short, inspect loose
  breadboard contacts and common ground, keep the tip steadily wet or fully dry,
  and confirm the supply is regulated at 5.00 V. The sketch intentionally has no
  production debounce beyond its 50 ms polling.
- **Missing common ground:** the reading is undefined; join bench ground,
  ESP32 GND, divider ground, and LED cathode ground.
- **Reversed LED polarity:** turn power off and swap it so the long anode faces
  the GPIO5 resistor and the short/flat-side cathode faces ground.
- **Incorrect resistor values:** power off and verify with color bands or a
  meter: divider resistors are 10 kΩ and LED resistance is 330 Ω.
- **Wrong sensor wire connections:** power off immediately and restore red to
  +5.00 V, blue to common ground, and green only through 10 kΩ to the node.

## Shutdown

Turn the bench output OFF before touching wiring, then disconnect USB. Blot the
optical tip, empty the test cup, inspect for moisture, and store all electronics
dry.

## Validation record

**Physical validation: PENDING.** A person must complete this table; no physical
results are claimed here.

| Test | Expected GPIO4 | Expected interpretation | Expected LED | Observed result | Pass/fail | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Sensor supply OFF | LOW | WET (fault-conservative) | ON |  |  |  |
| Sensor powered and dry | HIGH | DRY | OFF |  |  |  |
| Sensor tip wet | LOW | WET | ON |  |  |  |
| Sensor removed and blotted dry | HIGH | DRY | OFF |  |  |  |
| Five repeated wet/dry cycles | HIGH/LOW each cycle | DRY/WET each cycle | OFF/ON each cycle |  |  |  |
