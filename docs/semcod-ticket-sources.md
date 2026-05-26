# semcod ticket sources

Koru can turn semcod project analysis into `planfile` tickets in two ways:

1. native generators create tickets directly through `planfile`;
2. artifact adapters read reports from other tools and create focused Koru scan tickets.

The default workflow is configured in `koru.yaml` under
`autonomy.strategy.idle_discovery.tools`. `koru auto` applies that strategy:
it executes the current queue first, then broadens to whole-project discovery
when the queue is idle.

## Current matrix

| Tool | Role in autonomy | Ticket source | Koru status |
| --- | --- | --- | --- |
| `code2llm` | whole-project architecture/refactor discovery | native `--planfile-apply` plus `analysis.toon*` adapter | automated |
| `koru scan` | intake from repo signals | native Koru scan tickets | automated |
| `jscpd` | duplicate-code report | `.jscpd/jscpd-report.json` | artifact adapter |
| `redup` | duplicate groups, changed-file duplicate groups | `.redup/check.filtered.json`, `.redup/wup-changed.json` | artifact adapter |
| `testql` | API/scenario regressions | `testql_api_results.json` | artifact adapter |
| `vallm` | syntax/semantic validation | `validation.toon.yaml`, `project/validation.toon.yaml`, `.vallm/report.yaml` | artifact adapter |
| `pyqual` | quality checks | `.pyqual/report.*`, `pyqual-report.*`, `quality-report.yaml` | native CLI has `tickets`; Koru also reads artifacts |
| `prefact` | pre-refactor checks | `.prefact/report.json`, `prefact-report.json` | native autonomous/ticket mode exists; Koru also reads artifacts |
| `regix` | metric/regression gates | `.regix/report.json`, `.regix/gates.json`, `regix-gates.json` | artifact adapter |
| `redsl` | quality gate / improve lane | `.redsl/report.json`, `redsl-report.*`, `redsl-gate.json` | limited native planfile command; Koru reads gate artifacts |
| `wup` | file/service change watcher | watcher state and changed artifacts from other tools | orchestration input, not a direct ticket generator |
| `metrun` | execution intelligence | planned report adapter | local CLI currently needs repair before automation |
| `pfix`, `goal`, `costs` | repair, goal alignment, cost signals | advisory/manual until stable report contracts are defined | advisory |

## Report contract

Tools do not need to know Planfile to participate. The preferred contract is a
stable JSON/YAML report with one of these keys when work is actionable:

- `failed`, `failures`, `failed_checks`, `failed_gates`;
- `errors`, `issues`, `findings`, `violations`, `regressions`;
- `status: failed`.

`koru scan --semcod-artifacts --apply` converts those reports into deduplicated
tickets with labels naming the source tool. Native Planfile generation is still
preferred when a tool already supports it, especially `code2llm`, but adapters
keep the rest of the ecosystem useful without forcing every package to import
Planfile.

For focused work, limit intake to selected files or directories:

```bash
koru scan --semcod-artifacts --path src/koru/scan.py --apply
koru scan --semcod-artifacts --path plugins/koru-autopilot-vscodium --path tests
```

The filter matches the proposed ticket files, title, and description, so it can
work with native Koru signals and semcod artifacts whose reports mention the
affected file path.

## LLM coordination

OpenRouter is the planning assistant when `autonomy.strategy.planning_assistant`
is enabled and `OPENROUTER_API_KEY` is available in the environment or project
`.env`. The IDE LLM remains the executor lane: Koru sends scoped prompts through
the active autopilot plugin/MCP surface and expects the IDE agent to update the
Planfile ticket status.
