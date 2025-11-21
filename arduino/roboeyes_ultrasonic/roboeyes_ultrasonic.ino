/* RoboEyes Ultrasonic -> Serial Distance
 * Hardware: Arduino Uno + HC-SR04
 * Wiring:
 *   HC-SR04 TRIG -> D9
 *   HC-SR04 ECHO -> D8
 *   VCC -> 5V, GND -> GND
 * Serial protocol: prints lines "DIST:<cm>" about every 50ms.
 */

const int TRIG_PIN = 10;
const int ECHO_PIN = 9;

unsigned long lastSample = 0;
const unsigned long SAMPLE_INTERVAL_MS = 50; // 20 Hz

void setup(){
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  delay(50);
  Serial.println("RoboEyes Ultrasonic ready");
}

float readDistanceCM(){
  // Trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  // Measure echo pulse width
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL); // 30ms timeout (~5m)
  if(duration == 0){
    return -1.0; // timeout
  }
  // Speed of sound ~343 m/s -> 29.1 us per cm (round trip) / 2
  float distance = (duration / 58.0); // standard HC-SR04 conversion
  return distance; // in cm
}

void loop(){
  unsigned long now = millis();
  if(now - lastSample >= SAMPLE_INTERVAL_MS){
    lastSample = now;
    float d = readDistanceCM();
    if(d > 0){
      Serial.print("DIST:");
      Serial.println(d, 1); // one decimal
    }
  }
}
