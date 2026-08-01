<!-- t2c.code-change-review/v1 -->
# todo2code proposed code changes

This document is a grounded **review brief**, not an auto-applied source patch.
Implement the listed paths in a normal branch, re-run the pipeline, then
`t2c evaluate-code-change`. Acceptance still requires human/CI approval before DONE.

Graph fingerprint: `dd9b063f4ba8f2e3876fa2edd3264af2f26700c0e12ca50e16c5be0e98c0c146`

## P1

### Implement Update tests/test_provider_portal_screencast.py (`CPLAN-026cc3d4bbeae91e7b98`)

- Plan hash: `026cc3d4bbeae91e7b983db9fff9cc74ce39d340600bc951906f35f1ed7e505d`
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

### Implement Update docs/architecture/volume-reduction-plan.yaml (`CPLAN-0480893c6b56efaa7dd2`)

- Plan hash: `0480893c6b56efaa7dd285f2b65f1f13acbef6b08be1fb994dafbb368a96cc3f`
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

### Implement `docs/llm-tools/mdflow/` — markdown dependency analyzer (extract markpact:ref, generate Mermaid diagrams, validate links). (`CPLAN-072f29a1a01c6f617ac1`)

- Plan hash: `072f29a1a01c6f617ac11df8d1071fb8af12f6d30e7fbf13743e4b949847f874`
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

### Implement Update docs/refactoring/REFACTORING_PLAN.md (`CPLAN-0b9d5fa3e344f731b922`)

- Plan hash: `0b9d5fa3e344f731b92228fe9ef66e0c576c8b50f7c9a7a9a108bb0c0f4736d5`
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

### Implement Update project/compact_flow.png (`CPLAN-1a3259936912eb3a53de`)

- Plan hash: `1a3259936912eb3a53ded576e2fff958b8fae2de2930715a34a5ff876d3620dd`
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

### Implement Update tests/test_autopilot_injector.py (`CPLAN-23211aa171154406732b`)

- Plan hash: `23211aa171154406732b84c6371b90d86ca2d78e85d15a915c990c8028fe6185`
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

### Implement Update docs/agent-backends-architecture.md (`CPLAN-298bd9a2b167138db233`)

- Plan hash: `298bd9a2b167138db2334a34fb249a23f7d5ad77bc197e4728ef92629a500502`
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

### Implement Update .windsurf/workflows/koru-gate.md (`CPLAN-2b29f64136b88edfcb68`)

- Plan hash: `2b29f64136b88edfcb687f33b8c7da468cc3d6e89b3a9d451ab3e83759f7123e`
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

### Implement Update docs/autopilot-quickstart.md (`CPLAN-325b686f9ee75ad3fecd`)

- Plan hash: `325b686f9ee75ad3fecd6f98179ee68d5bcd01ce8cdc01090b34da241b439a94`
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

### Implement Update docs/autopilot-roadmap.md (`CPLAN-3311c7fc7ebe69ed8d39`)

- Plan hash: `3311c7fc7ebe69ed8d39b3fbc67f54fe07c8a0032336dd47947b70cd39d9057b`
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

### Implement Update docs/koru_auto_vs_observe_up.md (`CPLAN-376816f7398403b4a3bf`)

- Plan hash: `376816f7398403b4a3bf2023fde97e979a3e8b112c65688661e9089e3975ea2b`
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

### Implement Update tests/test_autopilot_injector.py (`CPLAN-3d477408f5eda57e6477`)

- Plan hash: `3d477408f5eda57e6477ae4c264ad0a7291bd22adcc82307199a95066a99dadc`
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

### Implement Update tests/test_provider_portal_screencast.py (`CPLAN-425d744e13703631d36f`)

- Plan hash: `425d744e13703631d36fd8454b4f642d95bc2cf7b6827cf4fb77c4b609db6ea6`
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

### Implement **New slash command** `.windsurf/workflows/koru-gate.md` (`/koru-gate`) — read-only manual triad invocation: detect → regix gates → testql smoke → wup status → aggregate decision. Used by the agent before `planfile ticket complete`. (`CPLAN-472ec22cbaae36c2c4f5`)

- Plan hash: `472ec22cbaae36c2c4f516e4435885a8211ee2b35846ead746315f206b788b9f`
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

### Implement Update docs/llm-tools/costs/install.sh (`CPLAN-49b2e41dac6320801330`)

- Plan hash: `49b2e41dac63208013304fabc6f2168225537e9840762cd1bf4d574686ac65f2`
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

### Implement Update docs/autodiagnostics-auto-repair.md (`CPLAN-4c03553f7eda91135918`)

- Plan hash: `4c03553f7eda9113591894d6998522824b3e4346e3eae83efdc890edeb29146c`
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

### Implement Update tests/test_autopilot_os_injector.py (`CPLAN-52d4bf17c6659491054c`)

- Plan hash: `52d4bf17c6659491054c1e0e468923f47e58412018b6bc562de7ec51835a980b`
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

### Implement Update .koru/project.json (`CPLAN-5300aa8869af4d84a0e7`)

- Plan hash: `5300aa8869af4d84a0e716e8190aa07eb212a76837c5f0b72fe3af661bb647b2`
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

### Implement Update project/calls.png (`CPLAN-540f7baf71574fbbc9f8`)

- Plan hash: `540f7baf71574fbbc9f86c7804d75f7a65b76fcc6b55b71f98a886d6219390d7`
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

### Implement `docs/llm-tools/op3/` — dokumentacja + `install.sh` dla `op3` (layered infra observation: physical/os/runtime/service/endpoint/ business). Companion redeploy/doql dla deeper device snapshots. (`CPLAN-5bef3837173c1f20bdbe`)

- Plan hash: `5bef3837173c1f20bdbee4e5d68f8ea8dcd3ee9113e6da80e52583c950850b53`
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

### Implement Update .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json (`CPLAN-5cb97c7ef9338c62946b`)

- Plan hash: `5cb97c7ef9338c62946bb0adfc5f79e752e2e5bf1b9cab4bec85220a223b57d2`
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

### Implement Update project/compact_flow.png (`CPLAN-6478f69066ca4d8b5db7`)

- Plan hash: `6478f69066ca4d8b5db79cac5314692b2d76d860f0892a398a1883f441d95e73`
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

### Implement Update docs/photo-vql-jetbrains-wayland.md (`CPLAN-648552d5ff37e8d2f126`)

- Plan hash: `648552d5ff37e8d2f126222de70baeec99c039d63b47baf48ec77c170aa02846`
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

### Implement Update project/flow.png (`CPLAN-680f42b9f71058ab2d36`)

- Plan hash: `680f42b9f71058ab2d360a589f02a604337b13ea59bed71dd3116fe0f99680fd`
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

### Implement Update docs/adr/adr-auto-002-autonomous-decision-llm.md (`CPLAN-70ec2a01b18726f23871`)

- Plan hash: `70ec2a01b18726f23871e2f12119398ae59597c90b0c11975f86c3fd21bac698`
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

### Implement Update project/calls.png (`CPLAN-780eb0ba45839f02e261`)

- Plan hash: `780eb0ba45839f02e26185ee5b7c725d3a38479df47d0968c52b736a108820ee`
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

### Implement Update .planfile/config.yaml (`CPLAN-7bb26f8c45eb3f0b69af`)

- Plan hash: `7bb26f8c45eb3f0b69afdba56fccce94339039c1ac4dfccb1ff93a715a39959e`
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

### Implement Update .planfile/config.yaml (`CPLAN-87555ef180882bb92cf5`)

- Plan hash: `87555ef180882bb92cf5f458d919bd7f3248b5ba117b8db57fbb3503f5d0e30b`
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

### Implement Update project/calls.png (`CPLAN-8a9353aa0e87657f303a`)

- Plan hash: `8a9353aa0e87657f303ab128d18f65ebb1f05da6cefe187ebd3a70df709262af`
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

### Implement Update project/compact_flow.png (`CPLAN-9990aa263bcf11930089`)

- Plan hash: `9990aa263bcf11930089a7425bd642c6341a9398a2577d681a527f513a50851c`
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

### Implement Update .planfile/config.yaml (`CPLAN-a3c3b0235ac4d73c5545`)

- Plan hash: `a3c3b0235ac4d73c55456f848b1567db390dd7b66f7390237af2db9501e48487`
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

### Implement Update .koru/project.json (`CPLAN-a8306431d258057b3251`)

- Plan hash: `a8306431d258057b3251a041674fb3b5ff0e36182505185f116e5e29e280c55c`
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

### Implement Update .planfile/config.yaml (`CPLAN-a8804cb0ce84d83c46d4`)

- Plan hash: `a8804cb0ce84d83c46d4b4a314f3999a05758a6388d68b1667511b91aab76b28`
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

### Implement Update docs/autonomy-ide-cursor.md (`CPLAN-b332c555c21b4f4d4a67`)

- Plan hash: `b332c555c21b4f4d4a6740df7ad70126f5bbe5062b11f5224c241516805ee4a2`
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

### Implement Update .koru/project.json (`CPLAN-b349f9272bc2d54b4442`)

- Plan hash: `b349f9272bc2d54b4442b18ee595fcc1c6f73fd8bf5ccd06a9d23df82a31e0a4`
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

### Implement Update docs/autopilot-quickstart.md (`CPLAN-b5952880fd2186d670db`)

- Plan hash: `b5952880fd2186d670db7a9abcd796abb224c41301b28779e7e9c8acae481d5a`
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

### Implement Update project/compact_flow.png (`CPLAN-bc4277edfea4abe05e81`)

- Plan hash: `bc4277edfea4abe05e819b785f39cc7b587802eac3817864e0e8646074fb5cf8`
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

### Implement Update scripts/koru-autoloop.sh (`CPLAN-bfeb886aa9c3e7ab927d`)

- Plan hash: `bfeb886aa9c3e7ab927da10f9a23da66043ce69950b7b321e899ac981d72d339`
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

### Implement Update docs/pipeline-design.md (`CPLAN-c0f02f4399f84802ebf5`)

- Plan hash: `c0f02f4399f84802ebf506b192b3cad7078b0600ec2d1dfbd016915fc90c1799`
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

### Implement Update docs/architecture/volume-reduction-plan.yaml (`CPLAN-d0c17bad6e47dc6d4187`)

- Plan hash: `d0c17bad6e47dc6d418799427fb1ad82ab370b76accc6077fc396cc93137ff93`
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

### Implement Update workflows/on-change-gates.md (`CPLAN-d22235b5d539f5db22af`)

- Plan hash: `d22235b5d539f5db22afe38916adde1e63564587043df4da6d3c72f90bfc5c7f`
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

### Implement Update .tmp/code2llm-plugins/compact_flow.png (`CPLAN-d2694b9a936b5ce072cf`)

- Plan hash: `d2694b9a936b5ce072cf2b3c0a218b63d7134f742d9a824a388eb294213dd903`
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

### Implement Update testql-testing/scenarios/realtime-health.testql.toon.yaml (`CPLAN-d494110b966f907e0896`)

- Plan hash: `d494110b966f907e08961e274a1b2182a62a0bdc0c3a6601e5b18dd59d1dc2f7`
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

### Implement Update docs/plans/capture-providers-refactor.md (`CPLAN-e039876bb95aea466f44`)

- Plan hash: `e039876bb95aea466f445b847532e48c2b110713622adf1c63f5c5bea4772fc5`
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

### Implement Update .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json (`CPLAN-e7c6298d6e1ace724755`)

- Plan hash: `e7c6298d6e1ace724755280d47c4332a4ee05b8b2d49408e14dff2de87f411d7`
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

### Implement Update .planfile/config.yaml (`CPLAN-e989c27c0f51086f4b93`)

- Plan hash: `e989c27c0f51086f4b9354a4b59398fde29b5f2ed178e68cab2add51ea407ed3`
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

### Implement Update plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt (`CPLAN-e99f40a59769497a18ea`)

- Plan hash: `e99f40a59769497a18eaab73c86f94b939576f63f5d239b5ac1e7a5c332a7af1`
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

### Implement Update .planfile/config.yaml (`CPLAN-f69bdb1f2c2c60a0cdc9`)

- Plan hash: `f69bdb1f2c2c60a0cdc9ee02e2f6853903f75636a98ddc6dbd35312e20599751`
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

### Implement Update .planfile/config.yaml (`CPLAN-fdf163f290e16836df56`)

- Plan hash: `fdf163f290e16836df567ed957495c8691c9b710c5b350d3ea13f837da3b61ae`
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


## P2

### Implement Trzeba bumpać dependency (`requirements*.txt`). (`CPLAN-7e7f0c64416fa79656ba`)

- Plan hash: `7e7f0c64416fa79656ba019baf7e727ba0bc5e800dbf0a0ede740ed78e575045`
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
