// Phase 0 uses an external divider: 10 kΩ above GPIO4 and 20 kΩ below it.
// The SST output polarity is inverted for water detection: HIGH is dry, LOW is wet.

constexpr uint8_t SENSOR_PIN = 4;
constexpr uint8_t LED_PIN = 5;
constexpr unsigned long POLL_INTERVAL_MS = 50;

int lastSensorLevel;

void reportState(int sensorLevel) {
  const bool wet = sensorLevel == LOW;
  digitalWrite(LED_PIN, wet ? HIGH : LOW);

  Serial.print("GPIO4: ");
  Serial.print(sensorLevel == HIGH ? "HIGH -> DRY" : "LOW -> WET");
  Serial.print("; GPIO5 LED: ");
  Serial.println(wet ? "ON" : "OFF");
}

void setup() {
  digitalWrite(LED_PIN, LOW);  // Preload the output latch before enabling output.
  pinMode(LED_PIN, OUTPUT);
  pinMode(SENSOR_PIN, INPUT);  // The 20 kΩ divider leg is the external pull-down.

  Serial.begin(115200);
  delay(250);
  Serial.println("Aquiloop SST + LED Phase 0");

  lastSensorLevel = digitalRead(SENSOR_PIN);
  reportState(lastSensorLevel);
}

void loop() {
  const int sensorLevel = digitalRead(SENSOR_PIN);
  if (sensorLevel != lastSensorLevel) {
    lastSensorLevel = sensorLevel;
    reportState(sensorLevel);
  }
  delay(POLL_INTERVAL_MS);
}
