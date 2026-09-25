---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "simple-task-model-routing",
  "kind": "analysis",
  "version": 5,
  "title": "Koru: model dla prostych zadan i pilotaz Flash",
  "status": "proposed",
  "owner": "semcod/koru",
  "scope": "repository",
  "created": "2026-09-19",
  "updated": "2026-09-25",
  "review_after": "2026-10-02",
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
    "https://github.com/subactor/subllm/pull/83",
    "planfile:STARTER-735 (koru-model-routing-audit)",
    "github-ruleset:semcod/koru/22026679 protected exact-head delivery",
    "validator-receipt:digest=7dc49cf3901f0ea6e925070d32f57a2622e69ae0eb7412a5960d879fd2d1aee1 correlation_id=local-semcod-koru-pr-361-ticket-179 registry_digest=4b36dd612732400ebe365e4fb6b1ce3f8e3e947d0cdbe1e9faab0eeec9d91ec0",
    "validator-release:673f4a387f3227a96b7040c76f82fc80e7697b2f-usage-9c40e04f4777 (src/validator_agent/github.py, src/validator_agent/direct_validation.py)"
  ]
}
---
# Koru: wybór modelu dla prostych zadań

## Aktualizacja v5: audyt wyścigu exact-head przy scaleniu PR361 (STARTER-735), 2026-09-20

Rozstrzygnięcie pytania z sekcji „Luka w dowodach publikacji" (v3):
czy przy scaleniu PR361 egzekwowano CAS na dokładnym headzie.

**Wniosek: nie. Operacja scalenia nie była związana z headem po stronie
serwera. Zgodność heada egzekwowano wyłącznie odczytami klienta przed
scaleniem oraz detekcją po fakcie; scalona zawartość nie miała nigdy
obowiązującej aprobaty ani wymaganego statusu `onedev/local-verify`.**

### Fakty

Oś czasu (UTC, 2026-09-19; odczyty GitHub i git read-only 2026-09-20):

| Czas | Zdarzenie |
|---|---|
| 19:38:39 | commit `acf71f47` na gałęzi ticketu (recenzowany zakres `d1a2e231..acf71f47`, 10 plików, +764/−4, `diff_sha256 df02b2a5…`) |
| 19:44:04 | lokalnie utworzony commit `60510a80` (4 pliki, +28/−3; m.in. `src/koru/task_model_policy.py`, `src/koru/queue/ticket.py`) |
| 19:44:19 | aprobara `5257358794` `ifuri-validator-agent[bot]` na `acf71f47` |
| ~19:44:19–39 | konwergencja po aprobacie: 2 stabilne odczyty head=`acf71f47` (interwał 10 s) i zaliczona pre-merge walidacja heada |
| 19:44:40 | push `60510a80` → GitHub zdyskwalifikował aprobate (`dismiss_stale_reviews_on_push`; aktor zdarzenia: pusher) |
| 19:44:46–47 | start check-runów Actions na nowym headzie |
| 19:44:49–50 | REST merge → merge commit `9ce405d0` z drugim rodzicem `60510a80`; stan MERGED |
| 19:44:51 | bot usunął gałąź head (`VALIDATOR_DELETE_BRANCH_AFTER_MERGE`) |
| po 19:44:50 | odczyt po scaleniu: head `60510a80` ≠ oczekiwane `acf71f47` → `STALE_HEAD_CHANGED`; receipt status=`blocked` (`merged=true`) |

Obserwacje GitHub (read-only):

- Review `5257358794`: `state=DISMISSED`, `commit_id=acf71f47`,
  `submitted_at=19:44:19Z`.
- PR361: `MERGED`, `mergedAt=19:44:50Z`, `mergeCommit=9ce405d0`,
  finalny `headRefOid=60510a80`.
- Statusy commitów: `acf71f47` → `onedev/local-verify` success
  (`total_count=1`); `60510a80` → `total_count=0` — zapytanie o statusy
  nowego heada nie zwróciło żadnych; `onedev/local-verify` nigdy nie
  raportował na scalonej rewizji.
- Check-runs na `60510a80`: 7 (Actions: `smoke`, `governance / enforce`,
  `governance / remote lifecycle`, `standard packs / conformance`;
  zielone/skipped, 19:44:46–55) — nie zawierają `onedev/local-verify`.
- Ruleset 22026679 „protected exact-head delivery" (active,
  `refs/heads/main`): wymagane konteksty `onedev/local-verify` i
  `standard packs / conformance` (`strict`), `dismiss_stale_reviews_on_push=true`,
  `required_approving_review_count=0`; `bypass_actors`:
  RepositoryRole(id 5, always) oraz Integration(id 4344831, always).
  Ponieważ `onedev/local-verify` nie istnieje na `60510a80`, scalenie
  przeszło wyłącznie dzięki bypassowi Integracji; liczba wymaganych
  aprobat równa zero oznacza, że dyskwalifikacja sama w sobie niczego
  nie blokowała.

Analiza chronionego adaptera (źródło `subactor/validator-agent` oraz
wdrożone wydanie `673f4a38…`, identyczne w zakresie scalania):

- `_rest_merge_pull_request` (`src/validator_agent/github.py`): `PUT
  /repos/{owner}/{repo}/pulls/{n}/merge` z wyłącznie `merge_method` —
  bez parametru `sha`, więc GitHub scala aktualny head. To ścieżka
  główna; brak CAS po stronie serwera.
- `_graphql_merge_pull_request`: mutacja `mergePullRequest` z
  `expectedHeadOid` (prawdziwy CAS na headzie) — używana wyłącznie jako
  fallback po wąsko rozpoznanej niezgodności polityki HTTP 405 („Merge
  commits are not allowed"). W receipcie PR361 nie ma operacji fallback,
  więc scalono ścieżką REST.
- Zgodność heada sprawdzana jest tylko odczytami klienta: konwergencja
  po aprobacie (minimum 2 stabilne odczyty), `_validate_pull_request`
  przed scaleniem (`direct_validation.py`, błąd `STALE_HEAD_CHANGED`) oraz
  `_validate_merged_pull_request` po scaleniu. Okno wyścigu (TOCTOU)
  między ostatnim odczytem klienta a scaleniem serwera wyniosło około
  9–10 s (push ≈19:44:40, scalenie 19:44:49–50; interwał stabilnych
  odczytów 10 s).

Scalona rewizja `60510a80` nie posiadała więc żadnego z trzech
niezależnych warunków publikacji: (a) obowiązującej aprobaty w GitHub,
(b) wymaganego statusu `onedev/local-verify`, (c) pokrycia recenzji —
`diff_sha256` recenzji LLM i ocena semantyczna obejmują wyłącznie
`d1a2e231..acf71f47`. Zielone checki z `acf71f47` oraz zielone runy
Actions na `60510a80` nie są autoryzacją (zgodnie z warunkami zadania
nie wnioskowano autoryzacji ze starszych zielonych checków).

Chronione receipty zachowane bez zmian: receipt direct-pr
`semcod/koru#361` (digest katalogu `7dc49cf3901f0ea6e925070d32f57a2622e69ae0eb7412a5960d879fd2d1aee1`,
`correlation_id=local-semcod-koru-pr-361-ticket-179`, `registry_digest
4b36dd61…` zgodny z oczekiwanym digestem rejestru). Receipt
`subactor/onedev-agent#361` (ticket-351, 2026-09-15) dotyczy innego
repozytorium i nie jest dowodem w tej sprawie. W ramach audytu nie
wykonano żadnego scalenia, pushu ani bypassu; wszystkie zapytania były
odczytami (limit API konta 5669657 uniemożliwił potwierdzenie
tożsamości Integracji przez `/apps/{slug}`).

### Hipotezy (niepotwierdzone)

- Integration id 4344831 to aplikacja ifuri-validator-agent — bardzo
  prawdopodobne (bot jest autorem merge i jedynym nieadminowym aktorem
  mogącym ominąć wymagane statusy), ale potwierdzenie zablokował limit API.
- Moment pushu wywnioskowano ze zdarzenia dismissal (19:44:40Z) i startu
  check-runów (19:44:46Z); timeline REST nie nosi bezpośredniego
  znacznika czasu pushu.
- Commit `60510a80` powstał lokalnie przed aprobata (author date
  19:44:04Z), a push opóźniono — zgodne z metadanymi, nieobserwowane
  bezpośrednio.

### Zalecenia

1. W `_rest_merge_pull_request` przekazywać `sha=pr.head_sha` (GitHub
   odrzuca scalenie kodem 409 przy przesuniętym headzie) — zastępuje
   odczyt klienta atomowym CAS po stronie serwera. Alternatywnie uczynić
   mutację GraphQL z `expectedHeadOid` ścieżką główną.
2. `STALE_HEAD_CHANGED` wykryty po scaleniu traktować jako incydent
   publikacji wymagający decyzji właściciela runtime (revert lub pełna
   ponowna walidacja exact-head), a nie wyłącznie status `blocked`
   w receipcie.
3. Przeglądnąć `bypass_mode` Integracji w ruleset 22026679 („always" →
   tryb ograniczony) — poza zakresem tego ticketu; zmiana polityki
   wymaga własnej chronionej ścieżki.
4. Nie uznawać `9ce405d0` za zwalidowany exact-head; każde dalsze
   publikacje na tej bazie powinny wiązać się z własną pełną walidacją.
   Poświadczenie potomne (OneDev: 133 testy i 4 subtesty dla PR362 head
   `1380262f` z bazą `9ce405d0`, sekcja v3) to pokrycie testowe
   potomnego heada, nie autoryzacja scalenia `60510a80`.

### Wersjonowanie

Ticket STARTER-735 (utworzony 2026-09-19T19:53:54Z) prosił o raport
„v3"; dokument awansował w międzyczasie do v4 (commit `4baa31ae`), więc
zgodnie z regułą append-only niniejsza aktualizacja jest v5, a sekcje
v1–v4 pozostają bez zmian.



### Granica publikacji

Zakres STARTER-735 był początkowo read-only i nie upoważniał do
bezpośredniego merge ani bypassu. 25 września 2026 r. użytkownik jawnie
zatwierdził wypchnięcie i scalenie zaległych ticketów Koru. Ta późniejsza
autoryzacja obejmuje publikację raportu zwykłą ścieżką chronionego
Validatora; bypass rulesetu nie jest dozwolony.

## Aktualizacja v4: odczyt działającego dziennika SubLLM, 19:57 UTC

API Koru zwróciło teraz SubLLM `status=ready` i pięć zapisów aplikacji
`koru-agent`, funkcja `planning-assistant`, z okresu 19:54:23–19:56:38 UTC.
Trzy mają status success dla `zai/glm-5.3` z licznikami wejście/wyjście
203/400, 202/277 i 179/105. Pozostałe dwa mają status error dla jednego
request_id: `zai/glm-5.3` i `openrouter/z-ai/glm-5.3-flash`, bez liczników.
Widok odróżnia te błędy od udanej wiadomości Flash w pilotażu OpenCode.
To dane producenta SubLLM; nie przypisujemy ich do konkretnego projektu,
ticketu ani do naszej próby OpenCode. Nie diagnozujemy przyczyny błędów z
samych metadanych. Stan empty opisany w v3 jest wcześniejszą obserwacją.

Chromium pokazał `OpenCode: available; SubLLM: ready`, filtr Flash obejmował
zarówno udany zapis OpenCode, jak i błędny zapis SubLLM. Brak błędów JavaScript.
Digest bezpiecznego odczytu SHA-256: `67bc749f64a5b0369aae3d433ce2ffcfc94b343a60d85c88eee3e8b2fe133ad4`.

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
