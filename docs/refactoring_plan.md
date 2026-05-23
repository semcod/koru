# Plan Refaktoryzacji Architektury Koru

Ten dokument opisuje planowany podział kodu, eliminację cyklicznych zależności oraz dalsze usprawnienia w architekturze projektu **Koru**.

---

## 1. Wykryte obszary do poprawy (Technical Debt)

### A. Cykliczne zależności (Circular Imports)
Niedawno rozwiązany problem z `ImportError` w `koru.env_config` oraz `koru.bounded_contexts.env_config` pokazał, że architektura posiada zbyt ciasne powiązania między modułami domenowymi (CQRS Application Services) a pomocniczymi modułami konfiguracyjnymi (`env_config.py`).
* **Symptom:** Importowanie serwisów na poziomie modułów w plikach konfiguracyjnych i jednoczesne importowanie funkcji niskopoziomowych w serwisach.
* **Rozwiązanie:** Całkowite odseparowanie warstwy niskopoziomowych parserów (`env_config`, `dotenv_loader`) od warstwy logiki biznesowej/aplikacji (CQRS). Serwisy aplikacyjne powinny zależeć wyłącznie od czystych domenowych interfejsów lub repozytoriów.

### B. Monolityczny Daemon (`daemon.py`)
Plik `src/koruide/daemon.py` ma ponad 1200 linii kodu. Odpowiada za:
* Obsługę socketów sieciowych (select loop).
* Walidację i parsowanie wersji wtyczek.
* Serializację i deserializację wiadomości.
* Przechowywanie stanu sesji i logów konsoli (in-memory storage).
* Handoff i integrację z systemem powiadomień.
* **Rozwiązanie:** Podział `daemon.py` na mniejsze podmoduły w nowym pakiecie `koruide/daemon/`:
  - `koruide/daemon/server.py` — główna pętla i serwer socketów.
  - `koruide/daemon/storage.py` — thread-safe in-memory magazyn logów i sesji.
  - `koruide/daemon/handlers.py` — dyspenser i handlery poszczególnych komend.
  - `koruide/daemon/protocol.py` — walidacja wersji, protokołu i formatowanie komunikatów.

---

## 2. Etapy Refaktoryzacji

### Krok 1: Unifikacja i separacja warstwy danych
Przeniesienie globalnego stanu i operacji in-memory (jak baza logów konsolowych z wtyczek oraz sesji) do osobnej, zunifikowanej klasy `DaemonState` lub modułu `storage.py`.
Dzięki temu operacje takie jak `get_console_logs()`, `start_new_log_session()` i `add_console_log()` nie będą zaśmiecać głównej przestrzeni nazw modułu daemona.

### Krok 2: Podział `daemon.py`
Rozbicie monolitu na dedykowany pakiet:
```
src/koruide/daemon/
├── __init__.py
├── server.py       # Pętla select, obsługa połączeń i klientów
├── storage.py      # Thread-safe in-memory logi, sesje, stany wtyczek (max 10KB clamping)
├── protocol.py     # Definicje wiadomości, walidacja wersji
└── handlers.py     # Obsługa hello, status, session.started/ended, console_log
```

### Krok 3: Izolacja Modułu Konfiguracji Środowiskowej (`env_config`)
Wyeliminowanie konieczności stosowania lokalnych importów (inside-method imports) poprzez:
- Przeniesienie niskopoziomowych definicji kluczy (`KORU_ENV_KEYS`, `EnvKey`) oraz parsera `.env` do czystego pakietu `koru.domain.env`.
- Sprawienie, by serwisy CQRS wstrzykiwały i używały tych obiektów, zamiast importować je bezpośrednio z modułów klienckich/CLI.

---

## 3. Nowe Standardy i Dobre Praktyki
* **Clamping i limitowanie rozmiaru danych:** Każdy nowy endpoint API (taki jak `/api/plugin-logs` obcinany do 10KB na sesję) musi posiadać rygorystyczne limity rozmiaru przesyłanego payloadu, aby zapobiec problemom z wydajnością przeglądarki i zużyciem pamięci ram.
* **Separacja logiki I/O:** Przeniesienie wszelkich bezpośrednich zapisów na dysk (np. pliki `.env`, `.planfile`) do dedykowanych adapterów infrastruktury, dając możliwość łatwego mockowania w testach jednostkowych.
