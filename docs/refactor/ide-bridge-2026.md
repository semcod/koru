# Plan refaktoryzacji autopilota Koru (2026)

## 🩺 Diagnoza: co dziś zawodzi
Z analizy problemów w kooperacji z edytorami (np. Cursor 3.5.17 / VS Code 1.105+ z mechanizmem `trustedPublishers`) wynikają poniższe klasy problemów technicznych:

1. **Cicha awaria aktywacji wtyczki**: VSIX zainstalowany przez `cursor --install-extension --force` nie aktywuje wtyczki, bo publisher `semcod` nie jest zaufany. Instalator traktuje kod wyjścia `0` jako sukces, a wtyczka pozostaje martwa.
2. **Niespójne źródła konfiguracji socketu**: Niezgodności między globalnymi ustawieniami użytkownika a plikiem `.cursor/settings.json` w projekcie.
3. **Wielość osieroconych daemonów**: Brak garbage collection / czyszczenia martwych gniazd unixowych po zamknięciu pętli `koru auto`.
4. **Generyczne komunikaty błędów**: Komunikat `plugins: []` maskuje wiele różnych przyczyn źródłowych.
5. **Brak kontraktu wersji**: Brak handshake'u sprawdzającego zgodność protokołu plugin ↔ daemon.

---

## 🎯 Cele refaktoryzacji
* **Diagnoza zamiast nadziei**: Każde niepowodzenie autopilota mapuje się na precyzyjną hipotezę i instrukcję naprawczą.
* **Jedno źródło prawdy**: Spójne i deterministyczne ścieżki gniazd IPC dla każdego z edytorów.
* **Aktywna weryfikacja wtyczki**: Potwierdzenie rzeczywistego uruchomienia i aktywacji rozszerzenia w edytorze.
* **Wsparcie dla nowych IDE**: Modularne adaptery per-IDE z prostym interfejsem.

---

## 🏗️ Architektura docelowa

```
┌────────────────────────────────────────────────────────────┐
│  koru auto / autonomous up                                 │
└────────────────────────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────────┐
│  IdeBridge — orkiestrator startu autopilota                │
│  • wybiera adapter wg lane                                 │
│  • uruchamia: ensure_daemon → ensure_plugin → handshake    │
│  • zwraca strukturę BridgeStatus z konkretnymi hipotezami  │
└────────────────────────────────────────────────────────────┘
       │            │                  │                │
       ▼            ▼                  ▼                ▼
   ┌────────┐  ┌────────┐         ┌─────────┐     ┌──────────┐
   │ Cursor │  │ VSCode │   …     │Antigrav │     │JetBrains │
   │Adapter │  │Adapter │         │Adapter  │     │Adapter   │
   └────────┘  └────────┘         └─────────┘     └──────────┘
```

### Interfejs `IdeAdapter` (`src/koru/ide_adapters/base.py`)
```python
class IdeAdapter(Protocol):
    ide_id: str
    capabilities: IdeCapabilities

    def detect(self) -> IdePresence: ...
    def install_plugin(self, vsix: Path) -> InstallReport: ...
    def verify_plugin_active(self, *, timeout_s: float) -> ActivationReport: ...
    def resolve_settings(self, *, project: Path, socket_path: Path) -> SettingsReport: ...
    def diagnose_inactive(self, *, runtime: IdePresence) -> list[Hypothesis]: ...
    def hint_remediation(self, hypothesis: Hypothesis) -> Remediation: ...
```

---

## 📅 Harmonogram wdrożenia

### Faza 0 — Szybkie poprawki (Quick Wins)
* **0.1**: Dodanie dokumentacji do `docs/` o `trustedPublishers` w Cursorze 1.105+.
* **0.2**: Wprowadzenie w `operator_pipeline.py` dedykowanej diagnozy i instrukcji dla `semcod` w `trustedPublishers`.
* **0.3**: Dodanie flagi `koru autopilot status --explain`.
* **0.4**: Garbage collection (usuwanie) martwych/starych plików `.sock` przy starcie.
* **0.5**: Reconciliacja i ostrzeżenie o niezgodności socketu w `settings.json`.

### Faza 1 — Abstrakcja `IdeAdapter`
Przeniesienie rozproszonej logiki rozgałęzień per-IDE do wyizolowanych modułów w `src/koru/ide_adapters/`.

### Faza 2 — Aktywny uścisk dłoni (Handshake) i E2E Echo
Wdrożenie protokołu powitalnego z weryfikacją wersji kontraktu oraz komendy `koru autopilot drive --probe` sprawdzającej poprawność wpisywania tokenów.

### Faza 3 — Inteligentna autodiagnoza i samonaprawa
Automatyczne rozwiązywanie prostych konfliktów (usuwanie nieaktywnych socketów, zapisywanie zaufanych wydawców, reload okna IDE).

### Faza 4 — `koru ide doctor --fix`
Stworzenie jednego, wszechstronnego CLI do natychmiastowego testowania i naprawiania całego łańcucha połączenia z IDE.
