# SST water-detection hello world

This is the practical entry point for the supervised Phase 0 experiment. It
reads a SparkFun SST liquid-level sensor on GPIO4, lights an external LED on
GPIO5 only when the input is wet, and reports the initial state and changes at
115200 baud. The [authoritative Phase 0 design](../../../../docs/design/aquarium-auto-top-off.md#81-phase-0--sst-water-detection-hello-world)
contains the same electrical requirements and the phase exit criteria.

Phase 0 deliberately has no pump, relay, MOSFET, Wi-Fi, metrics, other sensor,
enclosure, or aquarium installation. It is not production controller logic.

## Safety and scope

Phase 0 is a supervised, low-energy, dry-bench experiment. Use a separate clean
cup of fresh water, not the aquarium, and allow only the SST optical prism tip
to contact water. Keep the ESP32, breadboard, USB cable, bench supply, exposed
conductors, sensor wire exit, and connector dry. Wear eye protection if desired.
Turn power off before rewiring.

The ESP32 GPIO absolute maximum is 3.6 V. Do not power the SST from 3.3 V; that
is below its documented operating range. Its output must pass through the
10 kΩ/20 kΩ divider and must never connect raw to a GPIO. Do not connect bench
+5 V to the ESP32 5 V pin while USB powers the board. No pump or other actuator
may be connected. There is no independent high-water cutoff, and LOW/WET cannot
distinguish water from disconnected wiring or lost sensor power. Passing this
experiment does not authorize unattended operation or aquarium installation.
No enclosure or structural part is needed, so Phase 0 creates no OpenSCAD or
STL files; PLA/OpenSCAD requirements begin with later structural phases.

## Bill of materials

Required:

- 1 × Espressif ESP32-S3-DevKitC-1-N8R8.
- 1 × SparkFun SST Liquid Level Sensor, `SEN-13835` /
  `LLC200D3SH-LLPK1`.
- 1 × solderless breadboard and suitable jumper wires or test leads.
- 1 × data-capable Micro-USB/Micro-B cable for the board USB-to-UART port.
- 1 × regulated bench power supply.
- 3 × 10 kΩ, ¼ W, 5% resistors: one upper resistor and two in series for
  the 20 kΩ lower resistance.
- 1 × 330 Ω, ¼ W, 5% resistor and 1 × ordinary external LED.
- 1 × clean cup containing fresh water.

A 10 kΩ four-band resistor is brown-black-orange, typically with a gold
tolerance band. A 330 Ω four-band resistor is orange-orange-brown, typically
with a gold tolerance band. Resistor orientation does not matter. The LED anode
is normally the longer lead; its cathode is normally shorter and corresponds
to the package's flat side.

Recommended, not required: a digital multimeter, eye protection, and a
lint-free cloth for drying the sensor tip. No capacitor is required.

## Exact wiring

1. Power the ESP32-S3 through its USB-to-UART Micro-B connector with the
   data-capable cable.
2. Configure the bench supply for exactly 5.00 V and an approximately 50 mA
   current limit; it powers only the SST.
3. Connect SST red to bench +5.00 V and SST blue to bench ground.
4. Connect bench ground to an ESP32 pin labeled GND for a common reference.
5. Connect SST green through one 10 kΩ resistor to a junction node.
6. Connect the junction to the ESP32 header pin labeled GPIO4.
7. Connect the junction through two series 10 kΩ resistors to ground; together
   they are the 20 kΩ lower resistance.
8. Connect GPIO5 through the 330 Ω resistor to the LED anode.
9. Connect the LED cathode to ground.
10. Do not connect bench +5 V to the ESP32 5 V pin while it is USB-powered.
11. Never connect the raw SST green output directly to an ESP32 GPIO.

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

The upper resistance is 10 kΩ and lower resistance is 20 kΩ:

`Vgpio = Vsensor_out × 20 kΩ / (10 kΩ + 20 kΩ)`

A nominal 5.00 V sensor HIGH becomes approximately 3.33 V. Allowing for the
sensor output range, expect approximately 2.67–3.33 V when dry. A sensor LOW of
at most approximately 0.5 V becomes at most approximately 0.33 V. This protects
the 3.3 V input from the sensor's 5 V-class push-pull output. The lower 20 kΩ
also pulls GPIO4 LOW when the sensor is disconnected or unpowered. Thus that
fault appears as WET: conservative for future pump safety, although Phase 0
cannot distinguish it from actual water.

## Arduino IDE 2.x setup and upload

1. In Arduino IDE 2.x, add this **Additional Boards Manager URL**:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
2. In Boards Manager, install `esp32` by Espressif Systems and select version
   **3.3.8** for this reproducible environment.
3. Select board **ESP32S3 Dev Module** and these Tools options:
   - Flash Size: **8 MB**
   - Partition Scheme: **8M with spiffs**
   - Flash Mode: **QIO 80MHz**
   - PSRAM: **OPI PSRAM**
   - Upload Mode: **UART0 / Hardware CDC**
4. Open `sst_led.ino`, connect the board at its USB-to-UART Micro-B port, and
   select the corresponding serial port.
5. Click Upload. If it fails, confirm the cable carries data and the correct
   port is selected, then use the BOOT/reset sequence documented by Espressif:
   hold BOOT, press and release reset, release BOOT, and retry.

## Bring-up and test procedure

1. Put the breadboard, ESP32, supply, and exposed wiring on a dry surface away
   from the aquarium.
2. Keep USB disconnected and the bench-supply output OFF while wiring.
3. Set the supply to 5.00 V and approximately 50 mA current limit, output OFF.
4. Identify header labels GPIO4, GPIO5, and GND; do not count physical pin
   positions because board variants and orientation make that unsafe.
5. Build and inspect the 10 kΩ upper/20 kΩ lower divider.
6. Build and inspect the GPIO5, 330 Ω, LED circuit.
7. Connect common ground.
8. Connect the red, blue, and green sensor wires last.
9. If available, use a multimeter to verify resistor values and no accidental
   short between +5 V and ground.
10. Connect USB while leaving the sensor supply OFF.
11. Install core 3.3.8 and upload with the Arduino IDE procedure above.
12. Open Serial Monitor at 115200 baud.
13. Press reset after opening Serial Monitor to see the banner and initial state.
14. With sensor power OFF, verify GPIO4 LOW/WET and LED ON. This is a
    fault-conservative electrical state, not proof of water.
15. Turn on the 5.00 V supply while keeping the optical tip dry.
16. Verify GPIO4 HIGH/DRY, LED OFF, and the serial transition.
17. If available, measure GPIO4 to common ground: expect 2.67–3.33 V dry. Stop
    immediately and switch power OFF if it exceeds 3.6 V.
18. Touch or dip only the optical prism tip into fresh water. Do not immerse the
    wire exit, connector, breadboard, or electronics.
19. Verify GPIO4 LOW/WET, LED ON, and the serial transition.
20. If available, verify approximately 0–0.33 V at GPIO4 while wet.
21. Remove the sensor and gently blot the optical tip with a lint-free cloth.
22. Verify return to GPIO4 HIGH/DRY and LED OFF.
23. Repeat at least five wet/dry cycles and record every result below.
24. Turn the bench-supply output OFF before changing or disconnecting wiring.
25. Disconnect USB, dry the tip, empty the cup, and store electronics dry.

Expected output contains the initial state and transitions only:

```text
Aquiloop SST + LED Phase 0
GPIO4: LOW -> WET; GPIO5 LED: ON
GPIO4: HIGH -> DRY; GPIO5 LED: OFF
```

## Troubleshooting

| Symptom | Checks and corrective action |
| --- | --- |
| No serial port appears | Use the USB-to-UART connector, try a known data cable/USB port, and check the OS device list and driver. |
| Upload fails | Select the correct board/port/options; close competing serial tools; retry the Espressif BOOT/reset sequence above. |
| No serial text appears | Set 115200 baud, press reset after opening Serial Monitor, and confirm the sketch uploaded. |
| LED never turns on | Test sensor supply OFF; check GPIO5, 330 Ω, common ground, and reversed LED polarity. |
| LED is always on | Dry/blot the tip; verify SST power, common ground, divider continuity, and correct red/blue/green wires. |
| LED behavior is inverted | Confirm the LED is GPIO5-to-resistor-to-anode and firmware is LOW=WET/HIGH=DRY; do not swap sensor meaning. |
| GPIO4 is above 3.6 V | Switch power OFF immediately; correct the 10 kΩ upper and two-series-10 kΩ lower divider before reconnecting. |
| State changes on power but not when dipped | Dip only a clean prism tip; verify 5.00 V, wire colors, orientation, and clean the optical surface. |
| Sensor remains wet after removal | A retained droplet can cause LOW; gently blot the prism dry. |
| State changes rapidly | Stabilize leads and supply, clean/blot the tip, verify the 50 mA limit is not tripping, common ground, and resistor connections. |
| Missing common ground | Power OFF, then connect bench ground to ESP32 GND; without it GPIO4 has no valid shared reference. |
| Reversed LED polarity | Power OFF and put the long anode toward the 330 Ω/GPIO5 side and short/flat-side cathode toward ground. |
| Incorrect resistor values | Meter or decode them: 10 kΩ brown-black-orange; 330 Ω orange-orange-brown; gold commonly denotes 5%. |
| Sensor wires are wrong | Power OFF: red is +5.00 V, blue is ground, and green goes only through the upper 10 kΩ resistor. |

## Validation record

**Physical validation status: PENDING.** A person must record observations; no
physical result is claimed by this repository change.

| Test | Expected GPIO4 | Expected interpretation | Expected LED | Observed result | Pass/fail | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Sensor supply OFF | LOW | WET (fault-conservative) | ON |  |  |  |
| Sensor powered and dry | HIGH, 2.67–3.33 V if measured | DRY | OFF |  |  |  |
| Sensor tip wet | LOW, 0–0.33 V if measured | WET | ON |  |  |  |
| Sensor removed and blotted dry | HIGH | DRY | OFF |  |  |  |
| Five repeated wet/dry cycles | Alternating HIGH/LOW | DRY/WET | OFF/ON |  |  |  |

## Shutdown

Switch the bench output OFF before touching wiring, disconnect USB, blot the
optical tip dry, empty the test cup, and store all electronics dry. Physical
Phase 0 validation remains pending until the table is completed, including at
least five cycles and any available GPIO4 voltage measurements.
