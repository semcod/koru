<!-- t2c.code-change-review/v1 -->
# todo2code proposed code changes

This document is a grounded **review brief**, not an auto-applied source patch.
Implement the listed paths in a normal branch, re-run the pipeline, then
`t2c evaluate-code-change`. Acceptance still requires human/CI approval before DONE.

Graph fingerprint: `628e5d353eceb8937cd18a1769e22fc252688f8afb2eabade24e855fc82e2412`

## P1

### Implement Update docs/koru_auto_vs_observe_up.md (`CPLAN-02eb8c55ae535ddb11c9`)

- Plan hash: `02eb8c55ae535ddb11c9ff11eb6572e92e27602c807650bafac344c5ac415d5b`
- Risk: **medium** — Derived from review_required diagnostic DIAG-015c8fb54a512b4d6364.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/koru_auto_vs_observe_up.md Source intent: Update docs/koru_auto_vs_observe_up.md Paths: docs/koru_auto_vs_observe_up.md.
- Changes:
  - `modify` `docs/koru_auto_vs_observe_up.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-015c8fb54a512b4d6364 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/koru_auto_vs_observe_up.md.
- Diagnostics: `DIAG-015c8fb54a512b4d6364`
- Evidence records: `INT-CHANGELOG-bb22854b6b2f7e836137`
- Rollback: Revert the proposed changes to docs/koru_auto_vs_observe_up.md and re-run todo2code diagnostics.

### Implement Update docs/adr/adr-auto-002-autonomous-decision-llm.md (`CPLAN-092c3a519b349d8d0775`)

- Plan hash: `092c3a519b349d8d077588832e176d93ba3b2837f8f98dca7dc5bd7f23606a1f`
- Risk: **medium** — Derived from review_required diagnostic DIAG-031eb428249aa00186e0.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/adr/adr-auto-002-autonomous-decision-llm.md Source intent: Update docs/adr/adr-auto-002-autonomous-decision-llm.md Paths: docs/adr/adr-auto-002-autonomous-decision-llm.md. Tickets: AUTO-002.
- Changes:
  - `modify` `docs/adr/adr-auto-002-autonomous-decision-llm.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-031eb428249aa00186e0 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/adr/adr-auto-002-autonomous-decision-llm.md.
- Diagnostics: `DIAG-031eb428249aa00186e0`
- Evidence records: `INT-CHANGELOG-03604620c9fad82cfe1e`
- Rollback: Revert the proposed changes to docs/adr/adr-auto-002-autonomous-decision-llm.md and re-run todo2code diagnostics.

### Implement Update .planfile/config.yaml (`CPLAN-10acc0ef0166f15ee9ef`)

- Plan hash: `10acc0ef0166f15ee9efeb7daa30670e74761907857587bf9945ea8370bce7a2`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0e285caf252a3ac1675f.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .planfile/config.yaml Source intent: Update .planfile/config.yaml Paths: .planfile/config.yaml.
- Changes:
  - `modify` `.planfile/config.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0e285caf252a3ac1675f (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .planfile/config.yaml.
- Diagnostics: `DIAG-0e285caf252a3ac1675f`
- Evidence records: `INT-CHANGELOG-e5452673cb7f95e89fd6`
- Rollback: Revert the proposed changes to .planfile/config.yaml and re-run todo2code diagnostics.

### Implement Update docs/agent-backends-architecture.md (`CPLAN-113f0ae8c44322b2591e`)

- Plan hash: `113f0ae8c44322b2591e947f5cd1da43f75386a51e1519f46980982fe83b20ce`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0383a1367d489fb1926e.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/agent-backends-architecture.md Source intent: Update docs/agent-backends-architecture.md Paths: docs/agent-backends-architecture.md.
- Changes:
  - `modify` `docs/agent-backends-architecture.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0383a1367d489fb1926e (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/agent-backends-architecture.md.
- Diagnostics: `DIAG-0383a1367d489fb1926e`
- Evidence records: `INT-CHANGELOG-b59fc82afae9e5f6248c`
- Rollback: Revert the proposed changes to docs/agent-backends-architecture.md and re-run todo2code diagnostics.

### Implement Update docs/refactoring/REFACTORING_PLAN.md (`CPLAN-15f3f75b5c634685ac94`)

- Plan hash: `15f3f75b5c634685ac949517c4f65926b63bda239b054e8416ab36a64ec3d418`
- Risk: **medium** — Derived from review_required diagnostic DIAG-07f134838f18a2ef8a21.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/refactoring/REFACTORING_PLAN.md Source intent: Update docs/refactoring/REFACTORING_PLAN.md Paths: docs/refactoring/REFACTORING_PLAN.md. Symbols: REFACTORING_PLAN.
- Changes:
  - `modify` `docs/refactoring/REFACTORING_PLAN.md` symbols: `REFACTORING_PLAN`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Provide AST evidence for symbols: REFACTORING_PLAN.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-07f134838f18a2ef8a21 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/refactoring/REFACTORING_PLAN.md.
- Diagnostics: `DIAG-07f134838f18a2ef8a21`
- Evidence records: `INT-CHANGELOG-e275b80adb92cca340c0`
- Rollback: Revert the proposed changes to docs/refactoring/REFACTORING_PLAN.md and re-run todo2code diagnostics.

### Implement Update docs/autodiagnostics-auto-repair.md (`CPLAN-165c58f33bc21e1510eb`)

- Plan hash: `165c58f33bc21e1510eb2f8f4ab97df796361ed10cf6df562ed43a384cbe01cd`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0347e7e472f32501eda2.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/autodiagnostics-auto-repair.md Source intent: Update docs/autodiagnostics-auto-repair.md Paths: docs/autodiagnostics-auto-repair.md.
- Changes:
  - `modify` `docs/autodiagnostics-auto-repair.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0347e7e472f32501eda2 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/autodiagnostics-auto-repair.md.
- Diagnostics: `DIAG-0347e7e472f32501eda2`
- Evidence records: `INT-CHANGELOG-1d8f4361594d5cf0203c`
- Rollback: Revert the proposed changes to docs/autodiagnostics-auto-repair.md and re-run todo2code diagnostics.

### Implement Update .tmp/code2llm-plugins/compact_flow.png (`CPLAN-2030c24efb3cd6c82efd`)

- Plan hash: `2030c24efb3cd6c82efd02e5862b1038a074f7c06f32d212926edab5d513412e`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0053c09f2dc310e6e821.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .tmp/code2llm-plugins/compact_flow.png Source intent: Update .tmp/code2llm-plugins/compact_flow.png Paths: .tmp/code2llm-plugins/compact_flow.png.
- Changes:
  - `modify` `.tmp/code2llm-plugins/compact_flow.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0053c09f2dc310e6e821 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .tmp/code2llm-plugins/compact_flow.png.
- Diagnostics: `DIAG-0053c09f2dc310e6e821`
- Evidence records: `INT-CHANGELOG-b59182d519790d62c246`
- Rollback: Revert the proposed changes to .tmp/code2llm-plugins/compact_flow.png and re-run todo2code diagnostics.

### Implement Update project/compact_flow.png (`CPLAN-21d776af4d2fdbf0ffe9`)

- Plan hash: `21d776af4d2fdbf0ffe95bdcbb0913d487554a30e53fe2f54dae28bb91556005`
- Risk: **medium** — Derived from review_required diagnostic DIAG-006eff514b700dd9c8b4.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/compact_flow.png Source intent: Update project/compact_flow.png Paths: project/compact_flow.png.
- Changes:
  - `modify` `project/compact_flow.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-006eff514b700dd9c8b4 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/compact_flow.png.
- Diagnostics: `DIAG-006eff514b700dd9c8b4`
- Evidence records: `INT-CHANGELOG-26a2103ca45b1f373f14`
- Rollback: Revert the proposed changes to project/compact_flow.png and re-run todo2code diagnostics.

### Implement Update workflows/on-change-gates.md (`CPLAN-21f3af0c24a5dc92dcaa`)

- Plan hash: `21f3af0c24a5dc92dcaa38adf07569c73e9ddfa667ac707a79d607a59b6f4f3a`
- Risk: **medium** — Derived from review_required diagnostic DIAG-05929ca785067d338471.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update workflows/on-change-gates.md Source intent: Update workflows/on-change-gates.md Paths: workflows/on-change-gates.md.
- Changes:
  - `modify` `workflows/on-change-gates.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-05929ca785067d338471 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: workflows/on-change-gates.md.
- Diagnostics: `DIAG-05929ca785067d338471`
- Evidence records: `INT-CHANGELOG-4927d791312966109259`
- Rollback: Revert the proposed changes to workflows/on-change-gates.md and re-run todo2code diagnostics.

### Implement Update tests/test_autopilot_injector.py (`CPLAN-230518e4323a364a44dc`)

- Plan hash: `230518e4323a364a44dc725f85492b49e1bfa3e7da22affeae860977092b8a5b`
- Risk: **medium** — Derived from review_required diagnostic DIAG-12d94ddebfac9d78ada4.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update tests/test_autopilot_injector.py Source intent: Update tests/test_autopilot_injector.py Paths: tests/test_autopilot_injector.py.
- Changes:
  - `modify` `tests/test_autopilot_injector.py`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-12d94ddebfac9d78ada4 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: tests/test_autopilot_injector.py.
- Diagnostics: `DIAG-12d94ddebfac9d78ada4`
- Evidence records: `INT-CHANGELOG-a204f630e319f04da750`
- Rollback: Revert the proposed changes to tests/test_autopilot_injector.py and re-run todo2code diagnostics.

### Implement Update .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json (`CPLAN-266b582bc86caaf816dc`)

- Plan hash: `266b582bc86caaf816dc5f98034f3230a088cff24629be98da0fb791580cbca1`
- Risk: **medium** — Derived from review_required diagnostic DIAG-136aa32e099a60ac26a6.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json Source intent: Update .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json Paths: .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json.
- Changes:
  - `modify` `.vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-136aa32e099a60ac26a6 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json.
- Diagnostics: `DIAG-136aa32e099a60ac26a6`
- Evidence records: `INT-CHANGELOG-e991c5a3cbc80eacc5f3`
- Rollback: Revert the proposed changes to .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json and re-run todo2code diagnostics.

### Implement Update docs/architecture/volume-reduction-plan.yaml (`CPLAN-282b023a58be298ecae0`)

- Plan hash: `282b023a58be298ecae0cc712303f9f5c3f92235e538d2f61b3b5ccc5a78366f`
- Risk: **medium** — Derived from review_required diagnostic DIAG-07a868405a66fc75d328.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/architecture/volume-reduction-plan.yaml Source intent: Update docs/architecture/volume-reduction-plan.yaml Paths: docs/architecture/volume-reduction-plan.yaml.
- Changes:
  - `modify` `docs/architecture/volume-reduction-plan.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-07a868405a66fc75d328 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/architecture/volume-reduction-plan.yaml.
- Diagnostics: `DIAG-07a868405a66fc75d328`
- Evidence records: `INT-CHANGELOG-45b9f413ab54fe498116`
- Rollback: Revert the proposed changes to docs/architecture/volume-reduction-plan.yaml and re-run todo2code diagnostics.

### Implement Update docs/autopilot-roadmap.md (`CPLAN-2f45d4e17bb0a16dfd21`)

- Plan hash: `2f45d4e17bb0a16dfd21ab3f17e1531d04c7a96921cadaecbbba650f1bce4735`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0aab4096788538c3d79b.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/autopilot-roadmap.md Source intent: Update docs/autopilot-roadmap.md Paths: docs/autopilot-roadmap.md.
- Changes:
  - `modify` `docs/autopilot-roadmap.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0aab4096788538c3d79b (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/autopilot-roadmap.md.
- Diagnostics: `DIAG-0aab4096788538c3d79b`
- Evidence records: `INT-CHANGELOG-e56d2a857470d4e23c62`
- Rollback: Revert the proposed changes to docs/autopilot-roadmap.md and re-run todo2code diagnostics.

### Implement Update project/compact_flow.png (`CPLAN-4070ccf90f0d97607c88`)

- Plan hash: `4070ccf90f0d97607c88cf106688f25686bef0f0eb8ba9106f2baa410c204bdf`
- Risk: **medium** — Derived from review_required diagnostic DIAG-09a0b041d5caea2ab059.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/compact_flow.png Source intent: Update project/compact_flow.png Paths: project/compact_flow.png.
- Changes:
  - `modify` `project/compact_flow.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-09a0b041d5caea2ab059 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/compact_flow.png.
- Diagnostics: `DIAG-09a0b041d5caea2ab059`
- Evidence records: `INT-CHANGELOG-4c105b287b4475462179`
- Rollback: Revert the proposed changes to project/compact_flow.png and re-run todo2code diagnostics.

### Implement Update docs/architecture/volume-reduction-plan.yaml (`CPLAN-5765539165bd294a287d`)

- Plan hash: `5765539165bd294a287d201efb30798dd39dddd6f13c8acf68fbb6e2d52fdd3f`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0b1d0032cc058aacc6b7.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/architecture/volume-reduction-plan.yaml Source intent: Update docs/architecture/volume-reduction-plan.yaml Paths: docs/architecture/volume-reduction-plan.yaml.
- Changes:
  - `modify` `docs/architecture/volume-reduction-plan.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0b1d0032cc058aacc6b7 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/architecture/volume-reduction-plan.yaml.
- Diagnostics: `DIAG-0b1d0032cc058aacc6b7`
- Evidence records: `INT-CHANGELOG-7782b17c9a35a11b520c`
- Rollback: Revert the proposed changes to docs/architecture/volume-reduction-plan.yaml and re-run todo2code diagnostics.

### Implement Update .planfile/config.yaml (`CPLAN-5de68accd5dafb69cbca`)

- Plan hash: `5de68accd5dafb69cbca59fb7a87008d1a6be912d8d5dd963076d3919ce9fcd4`
- Risk: **medium** — Derived from review_required diagnostic DIAG-114b7e7b525dc130d50a.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .planfile/config.yaml Source intent: Update .planfile/config.yaml Paths: .planfile/config.yaml.
- Changes:
  - `modify` `.planfile/config.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-114b7e7b525dc130d50a (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .planfile/config.yaml.
- Diagnostics: `DIAG-114b7e7b525dc130d50a`
- Evidence records: `INT-CHANGELOG-ea5af7c46ceb25c1c602`
- Rollback: Revert the proposed changes to .planfile/config.yaml and re-run todo2code diagnostics.

### Implement Update testql-testing/scenarios/realtime-health.testql.toon.yaml (`CPLAN-604c2e7e08488a2e48b3`)

- Plan hash: `604c2e7e08488a2e48b3ff51301873f593fc82dc74db03d71971611f9510f0cf`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0c2e870747c21f02d0fd.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update testql-testing/scenarios/realtime-health.testql.toon.yaml Source intent: Update testql-testing/scenarios/realtime-health.testql.toon.yaml Paths: testql-testing/scenarios/realtime-health.testql.toon.yaml.
- Changes:
  - `modify` `testql-testing/scenarios/realtime-health.testql.toon.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0c2e870747c21f02d0fd (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: testql-testing/scenarios/realtime-health.testql.toon.yaml.
- Diagnostics: `DIAG-0c2e870747c21f02d0fd`
- Evidence records: `INT-CHANGELOG-960dcb1638305048a01c`
- Rollback: Revert the proposed changes to testql-testing/scenarios/realtime-health.testql.toon.yaml and re-run todo2code diagnostics.

### Implement Update .planfile/config.yaml (`CPLAN-61e06f39a9cd18039b3b`)

- Plan hash: `61e06f39a9cd18039b3b0d2b2333d80a378811cfb4e49c3ca806da026e3a61df`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0538a061dd33742b969b.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .planfile/config.yaml Source intent: Update .planfile/config.yaml Paths: .planfile/config.yaml.
- Changes:
  - `modify` `.planfile/config.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0538a061dd33742b969b (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .planfile/config.yaml.
- Diagnostics: `DIAG-0538a061dd33742b969b`
- Evidence records: `INT-CHANGELOG-31455725de85f5145a52`
- Rollback: Revert the proposed changes to .planfile/config.yaml and re-run todo2code diagnostics.

### Implement **New slash command** `.windsurf/workflows/koru-gate.md` (`/koru-gate`) — read-only manual triad invocation: detect → regix gates → testql smoke → wup status → aggregate decision. Used by the agent before `planfile ticket complete`. (`CPLAN-6f5271911ae0390c0d1c`)

- Plan hash: `6f5271911ae0390c0d1cdb8960dc4351f3b19f5e2e9c72a13d5565bd011a89fc`
- Risk: **medium** — Derived from review_required diagnostic DIAG-097fb3e27fe309801be1.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: **New slash command** `.windsurf/workflows/koru-gate.md` (`/koru-gate`) — read-only manual triad invocation: detect → regix gates → testql smoke → wup status → aggregate decision. Used by the agent before `planfile ticket complete`. Source intent: **New slash command** `.windsurf/workflows/koru-gate.md` (`/koru-gate`) — read-only manual triad invocation: detect → regix gates → testql smoke → wup status → aggregate decision. Used by the agent before `planfile ticket complete`. Paths: .windsurf/workflows/koru-gate.md.
- Changes:
  - `modify` `.windsurf/workflows/koru-gate.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-097fb3e27fe309801be1 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .windsurf/workflows/koru-gate.md.
- Diagnostics: `DIAG-097fb3e27fe309801be1`
- Evidence records: `INT-CHANGELOG-2f966e1687a9180a828c`
- Rollback: Revert the proposed changes to .windsurf/workflows/koru-gate.md and re-run todo2code diagnostics.

### Implement Update docs/photo-vql-jetbrains-wayland.md (`CPLAN-71743cce4cf42aaaccc9`)

- Plan hash: `71743cce4cf42aaaccc9a52c9868252a7c6ceef2fb9490c68b8c8843a6c1b2b0`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0067c5596efa659df859.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/photo-vql-jetbrains-wayland.md Source intent: Update docs/photo-vql-jetbrains-wayland.md Paths: docs/photo-vql-jetbrains-wayland.md.
- Changes:
  - `modify` `docs/photo-vql-jetbrains-wayland.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0067c5596efa659df859 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/photo-vql-jetbrains-wayland.md.
- Diagnostics: `DIAG-0067c5596efa659df859`
- Evidence records: `INT-CHANGELOG-b238af8c0b958deb2f63`
- Rollback: Revert the proposed changes to docs/photo-vql-jetbrains-wayland.md and re-run todo2code diagnostics.

### Implement Update .windsurf/workflows/koru-gate.md (`CPLAN-7ecc6afe3afef78de521`)

- Plan hash: `7ecc6afe3afef78de521a113372fae31fee52159430d2f55f0c6d068c09d29de`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0af0f4ad8be0fbbb851b.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .windsurf/workflows/koru-gate.md Source intent: Update .windsurf/workflows/koru-gate.md Paths: .windsurf/workflows/koru-gate.md.
- Changes:
  - `modify` `.windsurf/workflows/koru-gate.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0af0f4ad8be0fbbb851b (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .windsurf/workflows/koru-gate.md.
- Diagnostics: `DIAG-0af0f4ad8be0fbbb851b`
- Evidence records: `INT-CHANGELOG-e0192cfa36026daec07d`
- Rollback: Revert the proposed changes to .windsurf/workflows/koru-gate.md and re-run todo2code diagnostics.

### Implement Update project/flow.png (`CPLAN-7f3e9a923ba862c6c580`)

- Plan hash: `7f3e9a923ba862c6c5806f98edda6f462c2380578fc8b0b0c6b2b68b4fe35757`
- Risk: **medium** — Derived from review_required diagnostic DIAG-092a69e1573a3cd38731.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/flow.png Source intent: Update project/flow.png Paths: project/flow.png.
- Changes:
  - `modify` `project/flow.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-092a69e1573a3cd38731 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/flow.png.
- Diagnostics: `DIAG-092a69e1573a3cd38731`
- Evidence records: `INT-CHANGELOG-c34461bc70b96cca11ca`
- Rollback: Revert the proposed changes to project/flow.png and re-run todo2code diagnostics.

### Implement Update .planfile/config.yaml (`CPLAN-81b95ee483a474ff8f98`)

- Plan hash: `81b95ee483a474ff8f984515b3c7771529ca5323c4c0788ffa50d1ac404fcbb4`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0a23399844b57935e321.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .planfile/config.yaml Source intent: Update .planfile/config.yaml Paths: .planfile/config.yaml.
- Changes:
  - `modify` `.planfile/config.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0a23399844b57935e321 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .planfile/config.yaml.
- Diagnostics: `DIAG-0a23399844b57935e321`
- Evidence records: `INT-CHANGELOG-f68195cf68bb35696a95`
- Rollback: Revert the proposed changes to .planfile/config.yaml and re-run todo2code diagnostics.

### Implement Update project/compact_flow.png (`CPLAN-83b80473d25fa20728c8`)

- Plan hash: `83b80473d25fa20728c8c64d79b3f6837b42897a8967ec29ce574bff0b001692`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0baa6f38bc8d225ef98c.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/compact_flow.png Source intent: Update project/compact_flow.png Paths: project/compact_flow.png.
- Changes:
  - `modify` `project/compact_flow.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0baa6f38bc8d225ef98c (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/compact_flow.png.
- Diagnostics: `DIAG-0baa6f38bc8d225ef98c`
- Evidence records: `INT-CHANGELOG-f698c7dce00707e21643`
- Rollback: Revert the proposed changes to project/compact_flow.png and re-run todo2code diagnostics.

### Implement Update scripts/koru-autoloop.sh (`CPLAN-87ffbdbd755c9e88fa20`)

- Plan hash: `87ffbdbd755c9e88fa20dbe674e54b69b9489795b9cc7f9e839f14088c4059a5`
- Risk: **medium** — Derived from review_required diagnostic DIAG-054ad8529d41e81116eb.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update scripts/koru-autoloop.sh Source intent: Update scripts/koru-autoloop.sh Paths: scripts/koru-autoloop.sh.
- Changes:
  - `modify` `scripts/koru-autoloop.sh`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-054ad8529d41e81116eb (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: scripts/koru-autoloop.sh.
- Diagnostics: `DIAG-054ad8529d41e81116eb`
- Evidence records: `INT-CHANGELOG-d8022ee84cee16b0f923`
- Rollback: Revert the proposed changes to scripts/koru-autoloop.sh and re-run todo2code diagnostics.

### Implement `docs/llm-tools/op3/` — dokumentacja + `install.sh` dla `op3` (layered infra observation: physical/os/runtime/service/endpoint/ business). Companion redeploy/doql dla deeper device snapshots. (`CPLAN-88db75f2c79eb656bd27`)

- Plan hash: `88db75f2c79eb656bd277f27fea07de0156c16c681564d78b7d52c6892b10752`
- Risk: **medium** — Derived from review_required diagnostic DIAG-1135249f7438290f32e4.; Touches 2 declared paths.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: `docs/llm-tools/op3/` — dokumentacja + `install.sh` dla `op3` (layered infra observation: physical/os/runtime/service/endpoint/ business). Companion redeploy/doql dla deeper device snapshots. Source intent: `docs/llm-tools/op3/` — dokumentacja + `install.sh` dla `op3` (layered infra observation: physical/os/runtime/service/endpoint/ business). Companion redeploy/doql dla deeper device snapshots. Paths: docs/llm-tools/op3, install.sh. Symbols: install.sh, op3.
- Changes:
  - `modify` `docs/llm-tools/op3` symbols: `install.sh`, `op3`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
  - `modify` `install.sh` symbols: `install.sh`, `op3`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Provide AST evidence for symbols: install.sh, op3.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-1135249f7438290f32e4 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/llm-tools/op3, install.sh.
- Diagnostics: `DIAG-1135249f7438290f32e4`
- Evidence records: `INT-CHANGELOG-4f34afd331e210049349`
- Rollback: Revert the proposed changes to docs/llm-tools/op3, install.sh and re-run todo2code diagnostics.

### Implement Update docs/pipeline-design.md (`CPLAN-8d0c734672e84facd715`)

- Plan hash: `8d0c734672e84facd715971b6bbe6654e3678799dec5bc71f08aa90fe044425e`
- Risk: **medium** — Derived from review_required diagnostic DIAG-00437c8f077193d86ba7.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/pipeline-design.md Source intent: Update docs/pipeline-design.md Paths: docs/pipeline-design.md.
- Changes:
  - `modify` `docs/pipeline-design.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-00437c8f077193d86ba7 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/pipeline-design.md.
- Diagnostics: `DIAG-00437c8f077193d86ba7`
- Evidence records: `INT-CHANGELOG-ac1326f3acfd4659c4d0`
- Rollback: Revert the proposed changes to docs/pipeline-design.md and re-run todo2code diagnostics.

### Implement Update .planfile/config.yaml (`CPLAN-91b99966524007883882`)

- Plan hash: `91b99966524007883882fde142569027ae255b242eb8297be00a6c1393f5944c`
- Risk: **medium** — Derived from review_required diagnostic DIAG-03b213947f69d470b02e.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .planfile/config.yaml Source intent: Update .planfile/config.yaml Paths: .planfile/config.yaml.
- Changes:
  - `modify` `.planfile/config.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-03b213947f69d470b02e (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .planfile/config.yaml.
- Diagnostics: `DIAG-03b213947f69d470b02e`
- Evidence records: `INT-CHANGELOG-59833ea06453204fd85a`
- Rollback: Revert the proposed changes to .planfile/config.yaml and re-run todo2code diagnostics.

### Implement Update tests/test_autopilot_os_injector.py (`CPLAN-9b4ffa31a427c5e291f4`)

- Plan hash: `9b4ffa31a427c5e291f45cf48badde7023e36c4d9365d8c23b0fcd400bda23b0`
- Risk: **medium** — Derived from review_required diagnostic DIAG-10dd9d7c5b660f331ff5.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update tests/test_autopilot_os_injector.py Source intent: Update tests/test_autopilot_os_injector.py Paths: tests/test_autopilot_os_injector.py.
- Changes:
  - `modify` `tests/test_autopilot_os_injector.py`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-10dd9d7c5b660f331ff5 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: tests/test_autopilot_os_injector.py.
- Diagnostics: `DIAG-10dd9d7c5b660f331ff5`
- Evidence records: `INT-CHANGELOG-200164fb613d665c6e18`
- Rollback: Revert the proposed changes to tests/test_autopilot_os_injector.py and re-run todo2code diagnostics.

### Implement Update .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json (`CPLAN-a20aa9e3c3c6f55f964a`)

- Plan hash: `a20aa9e3c3c6f55f964a906be0bcdcbf83bb5d3998ed232089932ee0cba867fd`
- Risk: **medium** — Derived from review_required diagnostic DIAG-020c07250a590128943c.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json Source intent: Update .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json Paths: .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json.
- Changes:
  - `modify` `.vdisplay/2026-06-10T14-32-42Z__local__cli/env.json`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-020c07250a590128943c (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json.
- Diagnostics: `DIAG-020c07250a590128943c`
- Evidence records: `INT-CHANGELOG-0e90c54176f454435b41`
- Rollback: Revert the proposed changes to .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json and re-run todo2code diagnostics.

### Implement Update docs/llm-tools/costs/install.sh (`CPLAN-a47d36ac7abd0c4e97d0`)

- Plan hash: `a47d36ac7abd0c4e97d04b875adb08fb6d481cabeb066d6e5d196118cfca463e`
- Risk: **medium** — Derived from review_required diagnostic DIAG-040eba6f82854d42d2ff.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/llm-tools/costs/install.sh Source intent: Update docs/llm-tools/costs/install.sh Paths: docs/llm-tools/costs/install.sh.
- Changes:
  - `modify` `docs/llm-tools/costs/install.sh`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-040eba6f82854d42d2ff (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/llm-tools/costs/install.sh.
- Diagnostics: `DIAG-040eba6f82854d42d2ff`
- Evidence records: `INT-CHANGELOG-99fc853195216e359ace`
- Rollback: Revert the proposed changes to docs/llm-tools/costs/install.sh and re-run todo2code diagnostics.

### Implement Update .planfile/config.yaml (`CPLAN-a85279117309410210a9`)

- Plan hash: `a85279117309410210a9402368c523489c23a34937d3df0f9219ac5abf399a02`
- Risk: **medium** — Derived from review_required diagnostic DIAG-098ff5af3cad8aca0bfb.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .planfile/config.yaml Source intent: Update .planfile/config.yaml Paths: .planfile/config.yaml.
- Changes:
  - `modify` `.planfile/config.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-098ff5af3cad8aca0bfb (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .planfile/config.yaml.
- Diagnostics: `DIAG-098ff5af3cad8aca0bfb`
- Evidence records: `INT-CHANGELOG-8c434c99be6eac7fd2e7`
- Rollback: Revert the proposed changes to .planfile/config.yaml and re-run todo2code diagnostics.

### Implement Update .koru/project.json (`CPLAN-ae746c28dd1f9c79c791`)

- Plan hash: `ae746c28dd1f9c79c7919e43cadd1ed3f90dab801dd30a426f8be7beb44149d6`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0ad8cdf8a8b01b62b3c4.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .koru/project.json Source intent: Update .koru/project.json Paths: .koru/project.json.
- Changes:
  - `modify` `.koru/project.json`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0ad8cdf8a8b01b62b3c4 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .koru/project.json.
- Diagnostics: `DIAG-0ad8cdf8a8b01b62b3c4`
- Evidence records: `INT-CHANGELOG-f865ed0977fd5ceb1a03`
- Rollback: Revert the proposed changes to .koru/project.json and re-run todo2code diagnostics.

### Implement Update docs/autopilot-quickstart.md (`CPLAN-b13438d99084c6d02632`)

- Plan hash: `b13438d99084c6d026327d8f975eab38e12a865308404ce6c8faa8630fd9d0af`
- Risk: **medium** — Derived from review_required diagnostic DIAG-080483d7a1eee84c2017.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/autopilot-quickstart.md Source intent: Update docs/autopilot-quickstart.md Paths: docs/autopilot-quickstart.md.
- Changes:
  - `modify` `docs/autopilot-quickstart.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-080483d7a1eee84c2017 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/autopilot-quickstart.md.
- Diagnostics: `DIAG-080483d7a1eee84c2017`
- Evidence records: `INT-CHANGELOG-8cda167472ad89dda11b`
- Rollback: Revert the proposed changes to docs/autopilot-quickstart.md and re-run todo2code diagnostics.

### Implement Update tests/test_provider_portal_screencast.py (`CPLAN-bda857501f334107a3a0`)

- Plan hash: `bda857501f334107a3a06238008d9152367df7395a57f9318e91384b04126953`
- Risk: **medium** — Derived from review_required diagnostic DIAG-066481178aef6218a58b.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update tests/test_provider_portal_screencast.py Source intent: Update tests/test_provider_portal_screencast.py Paths: tests/test_provider_portal_screencast.py.
- Changes:
  - `modify` `tests/test_provider_portal_screencast.py`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-066481178aef6218a58b (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: tests/test_provider_portal_screencast.py.
- Diagnostics: `DIAG-066481178aef6218a58b`
- Evidence records: `INT-CHANGELOG-f0782327ecbf9ee3400a`
- Rollback: Revert the proposed changes to tests/test_provider_portal_screencast.py and re-run todo2code diagnostics.

### Implement Update tests/test_autopilot_injector.py (`CPLAN-c1e8a1f1e54c3d7c2952`)

- Plan hash: `c1e8a1f1e54c3d7c2952413296adfedc7f7dc335944dc3f923a686850c401541`
- Risk: **medium** — Derived from review_required diagnostic DIAG-038e836332e13c38b11e.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update tests/test_autopilot_injector.py Source intent: Update tests/test_autopilot_injector.py Paths: tests/test_autopilot_injector.py.
- Changes:
  - `modify` `tests/test_autopilot_injector.py`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-038e836332e13c38b11e (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: tests/test_autopilot_injector.py.
- Diagnostics: `DIAG-038e836332e13c38b11e`
- Evidence records: `INT-CHANGELOG-171ec3f996dcb368e98b`
- Rollback: Revert the proposed changes to tests/test_autopilot_injector.py and re-run todo2code diagnostics.

### Implement Update .koru/project.json (`CPLAN-c6b138c43159cfae676f`)

- Plan hash: `c6b138c43159cfae676f6d4a3eb7a4f89d7f4b6bee617c25d013fbc27f3aeacb`
- Risk: **medium** — Derived from review_required diagnostic DIAG-054e1ec37a29e67d976a.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .koru/project.json Source intent: Update .koru/project.json Paths: .koru/project.json.
- Changes:
  - `modify` `.koru/project.json`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-054e1ec37a29e67d976a (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .koru/project.json.
- Diagnostics: `DIAG-054e1ec37a29e67d976a`
- Evidence records: `INT-CHANGELOG-bce9356482acea8093a6`
- Rollback: Revert the proposed changes to .koru/project.json and re-run todo2code diagnostics.

### Implement Update project/calls.png (`CPLAN-ca7419a314e03901d4d3`)

- Plan hash: `ca7419a314e03901d4d32cce4461836de4fcaa6261d54f62c7330d9fa398f070`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0c16ba857ca282189441.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/calls.png Source intent: Update project/calls.png Paths: project/calls.png.
- Changes:
  - `modify` `project/calls.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0c16ba857ca282189441 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/calls.png.
- Diagnostics: `DIAG-0c16ba857ca282189441`
- Evidence records: `INT-CHANGELOG-e1091d7b0247085bb871`
- Rollback: Revert the proposed changes to project/calls.png and re-run todo2code diagnostics.

### Implement Update docs/plans/capture-providers-refactor.md (`CPLAN-d6dcaa7d7d108acc7869`)

- Plan hash: `d6dcaa7d7d108acc7869be0e417e076ccb01846c88e05af4a846e85e4662929e`
- Risk: **medium** — Derived from review_required diagnostic DIAG-06c37e0ac14ba6c39e04.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/plans/capture-providers-refactor.md Source intent: Update docs/plans/capture-providers-refactor.md Paths: docs/plans/capture-providers-refactor.md.
- Changes:
  - `modify` `docs/plans/capture-providers-refactor.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-06c37e0ac14ba6c39e04 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/plans/capture-providers-refactor.md.
- Diagnostics: `DIAG-06c37e0ac14ba6c39e04`
- Evidence records: `INT-CHANGELOG-a6d7d0491c2ff551bcf4`
- Rollback: Revert the proposed changes to docs/plans/capture-providers-refactor.md and re-run todo2code diagnostics.

### Implement Update project/compact_flow.png (`CPLAN-d9ae54f1d015358d7396`)

- Plan hash: `d9ae54f1d015358d739683f5b245fa011572829cbda1330bbb84381ee3116be9`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0f0c6166aa2d4b880ec9.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/compact_flow.png Source intent: Update project/compact_flow.png Paths: project/compact_flow.png.
- Changes:
  - `modify` `project/compact_flow.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0f0c6166aa2d4b880ec9 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/compact_flow.png.
- Diagnostics: `DIAG-0f0c6166aa2d4b880ec9`
- Evidence records: `INT-CHANGELOG-b3b313a187116ca33f0b`
- Rollback: Revert the proposed changes to project/compact_flow.png and re-run todo2code diagnostics.

### Implement `docs/llm-tools/mdflow/` — markdown dependency analyzer (extract markpact:ref, generate Mermaid diagrams, validate links). (`CPLAN-d9e3446fce85856eb7ec`)

- Plan hash: `d9e3446fce85856eb7ec8b36242f4676a6c2164655ece149919fb275e6775c16`
- Risk: **medium** — Derived from review_required diagnostic DIAG-00066abd98c3f5946b08.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: `docs/llm-tools/mdflow/` — markdown dependency analyzer (extract markpact:ref, generate Mermaid diagrams, validate links). Source intent: `docs/llm-tools/mdflow/` — markdown dependency analyzer (extract markpact:ref, generate Mermaid diagrams, validate links). Paths: docs/llm-tools/mdflow.
- Changes:
  - `modify` `docs/llm-tools/mdflow`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-00066abd98c3f5946b08 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/llm-tools/mdflow.
- Diagnostics: `DIAG-00066abd98c3f5946b08`
- Evidence records: `INT-CHANGELOG-7a4c6b6ff10c1a07aead`
- Rollback: Revert the proposed changes to docs/llm-tools/mdflow and re-run todo2code diagnostics.

### Implement Update plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt (`CPLAN-e51e8f728ad7de5e9713`)

- Plan hash: `e51e8f728ad7de5e97131ef05e6cbabbb50a29c7290d9623bf6c96a1177bd1eb`
- Risk: **medium** — Derived from review_required diagnostic DIAG-044f790756883ee703a9.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt Source intent: Update plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt Paths: plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt. Symbols: KoruAutopilotService.
- Changes:
  - `modify` `plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt` symbols: `KoruAutopilotService`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Provide AST evidence for symbols: KoruAutopilotService.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-044f790756883ee703a9 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt.
- Diagnostics: `DIAG-044f790756883ee703a9`
- Evidence records: `INT-CHANGELOG-0e727a4300f17b2272e7`
- Rollback: Revert the proposed changes to plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt and re-run todo2code diagnostics.

### Implement Update docs/autopilot-quickstart.md (`CPLAN-e9672e20b8e3945f84b2`)

- Plan hash: `e9672e20b8e3945f84b2d389ce310e73e0fa5ac98a44849a37fb999e62e050ae`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0cb6729ac51f8fa422e4.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/autopilot-quickstart.md Source intent: Update docs/autopilot-quickstart.md Paths: docs/autopilot-quickstart.md.
- Changes:
  - `modify` `docs/autopilot-quickstart.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0cb6729ac51f8fa422e4 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/autopilot-quickstart.md.
- Diagnostics: `DIAG-0cb6729ac51f8fa422e4`
- Evidence records: `INT-CHANGELOG-f4d367f28f9afcd65cb2`
- Rollback: Revert the proposed changes to docs/autopilot-quickstart.md and re-run todo2code diagnostics.

### Implement Update .planfile/config.yaml (`CPLAN-ea9f2b403e80ef961f5a`)

- Plan hash: `ea9f2b403e80ef961f5a10fe90ae5e0e07c52238819ecb912460ffbb076219d9`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0e6e38e505d08420513e.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .planfile/config.yaml Source intent: Update .planfile/config.yaml Paths: .planfile/config.yaml.
- Changes:
  - `modify` `.planfile/config.yaml`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0e6e38e505d08420513e (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .planfile/config.yaml.
- Diagnostics: `DIAG-0e6e38e505d08420513e`
- Evidence records: `INT-CHANGELOG-32db45f03496cef0469c`
- Rollback: Revert the proposed changes to .planfile/config.yaml and re-run todo2code diagnostics.

### Implement Update project/calls.png (`CPLAN-eb5fa99aaaa71575f740`)

- Plan hash: `eb5fa99aaaa71575f7401dd9e995d54069ce19ca952c91429d6d7d97197a591a`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0db2bf8be0d7716eb33e.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/calls.png Source intent: Update project/calls.png Paths: project/calls.png.
- Changes:
  - `modify` `project/calls.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0db2bf8be0d7716eb33e (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/calls.png.
- Diagnostics: `DIAG-0db2bf8be0d7716eb33e`
- Evidence records: `INT-CHANGELOG-1a3bd4cb9b6e65d7acb7`
- Rollback: Revert the proposed changes to project/calls.png and re-run todo2code diagnostics.

### Implement Update docs/autonomy-ide-cursor.md (`CPLAN-f180d82c7e9ab1bb21ca`)

- Plan hash: `f180d82c7e9ab1bb21cae3800aad3bbe4a9ed2ecc0a51b0f5cf7023438468740`
- Risk: **medium** — Derived from review_required diagnostic DIAG-113474bdf278a3bb050a.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update docs/autonomy-ide-cursor.md Source intent: Update docs/autonomy-ide-cursor.md Paths: docs/autonomy-ide-cursor.md.
- Changes:
  - `modify` `docs/autonomy-ide-cursor.md`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-113474bdf278a3bb050a (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: docs/autonomy-ide-cursor.md.
- Diagnostics: `DIAG-113474bdf278a3bb050a`
- Evidence records: `INT-CHANGELOG-081a02e45f006e0fa3d5`
- Rollback: Revert the proposed changes to docs/autonomy-ide-cursor.md and re-run todo2code diagnostics.

### Implement Update .koru/project.json (`CPLAN-f382d25273fcb2b7d3dd`)

- Plan hash: `f382d25273fcb2b7d3ddc952c82e1c5e806994fc3a97b5ff5d89717e789ca19a`
- Risk: **medium** — Derived from review_required diagnostic DIAG-04f94f9a642f7414f69c.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update .koru/project.json Source intent: Update .koru/project.json Paths: .koru/project.json.
- Changes:
  - `modify` `.koru/project.json`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-04f94f9a642f7414f69c (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: .koru/project.json.
- Diagnostics: `DIAG-04f94f9a642f7414f69c`
- Evidence records: `INT-CHANGELOG-62f03ca2c76efee8d036`
- Rollback: Revert the proposed changes to .koru/project.json and re-run todo2code diagnostics.

### Implement Update project/calls.png (`CPLAN-f6bacb319a08314848ac`)

- Plan hash: `f6bacb319a08314848ac4628bb2aab534d4610d71abf36d020f889bc3df48d8c`
- Risk: **medium** — Derived from review_required diagnostic DIAG-03f95e5e8042e41e4700.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update project/calls.png Source intent: Update project/calls.png Paths: project/calls.png.
- Changes:
  - `modify` `project/calls.png`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-03f95e5e8042e41e4700 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: project/calls.png.
- Diagnostics: `DIAG-03f95e5e8042e41e4700`
- Evidence records: `INT-CHANGELOG-7fe5a823a6c995f07183`
- Rollback: Revert the proposed changes to project/calls.png and re-run todo2code diagnostics.

### Implement Update tests/test_provider_portal_screencast.py (`CPLAN-fda18150c0609cc43207`)

- Plan hash: `fda18150c0609cc432077620da47b3c691440d7ee41d9dd4d4803520cde5404d`
- Risk: **medium** — Derived from review_required diagnostic DIAG-0b4e60b33cfa6d0b2be8.; Touches 1 declared path.
- Confidence: 0.80
- Description: Wpis wydania nie ma powiązanego commita ani faktu AST: Update tests/test_provider_portal_screencast.py Source intent: Update tests/test_provider_portal_screencast.py Paths: tests/test_provider_portal_screencast.py.
- Changes:
  - `modify` `tests/test_provider_portal_screencast.py`
    - Zweryfikować wpis lub dodać jednoznaczne odwołanie do ticketu, commita, pliku albo symbolu.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-0b4e60b33cfa6d0b2be8 (CHANGELOG_WITHOUT_IMPLEMENTATION).
  - [ ] Touch only the declared paths: tests/test_provider_portal_screencast.py.
- Diagnostics: `DIAG-0b4e60b33cfa6d0b2be8`
- Evidence records: `INT-CHANGELOG-d4f34103320961afb484`
- Rollback: Revert the proposed changes to tests/test_provider_portal_screencast.py and re-run todo2code diagnostics.


## P2

### Implement Trzeba bumpać dependency (`requirements*.txt`). (`CPLAN-eff860615a0426d95ebb`)

- Plan hash: `eff860615a0426d95ebb8556096f74ae0ba7c448a0dc0ab7567e169a4db3e4f8`
- Risk: **low** — Derived from warning diagnostic DIAG-051669dca564a727b337.; Touches 1 declared path.
- Confidence: 0.72
- Description: Nie znaleziono powiązanego rekordu Git ani faktu AST dla: Trzeba bumpać dependency (`requirements*.txt`). Source intent: Trzeba bumpać dependency (`requirements*.txt`). Paths: requirements*.txt.
- Changes:
  - `modify` `requirements*.txt`
    - Dodać identyfikator ticketu/symbolu albo dostarczyć implementację i ponownie uruchomić linker.
- Acceptance criteria:
  - [ ] Do not introduce new blocking diagnostics.
  - [ ] Re-run todo2code link+diagnose and clear diagnostic DIAG-051669dca564a727b337 (PLANNED_NOT_IMPLEMENTED).
  - [ ] Touch only the declared paths: requirements*.txt.
- Diagnostics: `DIAG-051669dca564a727b337`
- Evidence records: `INT-DOC-93c2289e18a75d6db4e3`
- Rollback: Revert the proposed changes to requirements*.txt and re-run todo2code diagnostics.

## After implementation

1. Re-run `t2c pipeline` (or extract + link + diagnose) on the changed tree.
2. `t2c evaluate-code-change <plan.json> --before-graph … --after-graph … --out acceptance.json`.
3. Require `accepted=true` and human/CI review before marking work DONE.
