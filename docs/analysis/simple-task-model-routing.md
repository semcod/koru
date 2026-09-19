---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "simple-task-model-routing",
  "kind": "analysis",
  "version": 3,
  "title": "Koru: model dla prostych zadan i pilotaz Flash",
  "status": "proposed",
  "owner": "semcod/koru",
  "scope": "repository",
  "created": "2026-09-19",
  "updated": "2026-09-19",
  "review_after": "2026-09-26",
  "source_revision": "9ce405d00bb52e009774d88ead6993febc45858e",
  "affected_repositories": [
    "semcod/koru"
  ],
  "evidence": [
    "https://github.com/semcod/koru/blob/684463445c60d5701b67de47a942924d1b114f67/src/koru/autonomy/cycle/cycle_drive_retry.py",
    "https://github.com/semcod/koru/issues/353",
    "https://docs.z.ai/guides/overview/pricing",
    "https://docs.astral.sh/ruff/linter/#fix-safety",
    "https://github.com/semcod/koru/pull/361",
    "https://github.com/semcod/koru/pull/362",
    "https://github.com/subactor/subllm/pull/83"
  ]
}
---

# Koru: wybór modelu dla prostych zadań

## Aktualizacja v3: poprawka i rzeczywisty pilotaż, 2026-09-19

Poniższe starsze ustalenia opisują rewizję sprzed poprawki. Aktualny kod routingu
jest scalony w PR361 (merge `9ce405d00bb52e009774d88ead6993febc45858e`).
Widok Models w PR362 jest przygotowany i przetestowany, ale w chwili tej obserwacji
nie ma jeszcze potwierdzenia jego scalenia ani wdrożenia do aktywnej usługi.
Head interfejsu: `1380262f3e05f0df334215a65d58a0a144f553b5`.
OneDev zweryfikował ten head z bazą `9ce405d0`: 133 testy i 4 subtesty oraz
przypięty checker dokumentacji przeszły; pozostałe wymagane statusy są zielone.
Próba niezależnego Validatora o 19:54 UTC zakończyła się
`LOCAL_DIRECT_PR_APP_LOOKUP_FAILED` (HTTP403, limit API konta5669657),
przed oceną zmian. To blokada publikacji, nie odrzucenie kodu przez recenzenta.

### Zachowanie i konfiguracja

`KORU_TILLM_SIMPLE_MODEL=zai/glm-5.3-flash` włącza wybór dla OpenCode.
`KORU_TILLM_MODEL` nadal określa zwykły model; jawny wybór CLI lub ticketu ma
pierwszeństwo. To konfiguracja operatora, nie nowy katalog dostawców.
Polityka HTTP pozostaje własnością SubLLM.

W aktualnym Planfile używać zachowywanego rozszerzenia `source.context`:

```json
{
  "files": ["src/example.py"],
  "source": {
    "tool": "ruff",
    "context": {
      "model_routing": {"llm_task_kind": "lint_fix", "ruff_codes": ["F401"]}
    }
  }
}
```

Wymagane są jeden względny plik Python w src/tests/test i najwyżej 10 reguł
z listy F401, F541, I001, UP017, UP035. Oznaczenia refaktoryzacji, code2llm,
bezpieczeństwa, governance i zależności wykluczają obniżenie modelu.
Nieznany zakres zachowuje zwykły model. Tytuł „proste” ani sam tag Ruff nie
wystarczają. Istniejące zgłoszenia nie zostały masowo przeklasyfikowane.
Rzeczywiste zgłoszenie nxdo PLF-070 obejmowało 96 ustaleń w wielu plikach;
nie nadaje się do automatycznego uznania za mały lint.

Pierwsza wersja rozszerzenia `inputs` nie była zgodna z bieżącym Planfile,
który usuwa nieznane pola TicketInputs. Poprawka używa `source.context.model_routing`;
przejście przez rzeczywisty model Planfile zachowało metadane i wybór Flash.
Bezpośredni starszy caller może nadal przekazać równoważne pola inputs.

### Zaobserwowane wykonanie i testy

Izolowany, rzeczywisty OpenCode dostał model wybrany przez funkcję polityki Koru,
bez przypięcia modelu w samym zadaniu. Żądanie wymagało jedynie odpowiedzi OK;
uprawnienia do narzędzi były wyłączone. Odczyt dokładnego identyfikatora sesji
`ses_f44d3b408ffeM9lfggGmR9WB3P` potwierdził wiadomość asystenta
`zai/glm-5.3-flash`, status completed, 6148 tokenów wejścia i 4 wyjścia,
2026-09-19 19:37:20 UTC. To dowód inferencji, nie ukończenia poprawki kodu
ani pomiar oszczędności całej kolejki. Nie publikujemy promptów ani odpowiedzi.

Bezpieczny digest prywatnego receipt SHA-256: `759310bc3075c7debe6ded416b67064d67e81ca52016d86364445cc55a6138d2`.

- Routing: 215 testów i 11 subtestów po zmianie bazy; po poprawce zgodności
  Planfile dodatkowo 144 testy i 4 subtesty obejmujące zmienione ścieżki.
- Interfejs i parser: 98 testów; Ruff i governance bez błędów.
- Chromium: rzeczywista sesja Flash, filtr modelu, pusty wynik i stan HTTP503,
  bez błędów JavaScript. Podgląd lokalny: http://127.0.0.1:8771/?tab=models.
- Parser logów używa `ast.literal_eval`; test z próbą wykonania kodu nie tworzy pliku.

### Zakres danych i wdrożenia

Models oddziela żądany model z `.planfile/.koru/model-routing.jsonl` od odczytów
rzeczywistych wiadomości OpenCode. Pokazuje czas, dostawcę, model, status i tokeny;
brak liczników pozostaje unknown. Nie zgaduje związku sesji z ticketem i nie
prezentuje kosztów jako rozliczenia. OpenCode obejmuje wybrany projekt oraz jego
.worktrees. SubLLM obejmuje aplikację koru-agent we wszystkich projektach;
CLI OpenCode nie przechodzi przez SubLLM.

Konsument wykrywa już scalone API SubLLM z PR83 (main `a271eef`);
w chwili kontroli dziennik zwrócił empty. Jest to kod dostarczony, lecz nie dowód
zarejestrowania płatnego żądania Koru przez SubLLM. Widok pokazuje tę różnicę.

Aktywna koru-lane-koru.service nadal miała PID2882503 i działający proces OpenCode.
Nie restartowano jej w trakcie zadania. Globalny wybór Flash w tej usłudze nie jest
jeszcze potwierdzony; potrzebne są bezpieczna granica między zadaniami, wdrożenie
zweryfikowanego kodu, włączenie konfiguracji oraz odczyt nowej sesji.

### Luka w dowodach publikacji

PR361 scaliła niezależna aplikacja ifuri-validator-agent. Git potwierdza obecność
obu commitów, w tym poprawki `60510a80`. Widoczna aprobata dotyczyła `acf71f47`
i po dopchnięciu poprawki miała stan DISMISSED. Odczyt statusów nowego commita
nie zawierał onedev/local-verify. Nie traktujemy wcześniejszej aprobaty jako
walidacji nowego HEAD. To wymaga sprawdzenia wyścigu aktualizacji gałęzi z merge
w chronionym adapterze; sama obserwacja nie rozstrzyga mechanizmu błędu.
Trwały wniosek Planfile: STARTER-735, właściciel runtime subactor/validator-agent.

## Historyczna obserwacja sprzed wdrożenia routingu


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
