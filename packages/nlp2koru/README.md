# nlp2koru

NL → DSL (bez side-effect) → opcjonalnie `dsl2koru.dispatch()`.

```bash
nlp2koru to-dsl "repair history"
nlp2koru apply "validate lane auto default"
nlp2koru workflow "run tests"   # → nlpshim (osobny bridge)
```
