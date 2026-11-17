---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "composio-integration-role",
  "kind": "information",
  "version": 1,
  "title": "Rola Koru w lokalnym stosie integracji agentowych",
  "status": "proposed",
  "scope": "repository",
  "owner": "semcod/koru",
  "created": "2026-11-17",
  "updated": "2026-11-17",
  "review_after": "2026-12-01",
  "source_revision": "80acb166e1425c80a35c2684835ee8eb05b0005c",
  "affected_repositories": ["semcod/koru"],
  "evidence": ["https://github.com/semcod/koru/blob/80acb166e1425c80a35c2684835ee8eb05b0005c/README.md", "https://docs.composio.dev/docs/toolkits"]
}
---

# Rola Koru w lokalnym stosie integracji agentowych

<!-- docs:section purpose -->
## Purpose

Koru prowadzi pracę nad projektami: wykrywa zadanie, planuje, wykonuje, weryfikuje i obsługuje naprawę. Jest konsumentem warstwy narzędzi. Nie należy przedstawiać samego Koru jako gotowego odpowiednika Composio.

<!-- docs:section scope -->
## Scope

Ten dokument opisuje odpowiedzialność Koru. Porównanie całego ekosystemu ma jednego właściciela: `subactor/docs`, dokument `architecture/analysis/composio-local-alternatives.md`, przygotowany w ticket-245 dla Planfile PLF-27193. [Raport główny przy konkretnym commicie](https://github.com/subactor/docs/blob/b6e79536dbf916c3ebd0c8313831b329a01bdcfd/architecture/analysis/composio-local-alternatives.md) jest zależnością dokumentacyjną. Został wypchnięty i jest przeglądany w [Subactor #249](https://github.com/subactor/docs/pull/249); pozostaje draftem do naprawy indeksu i adopcji checkera dokumentacji. Nie oznacza to wdrożenia integracji Koru.

<!-- docs:section evidence -->
## Evidence

Obecny [README](../../README.md) opisuje cykl detect → plan → execute → verify → heal i pracę z Planfile. W integracji z narzędziami obowiązuje następujący podział odpowiedzialności:

| Obszar | Odpowiedzialność Koru |
| --- | --- |
| Cel i ciągłość | Zachować identyfikator zadania, kryteria ukończenia, checkpoint i następny krok |
| Wybór operacji | Korzystać z rzeczywiście dostępnego kontraktu/schematu, wskazanej wersji i zakresu |
| Konto | Przechowywać bezpieczną referencję i stan połączenia; dostęp realizuje dopuszczony adapter |
| Efekty | Respektować scope, właściciela, lease i grant wykonawcy; stan kolejki nie przyznaje uprawnień |
| Weryfikacja | Sprawdzić oczekiwany wynik zadania; kod wyjścia pojedynczego narzędzia nie zamyka całego celu |
| Publikacja | Odróżnić lokalne wykonanie, commit, PR, merge i wdrożenie |

To granice integracji i kryteria kwalifikacji, nie deklaracja, że każdy punkt jest obecnie połączony z urirun w jednym przepływie.

<!-- docs:section content -->
## Content

Dla pilota GitHub zadanie powinno określać repozytorium, numer PR i wynik odczytu, który ma zostać zweryfikowany. Koru może zachować takie zadanie i jego zależności. Adapter musi udostępnić faktyczny kontrakt odczytu PR. Nie wolno konstruować nieistniejącego URI na podstawie nazwy konektora.

Stan brakującego konta lub grantu powinien pozostawić zadanie z konkretną zależnością i możliwością wznowienia. Istniejące uwierzytelnienie `gh` jest osobną ścieżką dostępu od zarządzanego OAuth użytkownika. Zakończenie odczytu przez CLI nie potwierdza działania całego połączenia Koru/urirun.

W implementacji wykorzystać istniejący Planfile i runtime urirun. Nie dublować katalogu konektorów, przechowywania tokenów ani obsługi callback OAuth w Koru.

<!-- docs:section limitations -->
## Limitations

Audyt 2026-11-17 jest dokumentacyjny. Nie uruchomiono tu kolejki Koru ani zadań modyfikujących repozytoria. W źródle konektora GitHub istnieje 17 operacji, lecz sprawdzony zestaw nie zawiera dedykowanego odczytu PR. Publiczny katalog if-uri pokazuje tylko trzy starsze trasy tego konektora; jego wpis nie jest pełną listą aktualnych możliwości.

Nie mierzymy przewagi Koru nad Composio. Koru rozwiązuje inny problem: ciągłość pracy projektowej. Brak onboardingu lub narzędzia powinien być zadaniem właściciela odpowiedniej warstwy, a nie powodem do pominięcia kontroli przez orkiestrator.

<!-- docs:section next_actions -->
## Next actions

- [Koru README przy audytowanym SHA](https://github.com/semcod/koru/blob/80acb166e1425c80a35c2684835ee8eb05b0005c/README.md).
- [Kontrakty konektora GitHub](https://github.com/urirun-connectors/urirun-connector-github/blob/a660680f75d41acccc7d9a932ea46e0b335249d0/urirun_connector_github/contracts.json).
- [Composio Toolkits](https://docs.composio.dev/docs/toolkits): sesja rozdziela odkrywanie narzędzi, połączenie konta i wykonanie.

Kryterium następnego pilota: jedno trwałe zadanie Koru → dostępna akcja ze schematem → wskazane konto → autoryzowany odczyt → weryfikacja wyniku i checkpoint; dodatkowo odmowa, wygaśnięcie i wznowienie bez powtórzenia efektu.
