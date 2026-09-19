---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "simple-task-model-routing",
  "kind": "analysis",
  "version": 2,
  "title": "Koru: model dla prostych zadan i pilotaz Flash",
  "status": "proposed",
  "owner": "semcod/koru",
  "scope": "repository",
  "created": "2026-09-19",
  "updated": "2026-09-19",
  "review_after": "2026-09-26",
  "source_revision": "684463445c60d5701b67de47a942924d1b114f67",
  "affected_repositories": [
    "semcod/koru"
  ],
  "evidence": [
    "https://github.com/semcod/koru/blob/684463445c60d5701b67de47a942924d1b114f67/src/koru/autonomy/cycle/cycle_drive_retry.py",
    "https://github.com/semcod/koru/issues/353",
    "https://docs.z.ai/guides/overview/pricing",
    "https://docs.astral.sh/ruff/linter/#fix-safety"
  ]
}
---

# Koru: wybór modelu dla prostych zadań

<!-- docs:section question -->
## Pytanie

Czy Koru na komputerze NVIDIA automatycznie wybiera `glm-5.3-flash`
dla prostych zgłoszeń z analizy kodu i czy mogłoby ograniczyć ich koszt?

<!-- docs:section scope -->
## Zakres

Właściciel wyniku: Koru. Badano jego lane `koru-lane-koru.service`,
ścieżkę shell → Tillm → opencode i najnowsze zgłoszenia `semcod/koru`.
To analiza działania konsumenta, nie audyt całej floty ani zmiana konfiguracji.
Konfigurację operatora opisuje [istniejący przewodnik](../llm-provider-configuration.md).

<!-- docs:section method -->
## Metoda

Obserwacja 2026-09-19 około 18:35–18:50 UTC: kod, tylko dozwolone pola
konfiguracji modelu, argumenty działającego procesu, odczyt SQLite opencode
w trybie read-only, katalog `opencode models zai` i 60 najnowszych issues.
Nie wyświetlano kluczy, promptów ani treści wiadomości. Nie wykonywano inferencji.

<!-- docs:section evidence -->
## Dowody

- `_drive_shell_client` w `src/koru/autonomy/cycle/cycle_drive_retry.py`
  przekazuje `KORU_TILLM_MODEL`; nie otrzymuje klasy trudności ticketu.
- `src/koru/queue/runners.py` dopuszcza `request.model`, następnie zmienną
  środowiskową. `repair_runs/router.py` wybiera modele według konfiguracji
  i poprzednich błędów; nie ocenia kosztu ani prostoty zadania.
- Jednostka systemd nie deklaruje modelu. Lokalny `.env` ustawia
  `KORU_TILLM_MODEL=zai/glm-5.3`; obserwowany proces opencode w katalogu Koru
  miał argument `-m zai/glm-5.3`. Początkowe `/proc/PID/environ` nie ujawnia
  wszystkich zmian środowiska dokonanych później przez aplikację.
- Lokalna baza opencode: w ostatnich siedmiu dniach dla katalogu Koru
  2084 wiadomości asystenta w 30 sesjach miały `zai/glm-5.3`.
  Ostatni taki zapis był z 17:27:01 UTC. W całej badanej bazie było **0**
  wiadomości asystenta z identyfikatorem zawierającym `glm-5.3-flash`.
  Są to rekordy modelu, nie dowód ukończenia zadań ani rozliczenie kosztów.
- `opencode models zai` zawiera `zai/glm-5.3-flash`.
  Obecność w katalogu nie potwierdza uprawnień konta ani udanej inferencji.

<!-- docs:section facts -->
## Ustalenia

**W badanej ścieżce Koru nie przełącza prostych zadań automatycznie na Flash.**
Globalny opencode wskazuje DeepSeek, ale wybór Koru nadpisuje go przy wykonaniu.

47 z 60 najnowszych issues miało etykietę `code2llm`; żadne nie miało etykiety
`ruff`. Przykłady: [#353](https://github.com/semcod/koru/issues/353),
[#351](https://github.com/semcod/koru/issues/351),
[#345](https://github.com/semcod/koru/issues/345).
Redukcja złożoności i dzielenie funkcji nie są automatycznie drobnymi poprawkami.
Podobne tytuły nie wystarczają do uznania zgłoszeń za duplikaty.

Kontrolny `ruff check src --output-format json --no-cache` na rewizji
`f59c310018cf649b06006945a0ca5dd35771701c` dał 7 ustaleń, w tym 5 z poprawką
oznaczoną `safe` (F541, UP035, F401, dwa UP017). E741 i E501 pozostały bez takiej
poprawki. Był to odczyt; nie zmieniono kodu ani statusów zgłoszeń.

[Cennik Z.ai](https://docs.z.ai/guides/overview/pricing), USD za milion tokenów:

| Model | Wejście | Wejście z cache | Wyjście |
| --- | ---: | ---: | ---: |
| GLM-5.3 | 1.40 | 0.26 | 4.40 |
| GLM-5.3-Flash | 0.15 | 0.03 | 0.50 |

Przy identycznej liczbie tokenów wejście jest 9,33 raza, a wyjście 8,8 raza tańsze.
To porównanie taryf API, nie zmierzona oszczędność pracy ani cena Coding Plan.

### Uzupełnienie: routing i widok logów, 2026-09-19

Ponowna obserwacja po publikacji audytu nadal nie znalazła wiadomości asystenta
`glm-5.3-flash` w lokalnej bazie opencode. Audyt nie wdrażał polityki wyboru modelu.
Test bez inferencji, na `_resolve_shell_llm_call_args` z rzeczywistym pinem lane:

| Wejście do resolvera | Wybrany model |
| --- | --- |
| Jeden nieużywany import Ruff F401, complexity=low | zai/glm-5.3 |
| Refaktoryzacja wielu modułów, complexity=high | zai/glm-5.3 |
| Pierwsze zadanie z jawnym request.model=Flash | zai/glm-5.3-flash |

Przekazanie jawnego modelu działa w resolverze; udana inferencja Flash ani
klasyfikacja trudności nie zostały tym testem potwierdzone.

Dashboard nie odpowiadał pod 8768/8770. Uruchomiono lokalny podgląd istniejącego
Koru na `http://127.0.0.1:8770/`, z blokadą zastępowania istniejącego serwera,
bez restartu lane i bez uruchamiania zadań. Test prawdziwej przeglądarki Chromium:

- `?tab=logs`: HTTP 200, SSE connected, 50 wyrenderowanych wpisów;
  przełącznik DEBUG działa, po ponownym połączeniu strumień pozostaje connected.
- `/api/logs?limit=5`: pięć rekordów; pola `timestamp`, `level`, `message`,
  `category`, `event`, `source`. Brak strukturalnych pól model/provider/tokeny.
- `?tab=terminals`: dwie karty 4101 i 4102, obie `down`, zero sesji.
- Zero błędów JavaScript w obu widokach. Nie użyto przycisków uruchamiania
  agentów, odpowiedzi na uprawnienia ani modyfikacji konfiguracji.
- Testy `test_dashboard_logs.py`, `test_tillm_registry_contract.py` i
  `test_shell_drive_finalize.py`: **63 passed**, governance: zero błędów.

Widok Logs działa jako strumień aktywności; nie stanowi historii wywołań modeli.
W bazie opencode istnieją historyczne wiadomości Koru z DeepSeek V4 Pro
(2026-09-17), GLM-5.3 przez Z.ai i OpenRouter oraz GLM-4.5-Flash (2026-09-16).
GLM-4.5-Flash nie jest GLM-5.3-Flash. Pojedynczy zapis modelu nie dowodzi
ukończenia zadania; bez korelacji ticket/session nie można wyliczyć skuteczności.

Koru korzysta również z SubLLM, lecz headless opencode przez Tillm jest odrębną
ścieżką. W SubLLM `069dd19f559ef5d669eda4629ccb36d4b40b7f1d` trasy
`koru-agent/{queue-executor,planning-assistant,reflection}` preferują GLM-5.3;
OpenRouter z domyślnym Flash jest późniejszym fallbackiem. To nie wybór według
prostoty. `CompletionAttempt` zachowuje model/provider/wynik/czas próby,
`poa.EventStore` jest pamięciowy, a provider-health agreguje stan dostawcy.
Żaden z tych elementów nie jest centralną trwałą historią wszystkich wywołań Koru.

Zgłoszenie SubLLM **STARTER-018** dotyczące panelu historii pozostaje `open`;
w obserwacji nie było otwartego PR ani checkoutu implementacji tego panelu.
To potwierdzone planowanie, nie dowód rozpoczętej realizacji. Dopisano wymaganie
pokrycia ścieżki CLI i korelacji z ticketem. Koru **STARTER-734** rejestruje
brak historii modeli w UI oraz zauważoną potrzebę zastąpienia `eval` w parserze
logów dekodowaniem, które nie wykonuje kodu. W tym audycie parsera nie zmieniono.

<!-- docs:section hypotheses -->
## Hipotezy

Flash może obniżyć koszt małych zmian wymagających modelu. Jakość,
liczba ponownych prób, zużycie tokenów i dostępność na tym koncie są niezmierzone.
Mechaniczne poprawki obsługiwane przez Ruff mogą nie wymagać LLM w ogóle.

<!-- docs:section limitations -->
## Ograniczenia

Brak powiązania każdego historycznego issue z konkretną sesją i fakturą.
Brak potwierdzenia, że wskazane przez użytkownika zgłoszenia z innych repozytoriów
pochodzą z Ruffa. Badanie jednej lokalnej bazy nie wyklucza wykonania Flash
w innym kliencie lub na innym komputerze. Źródłowy routing nie został zmieniony.

<!-- docs:section recommendations -->
## Zalecany pilotaż

1. Dla świeżych, zweryfikowanych diagnostyk Ruffa najpierw użyć jego bezpiecznych
   poprawek w izolowanym tickecie, z jawnym `--no-unsafe-fixes`, przeglądem diffu
   i wymaganymi testami. Sprawdzić również konfigurację klasyfikacji fixów:
   [Ruff fix safety](https://docs.astral.sh/ruff/linter/#fix-safety).
2. Do Flash kwalifikować tylko ograniczony zakres potwierdzony strukturą zadania,
   np. jeden plik, brak zmian API, zależności i uprawnień, istniejący test odbioru.
   Etykieta `ruff`, priorytet lub krótki tytuł nie wystarczają.
3. Najpierw zebrać wyniki małej próbki: wybrany i faktyczny model, powód wyboru,
   tokeny, czas, liczba prób, testy i koszt ukończonej zmiany. Jawne piny operatora
   muszą mieć określoną precedencję; nie zastępować globalnie modelu wszystkich zadań.
4. Po niepowodzeniu dopuścić jedną kontrolowaną eskalację w tym samym tickecie,
   bez zmiany uprawnień i bez tworzenia kolejnych zgłoszeń. Większe refaktoryzacje
   oceniać oddzielnie. Zachować niezależne bramy publikacji.

Realizacja polityki i włączenie jej w runtime pozostają osobną fazą STARTER-732.
Wynik tego audytu nie oznacza wdrożenia Flash.
