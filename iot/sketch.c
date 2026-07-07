#include <WiFi.h>
#include <HTTPClient.h>
#include "DHTesp.h"

// ========== WiFi ==========
const char* ssid     = "Wokwi-GUEST";
const char* password = "";

// ========== ThingSpeak ==========
const String writeApiKey = "8FQ8R51WPPDDYFUE";
const String readApiKey  = "9ZS0RJBJ4JR3ZS4R";
const String channelID   = "3412304";

// ========== Pins ==========
#define DHT_PIN     15
#define PIR_PIN     14
#define LDR_PIN     34
#define LED_SALON   26
#define LED_CHAMBRE 27
#define LED_CUISINE 25

DHTesp dht;

bool ledSalon = false, ledChambre = false, ledCuisine = false;

unsigned long lastSensorSend = 0;
unsigned long lastLedPoll    = 0;
const unsigned long SENSOR_INTERVAL   = 15000;
const unsigned long LED_POLL_INTERVAL = 4000;

void setup() {
  Serial.begin(115200);
  dht.setup(DHT_PIN, DHTesp::DHT22);
  pinMode(PIR_PIN, INPUT);
  pinMode(LED_SALON,   OUTPUT);
  pinMode(LED_CHAMBRE, OUTPUT);
  pinMode(LED_CUISINE, OUTPUT);
  digitalWrite(LED_SALON,   LOW);
  digitalWrite(LED_CHAMBRE, LOW);
  digitalWrite(LED_CUISINE, LOW);

  WiFi.begin(ssid, password);
  Serial.print("[WiFi] Connexion");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\n[WiFi] OK — IP: " + WiFi.localIP().toString());
}

void applyLeds() {
  digitalWrite(LED_SALON,   ledSalon   ? HIGH : LOW);
  digitalWrite(LED_CHAMBRE, ledChambre ? HIGH : LOW);
  digitalWrite(LED_CUISINE, ledCuisine ? HIGH : LOW);
}

// Lit la DERNIERE valeur d'un champ ThingSpeak en texte brut (pas JSON)
// GET /channels/{id}/fields/{n}/last.txt  →  répond directement "1" ou "0"
// C'est l'endpoint le plus simple, pas de parsing JSON du tout
String readFieldRaw(String fieldNum) {
  HTTPClient http;
  String url = "http://api.thingspeak.com/channels/" + channelID
             + "/fields/" + fieldNum + "/last.txt"
             + "?api_key=" + readApiKey;
  http.begin(url);
  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.printf("[WARN] field%s HTTP %d\n", fieldNum.c_str(), code);
    http.end();
    return "0";
  }
  String val = http.getString();
  val.trim(); // retire \n et espaces
  http.end();
  Serial.printf("[TS] field%s = \"%s\"\n", fieldNum.c_str(), val.c_str());
  return val;
}

void pollLedStates() {
  if (WiFi.status() != WL_CONNECTED) return;
  Serial.println("[POLL] Lecture LEDs...");

  bool newSalon   = readFieldRaw("5") == "1";
  bool newChambre = readFieldRaw("6") == "1";
  bool newCuisine = readFieldRaw("7") == "1";

  if (newSalon != ledSalon || newChambre != ledChambre || newCuisine != ledCuisine) {
    ledSalon = newSalon; ledChambre = newChambre; ledCuisine = newCuisine;
    applyLeds();
    Serial.println("[LED] *** Changement applique ! ***");
  }
  Serial.printf("[LED] Salon:%s | Chambre:%s | Cuisine:%s\n",
    ledSalon?"ON":"OFF", ledChambre?"ON":"OFF", ledCuisine?"ON":"OFF");
}

void sendSensorData() {
  TempAndHumidity d = dht.getTempAndHumidity();
  if (isnan(d.temperature) || isnan(d.humidity)) {
    Serial.println("[ERROR] DHT22 echec"); return;
  }
  int pres  = digitalRead(PIR_PIN) == HIGH ? 1 : 0;
  int light = map(analogRead(LDR_PIN), 0, 4095, 0, 100);

  Serial.printf("[DATA] T=%.1f H=%.1f P=%d L=%d LED=%d%d%d\n",
    d.temperature, d.humidity, pres, light,
    ledSalon, ledChambre, ledCuisine);

  String url = "http://api.thingspeak.com/update?api_key=" + writeApiKey
    + "&field1=" + String(d.temperature, 1)
    + "&field2=" + String(d.humidity, 1)
    + "&field3=" + String(pres)
    + "&field4=" + String(light)
    + "&field5=" + (ledSalon   ? "1" : "0")
    + "&field6=" + (ledChambre ? "1" : "0")
    + "&field7=" + (ledCuisine ? "1" : "0");

  HTTPClient http;
  http.begin(url);
  int code = http.GET();
  String resp = http.getString();
  resp.trim();
  http.end();
  Serial.printf("[TS] Envoi capteurs entry_id=%s\n", resp.c_str());
}

void loop() {
  unsigned long now = millis();
  if (now - lastLedPoll    >= LED_POLL_INTERVAL) { lastLedPoll    = now; pollLedStates();  }
  if (now - lastSensorSend >= SENSOR_INTERVAL)   { lastSensorSend = now; sendSensorData(); }
  delay(100);
}
