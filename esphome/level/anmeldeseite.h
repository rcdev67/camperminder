// Anmeldeseite - die Wasserwaage oeffnet sich von selbst, sobald ein Handy
// dem eigenen Netz des Geraets beitritt.
//
// WARUM ES DAS GIBT
// =================
// Der Massstab ist ein Bluetooth-Geraet mit App: Ein Handgriff, und die
// Anzeige ist da. Bei uns waren es drei - Netz CamperMinder waehlen, Browser
// oeffnen, 192.168.4.1 tippen. Mit dem QR-Aufkleber (Code 1 tritt dem Netz
// bei) und dieser Datei ist es einer: Jedes Handy fragt nach dem Beitritt zu
// einem WLAN eine feste Adresse ab, um zu pruefen, ob es Internet gibt -
// Apple captive.apple.com/hotspot-detect.html, Android
// connectivitycheck.gstatic.com/generate_204, Windows www.msftconnecttest.com.
// Bekommt es statt der erwarteten Antwort eine Weiterleitung, haelt es das
// Netz fuer eines mit Anmeldung, wie im Hotel, und oeffnet die Seite dahinter
// von selbst. Die Seite dahinter ist hier die Wasserwaage.
//
// WARUM NICHT ESPHOMES captive_portal
// ===================================
// Das tut dasselbe, uebernimmt aber JEDE GET-Anfrage, solange das eigene Netz
// offen ist (canHandle in captive_portal.h: active_ && HTTP_GET) - die
// Wasserwaage waere nie erreichbar gewesen, nur seine WLAN-Einrichtung.
// Deshalb steht es bewusst nicht in der Firmware (camperminder-level.yaml).
//
// Diese Fassung ist schmal:
//
//   Namensdienst   beantwortet im eigenen Netz jede Anfrage nach einem Namen
//                  mit der Adresse des Geraets - so landet die Pruefanfrage
//                  des Handys ueberhaupt hier.
//   Umleitung      greift NUR, wenn eine Anfrage an einen fremden Namen
//                  gerichtet ist (Host-Kopf kein Adressliteral, kein .local).
//                  Die Geraeteseite spricht das Geraet immer ueber
//                  192.168.4.1 an und bleibt damit unberuehrt.
//
// Beides laeuft nur, solange das eigene Netz offen ist. Im Heim-WLAN ist es
// aus - dort gibt es einen echten Namensdienst, und niemand soll umgeleitet
// werden.
//
// Der Namensdienst folgt dem von ESPHome (captive_portal/
// dns_server_esp32_idf.cpp), mit zwei Abweichungen: Anfragen nach anderen
// Eintraegen als A (vor allem AAAA) bekommen sofort eine leere Antwort statt
// keiner - sonst wartet das iPhone auf eine Zeitueberschreitung. Und die
// Antwort traegt keine Zusatzeintraege: ESPHome laesst ar_count der Anfrage
// stehen, obwohl der EDNS-Eintrag dahinter ueberschrieben wird.
#pragma once

#include "esphome/core/log.h"
#include "esphome/components/network/ip_address.h"
#include "esphome/components/wifi/wifi_component.h"
#include "esphome/components/web_server_base/web_server_base.h"

#include <lwip/inet.h>
#include <lwip/sockets.h>

#include <cctype>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <string>

namespace anmeldeseite {

static const char *const TAG = "anmeldeseite";

inline bool eigenes_netz_offen() {
  return esphome::wifi::global_wifi_component != nullptr &&
         esphome::wifi::global_wifi_component->is_ap_active();
}

// Adresse des Geraets im eigenen Netz, in Netz-Byte-Reihenfolge und als Text.
// Aus der WLAN-Verwaltung gelesen statt abgeschrieben: Sie ist dieselbe, die
// in camperminder-level.yaml unter wifi: ap: manual_ip steht.
inline uint32_t eigene_adresse(char *text, size_t laenge) {
  ip4_addr_t a = esphome::wifi::global_wifi_component->wifi_soft_ap_ip();
  if (text != nullptr) ip4addr_ntoa_r(&a, text, laenge);
  return a.addr;
}

// --- Namensdienst ------------------------------------------------------------

struct Namensdienst {
  int fd = -1;
  uint8_t puffer[256];
};

inline Namensdienst &dienst() {
  static Namensdienst d;
  return d;
}

inline void dns_starten() {
  auto &d = dienst();
  if (d.fd >= 0) return;
  int fd = ::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (fd < 0) {
    ESP_LOGW(TAG, "Namensdienst: kein Socket (%d)", errno);
    return;
  }
  int ja = 1;
  ::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &ja, sizeof(ja));
  ::fcntl(fd, F_SETFL, ::fcntl(fd, F_GETFL, 0) | O_NONBLOCK);
  struct sockaddr_in adresse = {};
  adresse.sin_family = AF_INET;
  adresse.sin_port = htons(53);
  adresse.sin_addr.s_addr = htonl(INADDR_ANY);
  if (::bind(fd, (struct sockaddr *) &adresse, sizeof(adresse)) != 0) {
    ESP_LOGW(TAG, "Namensdienst: Port 53 belegt (%d)", errno);
    ::close(fd);
    return;
  }
  d.fd = fd;
  ESP_LOGI(TAG, "Eigenes Netz offen - Anmeldeseite aktiv");
}

inline void dns_stoppen() {
  auto &d = dienst();
  if (d.fd < 0) return;
  ::close(d.fd);
  d.fd = -1;
  ESP_LOGI(TAG, "Eigenes Netz zu - Anmeldeseite aus");
}

// Laenge der Frage hinter dem Kopf, oder 0, wenn sie nicht sauber endet.
inline size_t frage_laenge(const uint8_t *p, size_t n) {
  size_t i = 12;
  while (i < n && p[i] != 0) {
    const uint8_t teil = p[i];
    if (teil > 63 || i + teil + 1 >= n) return 0;  // Zeiger oder abgeschnitten
    i += teil + 1;
  }
  if (i >= n) return 0;  // Name nicht abgeschlossen
  i += 1 + 4;            // Nullbyte, Typ, Klasse
  return i <= n ? i - 12 : 0;
}

inline void dns_beantworten() {
  auto &d = dienst();
  if (d.fd < 0) return;
  const uint32_t ip = eigene_adresse(nullptr, 0);

  // Einige Anfragen je Durchgang, nicht nur eine: Ein Handy stellt nach dem
  // Beitritt mehrere auf einmal, und jede muss schnell zurueck.
  for (int runde = 0; runde < 8; runde++) {
    struct sockaddr_in von;
    socklen_t von_laenge = sizeof(von);
    const ssize_t n = ::recvfrom(d.fd, d.puffer, sizeof(d.puffer), MSG_DONTWAIT,
                                 (struct sockaddr *) &von, &von_laenge);
    if (n < 0) return;  // nichts mehr da
    uint8_t *p = d.puffer;
    if (n < 17) continue;

    const uint16_t flags = (p[2] << 8) | p[3];
    const uint16_t fragen = (p[4] << 8) | p[5];
    // Nur gewoehnliche Anfragen: keine Antwort, Opcode 0, genau eine Frage.
    if ((flags & 0x8000) || (flags & 0x7800) || fragen != 1) continue;

    const size_t frage = frage_laenge(p, (size_t) n);
    if (frage == 0) continue;
    const size_t ende_frage = 12 + frage;
    const uint16_t typ = (p[ende_frage - 4] << 8) | p[ende_frage - 3];
    const uint16_t klasse = (p[ende_frage - 2] << 8) | p[ende_frage - 1];
    const bool a_eintrag = typ == 0x0001 && klasse == 0x0001;

    // Kopf: Antwort, massgeblich, Rekursion gewuenscht wie angefragt und
    // verfuegbar, kein Fehler. Eine Antwort bei A, sonst leer.
    p[2] = 0x84 | (p[2] & 0x01);
    p[3] = 0x80;
    p[6] = 0;
    p[7] = a_eintrag ? 1 : 0;
    p[8] = p[9] = 0;    // keine Zustaendigen
    p[10] = p[11] = 0;  // keine Zusaetze

    size_t laenge = ende_frage;
    if (a_eintrag) {
      if (laenge + 16 > sizeof(d.puffer)) continue;
      uint8_t *a = p + laenge;
      a[0] = 0xC0;  // Zeiger auf den Namen in der Frage
      a[1] = 0x0C;
      a[2] = 0x00;  // Typ A
      a[3] = 0x01;
      a[4] = 0x00;  // Klasse IN
      a[5] = 0x01;
      // 60 s statt der 300 von ESPHome: Kommt das Handy danach ins Heim-WLAN,
      // soll die falsche Antwort nicht noch Minuten im Zwischenspeicher stehen.
      a[6] = a[7] = a[8] = 0x00;
      a[9] = 60;
      a[10] = 0x00;  // vier Bytes Adresse
      a[11] = 0x04;
      std::memcpy(a + 12, &ip, 4);
      laenge += 16;
    }
    ::sendto(d.fd, p, laenge, 0, (struct sockaddr *) &von, von_laenge);
  }
}

// --- Umleitung ---------------------------------------------------------------

// Ist der Host-Kopf ein fremder Name? Adressliterale (die Geraeteseite, jede
// Heimnetz-Adresse) und .local-Namen gehoeren dem Geraet und bleiben
// unberuehrt.
inline bool fremder_name(std::string host) {
  if (host.empty() || host[0] == '[') return false;  // leer oder IPv6-Literal
  const size_t doppelpunkt = host.find(':');
  if (doppelpunkt != std::string::npos) host.resize(doppelpunkt);
  for (auto &z : host) z = (char) std::tolower((unsigned char) z);
  if (host.empty()) return false;
  bool nur_ziffern = true;
  for (char z : host) {
    if (!std::isdigit((unsigned char) z) && z != '.') {
      nur_ziffern = false;
      break;
    }
  }
  if (nur_ziffern) return false;
  static const char ENDUNG[] = ".local";
  const size_t e = sizeof(ENDUNG) - 1;
  if (host.size() >= e && host.compare(host.size() - e, e, ENDUNG) == 0) return false;
  return true;
}

class Umleitung : public esphome::web_server_idf::AsyncWebHandler {
 public:
  bool canHandle(esphome::web_server_idf::AsyncWebServerRequest *request) const override {
    if (request->method() != HTTP_GET) return false;
    if (!eigenes_netz_offen()) return false;
    auto host = request->get_header("Host");
    return host.has_value() && fremder_name(*host);
  }

  void handleRequest(esphome::web_server_idf::AsyncWebServerRequest *request) override {
    char ip[16];
    eigene_adresse(ip, sizeof(ip));
    request->redirect(std::string("http://") + ip + "/");
  }
};

// Einmal beim Start, VOR dem Webserver der Geraeteseite (on_boot mit
// Prioritaet 600, der Webserver folgt mit 249): Die Handler werden in der
// Reihenfolge der Anmeldung gefragt, der erste Treffer gewinnt
// (request_handler_ in web_server_idf.cpp). Kaeme die Umleitung nach dem
// Webserver, beantwortete der "/" auch fuer fremde Namen selbst - dann liefe
// die Seite unter captive.apple.com statt unter 192.168.4.1.
inline void einrichten() {
  auto *basis = esphome::web_server_base::global_web_server_base;
  if (basis == nullptr) {
    ESP_LOGW(TAG, "Kein Webserver - keine Anmeldeseite");
    return;
  }
  basis->add_handler(new Umleitung());  // NOLINT - lebt so lange wie das Geraet
}

// Im Takt aufrufen (interval in hardware.yaml): Namensdienst an, wenn das
// eigene Netz aufgeht, aus, wenn es schliesst, und dazwischen beantworten.
inline void schritt() {
  if (eigenes_netz_offen()) {
    dns_starten();
    dns_beantworten();
  } else {
    dns_stoppen();
  }
}

}  // namespace anmeldeseite
