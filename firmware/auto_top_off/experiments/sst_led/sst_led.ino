// Aquiloop Phase 0: protected SST input and one external status LED.
constexpr uint8_t SENSOR_PIN = 4;
constexpr uint8_t LED_PIN = 5;
constexpr unsigned long POLL_INTERVAL_MS = 50;

int previousLevel = -1;

void reportState(int level) {
  // The SST polarity is inverted: HIGH is dry and LOW is wet.
  const bool wet = level == LOW;
  digitalWrite(LED_PIN, wet ? HIGH : LOW);
  Serial.printf("GPIO4: %s -> %s; GPIO5 LED: %s\n",
                level == HIGH ? "HIGH" : "LOW", wet ? "WET" : "DRY",
                wet ? "ON" : "OFF");
}

void setup() {
  // Preload OFF before enabling the output to avoid an LED-on glitch at boot.
  digitalWrite(LED_PIN, LOW);
  pinMode(LED_PIN, OUTPUT);

  // The external 10 kΩ/20 kΩ divider both limits voltage and pulls GPIO4 low.
  pinMode(SENSOR_PIN, INPUT);
  Serial.begin(115200);
  delay(250);
  Serial.println("Aquiloop SST + LED Phase 0");

  previousLevel = digitalRead(SENSOR_PIN);
  reportState(previousLevel);
}

void loop() {
  const int level = digitalRead(SENSOR_PIN);
  if (level != previousLevel) {
    previousLevel = level;
    reportState(level);
  }
  delay(POLL_INTERVAL_MS);
}
