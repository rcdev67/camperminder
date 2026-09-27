// Werkskalibrierung - der Sensor-Nullpunkt ab Werk, im eigenen Flash-Bereich.
//
// Der Beschleunigungssensor hat einen eigenen Nullpunktfehler, beim
// LSM6DS3TR-C laut Datenblatt bis etwa 40 mg - das sind gut 2 Grad und damit
// mehr, als eine Toleranz von 3 cm verträgt. Vor der Auslieferung wird er
// einmal gemessen (Werkstattbereich der Geräteseite) und hier abgelegt.
//
// Der Bereich "werk" (partitions.csv) liegt AUSSERHALB der Einstellungen:
// "Werkseinstellungen" löscht den nvs-Bereich vollständig, diesen nicht. Der
// Kunde landet nach einem Zurücksetzen also wieder auf "ab Werk kalibriert",
// nicht auf "nie kalibriert".
//
// Korrigiert wird an den Rohachsen des Chips (accel_x, accel_y), nicht an
// Pitch und Roll. Damit gilt die Werkskalibrierung für jede Einbaulage und
// jede Achszuordnung; die Kalibrierung im Fahrzeug (pitch_offset,
// roll_offset) kommt unverändert obendrauf.

#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>

#include "esp_partition.h"
#include "esp_rom_crc.h"

namespace werk {

// "CMWK" - erkennt einen leeren oder fremd beschriebenen Bereich.
static const uint32_t MAGIE = 0x4B574D43;
// Beim Ändern von Daten hochzählen; ältere Einträge gelten dann als fehlend.
static const uint16_t FASSUNG = 1;
// Mehr als 0,1 g Nullpunktfehler hat kein heiler Sensor - so etwas wird
// weder gespeichert noch angewendet.
static const float GRENZE_G = 0.1f;

struct Daten {
  uint32_t magie;
  uint16_t fassung;
  uint16_t laenge;       // sizeof(Daten) beim Schreiben
  float bx;              // Nullpunktfehler Chipachse X, in g
  float by;              // Nullpunktfehler Chipachse Y, in g
  float temp;            // Sensortemperatur bei der Messung, °C (NAN = unbekannt)
  uint32_t uhr;          // Unix-Zeit der Messung (0 = keine gültige Uhr)
  float unterlage_x;     // Neigung der Unterlage bei der Messung, in g - nur
  float unterlage_y;     // zur Nachvollziehbarkeit, angewendet wird sie nie
  uint32_t pruefsumme;   // CRC32 über alles davor
};

inline const esp_partition_t *bereich() {
  return esp_partition_find_first(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_ANY, "werk");
}

inline uint32_t summe(const Daten &d) {
  return esp_rom_crc32_le(0, reinterpret_cast<const uint8_t *>(&d), offsetof(Daten, pruefsumme));
}

inline bool plausibel(float wert) { return std::isfinite(wert) && std::fabs(wert) <= GRENZE_G; }

// true nur für einen vollständigen, unversehrten Eintrag.
inline bool lesen(Daten &d) {
  const esp_partition_t *b = bereich();
  if (b == nullptr) return false;
  if (esp_partition_read(b, 0, &d, sizeof(d)) != ESP_OK) return false;
  return d.magie == MAGIE && d.fassung == FASSUNG && d.laenge == sizeof(Daten) &&
         d.pruefsumme == summe(d) && plausibel(d.bx) && plausibel(d.by);
}

inline bool schreiben(Daten d) {
  const esp_partition_t *b = bereich();
  if (b == nullptr || !plausibel(d.bx) || !plausibel(d.by)) return false;
  d.magie = MAGIE;
  d.fassung = FASSUNG;
  d.laenge = sizeof(Daten);
  d.pruefsumme = summe(d);
  if (esp_partition_erase_range(b, 0, b->size) != ESP_OK) return false;
  if (esp_partition_write(b, 0, &d, sizeof(d)) != ESP_OK) return false;
  // Gegenlesen: Erst was wirklich im Flash steht, gilt als gespeichert.
  Daten kontrolle{};
  return lesen(kontrolle) && kontrolle.bx == d.bx && kontrolle.by == d.by;
}

}  // namespace werk
