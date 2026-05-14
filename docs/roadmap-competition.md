# Roadmap koru vs ekosystem konkurencji

## Cel dokumentu

Ten dokument zestawia **koru** z wybranymi produktami i liniami produktowymi:
[Grit](https://docs.grit.io/) (migracje i „checks” na repozytorium),
[OpenRewrite](https://docs.openrewrite.org/) wraz z ekosystemem
[Moderne](https://www.moderne.io/blog) (przepisy, skale, DevCenter),
[Gitar](https://gitar.ai/) (boty PR / automatyzacja na GitHubie),
oraz [Git AutoReview](https://gitautoreview.com/) i podobne narzędzia
review w IDE. Chodzi o **jasny kierunek rozwoju koru**: silny planfile +
bramki jakości lokalnie i w CI, opcjonalna warstwa „produktowa”
(hosted checks, App, cienki DevCenter) bez porzucania filozofii
dwóch trybów (IDE-native vs OpenRouter).

**Uwaga techniczna:** `koru serve` to lokalny serwer oparty o
`http.server` ze standardowej biblioteki Pythona (brak FastAPI w tej
ścieżce). HTTP API typu FastAPI/Alertmanager znajduje się m.in. w
`services/healing-webhook/`. **Observability** (Prometheus, Alertmanager,
blackbox itd.) to **osobny stack** referencyjny, nie część samego CLI
koru. **DevCenter** w sensie Moderne traktujemy jako **propozycję cienkiej
warstwy** nad planfile i metrykami, a nie duplikat platformy Moderne.

## Porównanie obszarów

| Obszar | Stan w koru | Konkurencja | Co dodać |
|--------|---------------|-------------|----------|
| Integracja GitHub / GitLab | CLI koru + Taskfile; `healing-webhook` + Alertmanager; brak oficjalnej GitHub App | Grit Checks, boty PR (np. Gitar): App, workflowy, komentarze, status checks | Oficjalna GitHub App (i analog na [GitLab](https://docs.gitlab.com/ee/integration/)), workflow szablony, komentarze PR + [Checks API](https://docs.github.com/en/rest/checks) |
| Szablony CI | Taskfile i szablony wymagają znajomości konwencji semcod | Grit hosted checks, gotowe integracje | Pakiet **koru-checks**, „thin” workflow (minimalny YAML + dokumentacja) |
| Dashboard / widoczność | `koru serve` = `http.server` (stdlib) + osobny stack observability | Moderne DevCenter | Cienki **DevCenter**: widok nad planfile + metryki z istniejącego stacku, bez monolitu |
| IDE | Autopilot (np. VS Code, socket) | Git AutoReview, rozszerzenia review | Uogólniony protokół, więcej IDE na tym samym kontrakcie |
| Trackery zgłoszeń | planfile wewnętrzny | Linear agents, integracje SaaS | Connectory (API / webhook) do zewnętrznych trackerów |
| Polityki vs przepisy | YAML: polityka / pipeline | `grit.yaml`, przepisy OpenRewrite | **Katalog przepisów koru** (wersjonowane „recipes”) spójne z polityką |
| Bramki bezpieczeństwa | regix, redup, vallm, sumr itd. | kampanie bezpieczeństwa w narzędziach hosted | Spójny **security pipeline** w planfile + CI (bez wyłączania lokalnych bramek) |
| Wielojęzyczność | roadmapa mocno pod Python | szeroka oferta OpenRewrite | Roadmapa języków i adapterów poza Pythonem |
| LLM BYOM | historycznie mocny nacisk na OpenRouter | wielu dostawców, UI wyboru | `llm.yaml`, `doctor-llm`, dokumentacja multi-provider |
| Onboarding | `koru init` zaawansowany | u konkurentów często „5 minut” | `koru init --quickstart` + ścieżka „pierwszy PR w 15 minut” |

## Backlog epików (skrót)

### Epic 1 — GitHub / GitLab App i eventy (P1)

- Jako maintainer chcę, żeby push i PR uruchamiały ten sam zestaw bramek co lokalnie (`task quality:regix:local`), aby nie było dryfu środowiskowego.
- Jako zespół chcę podpisanego webhooka i audytowalnego logu jobów (Docker `koru` lub hosted worker).
- Jako reviewer chcę widzieć wynik jako **Check Run** na PR z linkiem do szczegółów skanu.

### Epic 2 — koru-checks i thin CI (P1)

#### Status / wdrożenie (fragment)

- Cienki workflow GitHub Actions + instrukcja kopiowania: **[`docs/ci-github.md`](./ci-github.md)** (workflow źródłowy: `.github/workflows/koru-ci.yml`; pełna macierz na `main`: `.github/workflows/ci.yml`).
- Analog na GitLabie: **[`docs/ci-gitlab.md`](./ci-gitlab.md)** (przykład: [`examples/ci/gitlab-ci.example.yml`](../examples/ci/gitlab-ci.example.yml) — ten sam smoke co `koru-ci.yml`).
- **cache pip w CI (GitHub + GitLab)**.

- Jako adopters chcę skopiować jeden plik workflow i mieć działające gates bez czytania całego monorepo semcod.
- Jako release manager chcę wersjonowany obraz / akcję marketplace z pinowaną wersją koru.
- Jako dev chcę cache zależności i szybki fail na pierwszej bramce.

### Epic 3 — Observability + cienki DevCenter (P2)

- Jako SRE chcę, żeby dashboard koru (`koru serve`) linkował do istniejących dashboardów Prometheus/Grafana zamiast je duplikować.
- Jako PM chcę jedną stronę „stan sprintu” z planfile + alertami otwartymi w jednym widoku.
- Jako agent LLM chcę stabilny JSON brief (jak dziś `/api/context`) bez wymogu FastAPI po stronie `serve`.

### Epic 4 — Protokół IDE / autopilot (P2)

- Jako użytkownik Cursor chcę ten sam kontrakt zdarzeń co w VS Code.
- Jako twórca pluginu chcę dokumentowany schemat wiadomości (NDJSON / socket).
- Jako enterprise chcę opcjonalne TLS / auth dla socketa lokalnego.

### Epic 5 — Connectory do trackerów (P3)

- Jako zespół na Linearze chcę dwukierunkową synchronizację etykiet priorytetu z planfile.
- Jako koru chcę webhook „ticket zamknięty” → aktualizacja stanu w zewnętrznym trackerze.
- Jako audytor chcę mapowanie `PLF-XXX` ↔ ID obce bez utraty źródła prawdy w planfile.

### Epic 6 — Katalog przepisów (recipes) i polityka (P1)

- Jako architekt chcę udostępnić zestaw przepisów (np. migracje importów) wersjonowanych razem z polityką YAML.
- Jako dev chcę `koru recipe list / apply` z suchym runem przed zapisem.
- Jako org chcę politykę „dozwolone tylko przepisy z katalogu X”.

### Epic 7 — Security pipeline (P1)

- Jako security chcę, żeby regix / redup / sumr były obowiązkowe na gałęzi chronionej tak samo w CI jak u developera.
- Jako compliance chcę SBOM lub raport podatności jako artefakt check run.
- Jako dev chcę jednoznaczny komunikat „która bramka zablokowała merge”.

### Epic 8 — Multi-lang, BYOM, quickstart (P2–P3)

- Stub dokumentacji przyszłego **katalogu przepisów (recipes)** PL: [`docs/recipes/README.md`](./recipes/README.md).
- Jako org z Javą chcę roadmapę i pierwszy oficjalny adapter poza Pythonem (P3 dla języka, P2 dla dokumentacji ścieżki).
- Jako użytkownik chcę `llm.yaml` z wyborem dostawcy i `doctor-llm` wykrywającym brak kluczy (P2).
- Jako nowy użytkownik chcę `koru init --quickstart` z minimalnym `.koru` i przykładowym ticketem (P2).

## Architektura GitHub App (szkic)

1. **Webhook** [`pull_request`](https://docs.github.com/en/webhooks/webhook-events-and-payloads) / [`push`](https://docs.github.com/en/webhooks/webhook-events-and-payloads) (oraz ewentualnie inne zdarzenia) trafia do endpointu aplikacji.
2. **Weryfikacja podpisu** żądania (secret aplikacji / delivery headers zgodnie z dokumentacją GitHub Apps).
3. **Job** w izolacji: kontener Docker z narzędziami `koru` albo **hosted worker** (queue, retry, limity czasu).
4. W jobie: **`koru scan`** (lub równoważna komenda bramek) + istniejące gates (regix, testy, itd.).
5. Wynik zgłaszany przez **[GitHub Check Runs API](https://docs.github.com/en/rest/checks/runs)** (`queued` → `in_progress` → `completed` z `conclusion`: `success` / `failure` / `neutral`).
6. Opcjonalnie: **komentarz na PR** (skrót + linki) oraz **utworzenie ticketu planfile** (`planfile ticket create` lub HTTP API webhooka / healing), gdy polityka wymaga pracy ludzkiej lub śledzenia w backlogu.

**Command dispatch:** zdarzenie [`issue_comment`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issue_comment) (lub dedykowany slash command) może mapować komendę `/koru scan` na ten sam pipeline co webhook PR — z tym samym modelem uprawnień i deduplikacją buildów.

Analogiczny szkic dla **GitLab** to [Merge Request events](https://docs.gitlab.com/ee/user/project/integrations/webhook_events.html) + [External status checks](https://docs.gitlab.com/ee/user/project/merge_requests/status_checks.html) / pipelines zamiast Check Runs.

## Linki zewnętrzne (skrót)

- [Grit — dokumentacja](https://docs.grit.io/)
- [OpenRewrite](https://docs.openrewrite.org/)
- [Moderne — blog](https://www.moderne.io/blog)
- [Gitar](https://gitar.ai/)
- [Git AutoReview](https://gitautoreview.com/)
- [GitHub — Apps](https://docs.github.com/en/apps)
- [GitLab — integracje i webhooki](https://docs.gitlab.com/ee/integration/)
