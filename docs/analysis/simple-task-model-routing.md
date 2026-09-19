---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "simple-task-model-routing",
  "kind": "analysis",
  "version": 1,
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
