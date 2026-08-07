constexpr int SENSOR_PIN = 4;
constexpr int LED_PIN = 5;
constexpr unsigned long POLL_INTERVAL_MS = 50;

int lastSensorLevel = -1;

void reportState(int sensorLevel) {
  // The SST output is inverted: HIGH is dry and LOW is wet.
  const bool wet = sensorLevel == LOW;
  digitalWrite(LED_PIN, wet ? HIGH : LOW);

  Serial.print("GPIO4: ");
  Serial.print(sensorLevel == HIGH ? "HIGH -> DRY" : "LOW -> WET");
  Serial.print("; GPIO5 LED: ");
  Serial.println(wet ? "ON" : "OFF");
}

void setup() {
  Serial.begin(115200);

  // Preload OFF before enabling the LED output to avoid a startup flash.
  digitalWrite(LED_PIN, LOW);
  pinMode(LED_PIN, OUTPUT);
  // The external 10 kΩ/20 kΩ voltage divider supplies the pull-down.
  pinMode(SENSOR_PIN, INPUT);

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
