# nlp2koru

NL → DSL (bez side-effect) → opcjonalnie `dsl2koru.dispatch()`.

```bash
python -m pip install "nlp2koru[llm]"
```

```bash
nlp2koru to-dsl "repair history"
nlp2koru apply "validate lane auto default"
nlp2koru workflow "run tests"   # → nlpshim (osobny bridge)
```

Opcja `--llm` używa centralnej trasy SubLLM
`koru-agent/nl-to-koru-dsl`. Wybór modelu, dostawcy i failover należy do
centralnej polityki, a nie do adaptera.

Przestarzała opcja `--model` pozostaje akceptowana dla kompatybilności, lecz
efektywny model wybiera polityka centralnej trasy.
