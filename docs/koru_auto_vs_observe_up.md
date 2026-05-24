# Koru Auto vs Koru Observe Up & Kompatybilność z IDE

Ten dokument wyjaśnia różnice pomiędzy dwoma najważniejszymi poleceniami w ekosystemie Koru oraz szczegółowo omawia wyzwania i ograniczenia dotyczące kompatybilności z poszczególnymi środowiskami programistycznymi (IDE).

---

## 1. Porównanie i Przeznaczenie Komend

Choć oba polecenia są kluczowe w pracy z Koru, realizują one zupełnie odmienne zadania:

| Cecha | `koru auto` (alias `autonomous`) | `koru observe up` |
|---|---|---|
| **Rola** | **Silnik Wykonawczy** (Aktywny agent) | **System Telemetryczny** (Pasorny obserwator) |
| **Główny cel** | Automatyczne pobieranie zadań, sterowanie czatem IDE i kodowaniem. | Monitorowanie pracy agenta, zbieranie logów, zrzutów ekranu i dashboard. |
| **Interakcja z kodem** | **Aktywna:** Modyfikuje pliki, wstrzykuje prompty, uruchamia Quality Gates. | **Pasywna:** Nie modyfikuje kodu, nie wpływa na pliki. |
| **Mechanizm działania** | Odpala `AutopilotDaemon`, symuluje klawiaturę, odpala pętlę testową pytest. | Odpala `koru vision` (zrzuty ekranu), `koru mesh` i stawia dashboard na porcie `8765`. |
| **Użycie pamięci** | Średnie, skupione na pętli CLI i testowej. | Wyższe (ze względu na zrzuty ekranu i WebSocket mesh). |

### Jak używać ich razem?
W pełnym cyklu autonomicznym uruchamiasz je w dwóch osobnych terminalach:
1. `koru observe up` stawia kokpit (dashboard) i zbiera zrzuty ekranu z Twojego ekranu pracy.
2. `koru auto` uruchamia pętlę, która "zatrudnia" Twoje IDE i krok po kroku automatycznie rozwiązuje zgłoszenia z planfile.

---

## 2. Dlaczego `koru auto` nie działa "out of the box" w każdym IDE?

Współpraca z różnymi IDE (np. Windsurf, Cursor, VS Code, JetBrains) wiąże się ze znaczącymi różnicami technologicznymi w architekturze tych programów.

### A. Brak oficjalnego API dla czatu w niektórych edytorach (np. Cursor)
* **VS Code / Windsurf:** Udostępniają bogate API dla wtyczek, pozwalając rozszerzeniom na bezpośrednie wstrzykiwanie tekstu do czatu i odczytywanie historii konwersacji (tzw. *Fast Path*).
* **Cursor:** Jest zamkniętym forkiem VS Code. Twórcy Cursora zaimplementowali swój wbudowany czat (AI Pane) całkowicie poza standardowym API wtyczek VS Code. **Wtyczki nie mają możliwości programistycznego pisania i czytania z czatu Cursora za pomocą kodu TypeScript.**

### B. Fallback na symulację klawiatury i problem z Waylandem
Gdy oficjalne API jest niedostępne (jak w Cursorze), Koru przełącza się na systemową symulację klawiatury (klika w okno czatu, wkleja tekst i wysyła). To rodzi kolejne wyzwania:
1. **Wayland vs X11:** Klasyczne narzędzia takie jak `xdotool` działają wyłącznie na serwerze graficznym X11. Na nowoczesnych dystrybucjach Linuxa używających Waylanda, systemy bezpieczeństwa blokują syntetyczne zdarzenia klawiatury dla innych okien.
   - *Rozwiązanie Koru:* Koru potrafi przełączyć się na `ydotool`, który komunikuje się bezpośrednio z jądrem systemu przez `/dev/uinput`, lecz wymaga to dodania użytkownika do grupy `input` i konfiguracji usługi systemowej.
2. **Kursor myszy i Focus:** Symulacja wymaga, aby okno Cursora było stale widoczne i aktywne na ekranie. Kliknięcie w inne okno w trakcie cyklu przerywa wklejanie promptu.

### C. Skróty klawiszowe wysyłania (Enter vs Ctrl+Enter)
Różne edytory i czaty mają inne zachowanie domyślne klawisza `Enter`:
- W VS Code/Windsurf naciśnięcie `Enter` w polu czatu wysyła prompt.
- W Cursorze naciśnięcie `Enter` wstawia nową linię (newline), a wysłanie wiadomości wymaga kombinacji **`Ctrl+Enter`** (lub `Cmd+Enter` na macOS). Koru musi precyzyjnie wykrywać aktywne IDE i symulować właściwy akcelerator klawiszowy.

---

## Podsumowanie i Rekomendacje

* Dla **Windsurf** i **VS Code** autopilot działa najstabilniej i najszybciej, ponieważ korzysta z bezpośredniego API rozszerzeń.
* Dla **Cursor** autopilot wymaga poprawnej konfiguracji focusu okna oraz uprawnień do `ydotool` (na Waylandzie), aby skutecznie symulować skrót `Ctrl+Enter`.

---

## 3. Zdalna Kontrola Sieciowa (Multi-Node Orchestration)

Dzięki wbudowanej bibliotece zdalnego sterowania `KoruRemoteClient`, możesz zarządzać, monitorować i wysyłać komendy do wszystkich uruchomionych IDE w całej sieci lokalnej z poziomu jednego centralnego skryptu.

### Jak to działa?
1. Na maszynach zdalnych (Node 1, Node 2) uruchamiasz serwer Koru:
   ```bash
   koru serve --host 0.0.0.0 --port 8765
   ```
2. Na swojej głównej maszynie sterującej używasz klasy `KoruRemoteClient`, aby połączyć się z wybranym komputerem i wysłać żądanie wstrzyknięcia tekstu (promptu) bezpośrednio do aktywnego IDE:

```python
from koru.remote import KoruRemoteClient

# Połącz się ze zdalną maszyną w sieci
remote_node = KoruRemoteClient(host="192.168.1.15", port=8765)

# Pobierz status maszyn i podłączone wtyczki IDE
status = remote_node.get_status()
print(f"Project: {status['project']}")

# Wyślij zdalną komendę wstrzyknięcia do Cursora na zdalnej maszynie!
response = remote_node.send_drive_command(
    ide="cursor",
    text="Refactor login view and add logs"
)
print("Response:", response)
```

