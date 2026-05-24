# Strategia discovery: pusta kolejka -> code2llm -> planfile tickets

Ten dokument opisuje aktualna strategie Koru dla momentu, w ktorym kolejka
`planfile` jest pusta. Celem nie jest dalsze wysylanie ogolnego promptu
`continue with the next ticket` do IDE, tylko powrot z trybu lokalnej
implementacji do szerokiej analizy calego projektu i wygenerowanie nowych,
konkretnych ticketow.

## Model pracy

Koru pracuje w dwoch rytmach:

1. **Szczegol / execution mode** - gdy istnieja tickety, Koru wybiera nastepny
   ticket z `planfile`, buduje prompt dla IDE LLM, pilnuje statusu
   `waiting_input` i oczekuje, ze IDE LLM zakonczy prace jawna komenda
   `planfile`.
2. **Ogol / discovery mode** - gdy kolejka jest pusta, Koru wraca do obrazu
   calego repozytorium, uruchamia skan semcod/code2llm i zamienia wyniki na
   nowe tickety. Po utworzeniu ticketow broad discovery konczy sie, a petla
   wraca do trybu szczegolu.

Ta strategia zapobiega dwom problemom: bezproduktywnemu zapetlaniu pustego
promptu w IDE oraz zbyt szerokim edycjom bez jednoznacznego backlogu.

## Warunki uruchomienia

Automatyczne discovery po pustej kolejce jest aktywne, gdy:

- `koru auto` albo `koru autonomous up` uruchamia petle autonomiczna;
- kolejka `planfile` po `koru --queue --loop` zwraca `idle`;
- wlaczony jest skan po pustej kolejce: `koru auto` robi to domyslnie,
  `koru autonomous up` potrzebuje `--scan-after-idle-queue`;
- wlaczone sa artefakty semcod: `--semcod-artifacts`;
- `code2llm` jest dostepne w `PATH`;
- rate-limit `--scan-after-idle-min-interval` pozwala na kolejny skan.

W `koru auto` mozna to wylaczyc przez `--no-scan-after-idle-queue`. W trybie
adaptacyjnym `KORU_AUTO_PIPELINE=1` moze wlaczyc te elementy dla etapow jakosci
i architektury. Recznie mozna uruchomic:

```bash
koru autonomous up \
  --ticket-sources queue \
  --scan-after-idle-queue \
  --scan-after-idle-min-interval 60 \
  --semcod-artifacts
```

## Przebieg cyklu

1. Koru uruchamia normalny intake scan:

   ```bash
   koru scan --apply --semcod-artifacts
   ```

2. Jezeli ten skan utworzy tickety, Koru nie uruchamia broad discovery.
   Kolejny cykl bedzie juz pracowal na konkretnych ticketach.

3. Jezeli intake scan nie utworzy zadnego ticketu, Koru uruchamia lokalnie
   `code2llm`:

   ```bash
   code2llm "$PROJECT" \
     -f all \
     -o "$PROJECT/project" \
     --no-chunk \
     --exclude '*.md' \
     --planfile-apply \
     --planfile-source koru-project-discovery \
     --planfile-sprint current \
     --planfile-project "$PROJECT" \
     --planfile-limit 20
   ```

4. `code2llm` odswieza artefakty w `project/`, w tym:

   - `project/analysis.toon.yaml` - syntetyczna analiza modulow, warstw,
     zlozonosci i hotspotow;
   - `project/planfile-tickets.yaml` - tickety wygenerowane z analizy,
     z listami `applied` i `skipped`;
   - pozostale formaty wynikajace z `-f all`.

5. Dzieki `--planfile-apply` tickety sa tworzone przez CLI `planfile`, a nie
   przez reczna edycje YAML. Zrodlo ticketow jest oznaczane jako
   `koru-project-discovery`.

6. Koru zapisuje wynik jako zdarzenie `Code2llmDiscoveryCompleted` oraz
   telemetry:

   - `code2llm_discovery_run`;
   - `code2llm_discovery_applied`;
   - `code2llm_discovery_skipped`;
   - ewentualny blad albo powod pominiecia.

## Priorytety ticketow

Discovery powinno preferowac prace o wysokim sygnale:

- failing gates i regresje;
- god modules / duze gorace moduly;
- wysoka zlozonosc cyklomatyczna;
- duplikacja kodu;
- brakujace lub kruche testy;
- granice architektoniczne, ktore blokuja kolejne refaktory.

Koru nie powinien wykonywac szerokich edycji bez ticketu. Discovery ma
zamienic obraz calego projektu na kolejke mniejszych prac, a nie zastapic
normalny cykl ticket-driven development.

## Kontrakt z IDE LLM

Kazdy prompt wysylany do IDE LLM dla ticketu powinien zawierac jawny handoff
statusu `planfile`:

```bash
planfile ticket done <ID>
planfile ticket input <ID> --prompt "<exact input needed>" --note "<what you verified>"
planfile ticket fail <ID> --error "<short failure reason>"
```

Znaczenie:

- po poprawnym zakonczeniu pracy i lokalnych bramkach IDE LLM uruchamia
  `planfile ticket done <ID>`;
- gdy brakuje danych od operatora, IDE LLM uruchamia `planfile ticket input`
  z dokladnym pytaniem i notatka diagnostyczna;
- gdy proba implementacji realnie sie nie udala, IDE LLM uruchamia
  `planfile ticket fail`;
- zakonczona praca nie powinna zostawac w `waiting_input`.

To daje wspolny jezyk miedzy Koru, IDE LLM i operatorem: status ticketu jest
zrodlem prawdy, a log czatu IDE jest tylko kanalem wykonawczym.

## Rate limiting i cache

Discovery jest ograniczone kosztowo i czasowo:

- `--scan-after-idle-min-interval` ogranicza czestotliwosc skanow po pustej
  kolejce;
- swieze `project/analysis.toon.yaml` mlodsze niz 60 minut powstrzymuje pelny
  rerun `code2llm`;
- `--planfile-limit 20` ogranicza liczbe ticketow tworzonych w jednej fali.

Jesli `code2llm` nie jest dostepne albo zakonczy sie bledem, Koru loguje
ustrukturyzowany wynik `skipped` albo `error`. Operator moze wtedy doinstalowac
`code2llm`, uruchomic powyzsza komende recznie albo pozwolic petli wrocic do
normalnej kolejki, jezeli tickety pojawily sie innym kanalem.

## Oczekiwany efekt

Docelowy rytm autonomii wyglada tak:

1. Koru wykonuje tickety jeden po drugim.
2. Po zamknieciu backlogu kolejka staje sie `idle`.
3. Koru skanuje caly projekt przez semcod/code2llm.
4. Wyniki analizy staja sie konkretnymi ticketami w `planfile`.
5. Koru przerywa broad discovery i wraca do wykonywania ticketow.
6. Gdy backlog znowu jest pusty, kolejny cykl discovery moze sie powtorzyc.

