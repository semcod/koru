<!-- t2c.code-change-review/v1 -->
# todo2code proposed code changes

This document is a grounded **review brief**, not an auto-applied source patch.
Implement the listed paths in a normal branch, re-run the pipeline, then
`t2c evaluate-code-change`. Acceptance still requires human/CI approval before DONE.

Graph fingerprint: `8206c794b8fc949c0abe5e5f9ee70290a76825f0f444effd322fda529889267f`

## P1

### Implement Update .vdisplay/2026-06-10T14-32-42Z__local__cli/env.json (`CPLAN-083e65a70baaff89a6a2`)

- Plan hash: `083e65a70baaff89a6a20776ee94a82f4c89c4837e88e9b1951c2c8a20aa176f`
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

### Implement Update .koru/project.json (`CPLAN-08ee81e2474c8e10fc34`)

- Plan hash: `08ee81e2474c8e10fc3450af59d2b3def9f5e5c9e73379a5c5b59c4dbf9e1a52`
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

### Implement `docs/llm-tools/op3/` — dokumentacja + `install.sh` dla `op3` (layered infra observation: physical/os/runtime/service/endpoint/ business). Companion redeploy/doql dla deeper device snapshots. (`CPLAN-15fa2883d44139c1743b`)

- Plan hash: `15fa2883d44139c1743b62cf628761d91e724f8e91dda53ce3922c91261ff339`
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

### Implement **New slash command** `.windsurf/workflows/koru-gate.md` (`/koru-gate`) — read-only manual triad invocation: detect → regix gates → testql smoke → wup status → aggregate decision. Used by the agent before `planfile ticket complete`. (`CPLAN-17ef320d9579e8c474cd`)

- Plan hash: `17ef320d9579e8c474cda6df98b476687739808cf53bd641d396125b3d827f48`
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

### Implement Update docs/refactoring/REFACTORING_PLAN.md (`CPLAN-17ffada7fcb74d80fb5e`)

- Plan hash: `17ffada7fcb74d80fb5e651181f5653d06ceb81b81cc0adc0e9be28bc8b3ed01`
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

### Implement Update docs/architecture/volume-reduction-plan.yaml (`CPLAN-2381df12ae4609e05bf8`)

- Plan hash: `2381df12ae4609e05bf85451f02e934c33f3fc4d9a8cfc0625757610ed22b95a`
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

### Implement Update tests/test_autopilot_os_injector.py (`CPLAN-2679bf189dde8d94b11a`)

- Plan hash: `2679bf189dde8d94b11a04a6c42fb634631ad65e04e5888bb1c9645676ce21a4`
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

### Implement Update .koru/project.json (`CPLAN-39c23c2bf3db71bfe669`)

- Plan hash: `39c23c2bf3db71bfe66905aa6b714f945a92aaf0c4784524e384a7b942ca73ea`
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

### Implement Update tests/test_provider_portal_screencast.py (`CPLAN-40c5476248d17346f790`)

- Plan hash: `40c5476248d17346f790c74376ef5f54b5c92a8d978a554d001304244ddaa85a`
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

### Implement Update docs/llm-tools/costs/install.sh (`CPLAN-43e2828a5d0829715834`)

- Plan hash: `43e2828a5d0829715834d1cad59b3646aeb4c8b7da72f73a0499edbe016ce538`
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

### Implement Update .planfile/config.yaml (`CPLAN-442cff85fd50c6022158`)

- Plan hash: `442cff85fd50c6022158b0b4c415dae2ac03565f09f4ff7dd6b342f5ef765cc7`
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

### Implement Update project/compact_flow.png (`CPLAN-487a8325a372c2df4767`)

- Plan hash: `487a8325a372c2df47679867566217d2e56994a11e0ae68d1a5b2d41de02c3db`
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

### Implement Update .windsurf/workflows/koru-gate.md (`CPLAN-4baf252f194b325b4427`)

- Plan hash: `4baf252f194b325b442756457d23c4e536baac602af1e9c31042afb9a8d977a1`
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

### Implement Update .planfile/config.yaml (`CPLAN-51f27e71ba6a46c5c8cd`)

- Plan hash: `51f27e71ba6a46c5c8cd768aa29cac86c4cfc812fcdfd3d1ccd7f8dfd1b87413`
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

### Implement Update .vdisplay/vdisplay-auto-observe-auto-vision-find-cursor.png.context.json (`CPLAN-57fe3742d83646967dc2`)

- Plan hash: `57fe3742d83646967dc2c2865a4f3e1936fae58fd557fd9785ea5a7f12762887`
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

### Implement Update testql-testing/scenarios/realtime-health.testql.toon.yaml (`CPLAN-5949b4928a7fca0473fc`)

- Plan hash: `5949b4928a7fca0473fc3ceeec88da5d82bbe5f8784e2f04f79ea0019ad78b7b`
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

### Implement Update project/compact_flow.png (`CPLAN-5984311e1b72aeb52605`)

- Plan hash: `5984311e1b72aeb526052b314caf4fbfb26b16b67167cdade41df02e25ab516a`
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

### Implement Update project/compact_flow.png (`CPLAN-5b5a2d6d5971f9053d61`)

- Plan hash: `5b5a2d6d5971f9053d611cee3d35ecffbd97793e7f32c97bf872282f563f7f19`
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

### Implement Update docs/koru_auto_vs_observe_up.md (`CPLAN-5d4d07f898fd829a2d07`)

- Plan hash: `5d4d07f898fd829a2d077295269457e3b5f96402b0c4be9899ae2e9282accd5e`
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

### Implement Update docs/photo-vql-jetbrains-wayland.md (`CPLAN-72da48dfae1759818ae4`)

- Plan hash: `72da48dfae1759818ae4b7470eeee4d40fa78d1376ccb5bb1c88587f1167742f`
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

### Implement Update tests/test_autopilot_injector.py (`CPLAN-7a97cabda92389890255`)

- Plan hash: `7a97cabda92389890255d113c382159aabe1f42cc966220e90a9e6eda57ce448`
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

### Implement Update project/calls.png (`CPLAN-7c50472f227aceb44ac6`)

- Plan hash: `7c50472f227aceb44ac6f299ff312f003a10bd8cf2cf8bd4c88c97afc3b1a63f`
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

### Implement Update docs/architecture/volume-reduction-plan.yaml (`CPLAN-8b5ad61423c13ec618c9`)

- Plan hash: `8b5ad61423c13ec618c94cf383fe918fc689b722f179c4524f28333a06fd7197`
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

### Implement Update docs/autopilot-roadmap.md (`CPLAN-8cc8de8028a7cc6ecbf3`)

- Plan hash: `8cc8de8028a7cc6ecbf3c1fec0fe2b076401fdff387d8dd76c2782d57cf7af2f`
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

### Implement Update tests/test_autopilot_injector.py (`CPLAN-9d00cf44081eedce6bbb`)

- Plan hash: `9d00cf44081eedce6bbb54632a7e843681c3764c6aad0236bd5e123a1c4ad441`
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

### Implement Update workflows/on-change-gates.md (`CPLAN-a8c3c2bec08f464c7680`)

- Plan hash: `a8c3c2bec08f464c7680658ec0d5b407e8deb9bc22702594c15aa40a1a5c6e75`
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

### Implement Update .tmp/code2llm-plugins/compact_flow.png (`CPLAN-b3d9815edf8ca53d9906`)

- Plan hash: `b3d9815edf8ca53d990613193b03411bd6ab7a5aaa2500d79cf8373ef93b31f6`
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

### Implement Update tests/test_provider_portal_screencast.py (`CPLAN-bbad63ed35219f422d27`)

- Plan hash: `bbad63ed35219f422d2758a23bd677d3e565b7e7ba0cc71443801ae0ab4f5917`
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

### Implement Update docs/autonomy-ide-cursor.md (`CPLAN-bd48b0e9430516ad99a7`)

- Plan hash: `bd48b0e9430516ad99a70a23198cdc18de1a3592bca8ed09f27d8bb7103afa59`
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

### Implement Update plugins/koru-autopilot-jetbrains/src/main/kotlin/com/semcod/koru/autopilot/KoruAutopilotService.kt (`CPLAN-c2badc3e24a458f21305`)

- Plan hash: `c2badc3e24a458f213056b53633aef2a733aede120f7ae10039d27d22edd1e1b`
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

### Implement Update .planfile/config.yaml (`CPLAN-c4172ca50580e559a184`)

- Plan hash: `c4172ca50580e559a184737eea484ec35b5eadfec895643378b4a0d0b681731f`
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

### Implement Update .planfile/config.yaml (`CPLAN-c9fbac5cc4456a5cfd06`)

- Plan hash: `c9fbac5cc4456a5cfd061d599981bbadcf5585730e0da535a6063c1429b4fcac`
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

### Implement Update project/compact_flow.png (`CPLAN-cb35519ff1d65b42f935`)

- Plan hash: `cb35519ff1d65b42f935d6616f0c6b2b660796974c2913711db33c39e2d018bc`
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

### Implement Update project/calls.png (`CPLAN-ccf699cd68e4c69a4606`)

- Plan hash: `ccf699cd68e4c69a460673486fca6f81b7484eb7588efcb8b1489f6fb3276052`
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

### Implement Update docs/adr/adr-auto-002-autonomous-decision-llm.md (`CPLAN-d0630f9a045c7bce33bb`)

- Plan hash: `d0630f9a045c7bce33bb02180a216998e14f1d81f5cc1c15b3425c05749fab5c`
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

### Implement Update project/flow.png (`CPLAN-d11f6fea6de3f955c7fa`)

- Plan hash: `d11f6fea6de3f955c7faba84561083c566541e9d28fafa8d3c91a0c24fe437cb`
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

### Implement Update docs/pipeline-design.md (`CPLAN-d39ef997a49aad3694f6`)

- Plan hash: `d39ef997a49aad3694f6cdcdf304f453a446ff9a6412879dc028fbe2c5a59ea9`
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

### Implement Update docs/autodiagnostics-auto-repair.md (`CPLAN-d7fda272e7d61f1fb201`)

- Plan hash: `d7fda272e7d61f1fb201b83197ece55a10f843b395c2d0f185123b75e0edcee7`
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

### Implement Update scripts/koru-autoloop.sh (`CPLAN-d8a909cc6ab208abf719`)

- Plan hash: `d8a909cc6ab208abf71944b58eb9d5284032dc3db7ecd9c2a5fbf8468c427f3d`
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

### Implement Update .koru/project.json (`CPLAN-da78807cf56aa29f6b70`)

- Plan hash: `da78807cf56aa29f6b70a1ccfbe9ae4902694a08da69288a0fb4d642fb86fe3a`
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

### Implement Update project/calls.png (`CPLAN-daa1d3f694ae5ca159be`)

- Plan hash: `daa1d3f694ae5ca159bec08d6a4fee0e0d9d8004a369ebddb55b273bdbae5f2c`
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

### Implement Update .planfile/config.yaml (`CPLAN-db9d2dde1ab4057028ea`)

- Plan hash: `db9d2dde1ab4057028ea9844b2bad504663b00d662e5b71c203c762fbd888d6e`
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

### Implement `docs/llm-tools/mdflow/` — markdown dependency analyzer (extract markpact:ref, generate Mermaid diagrams, validate links). (`CPLAN-dbf66eb0f0e14f53c553`)

- Plan hash: `dbf66eb0f0e14f53c553c8b008b7453ea55e7656ef762b189f7107ea2dce14d3`
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

### Implement Update .planfile/config.yaml (`CPLAN-f043ec8a3d0aee5e4a8e`)

- Plan hash: `f043ec8a3d0aee5e4a8ef4fe7c973d51c24b93de8d804247d90404bde0153905`
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

### Implement Update docs/autopilot-quickstart.md (`CPLAN-f4a808e7c57b91c52ca4`)

- Plan hash: `f4a808e7c57b91c52ca46a41c2bfce380f42a4758677fd60b08233ec5dae8030`
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

### Implement Update .planfile/config.yaml (`CPLAN-f4c16676a1c37b7f4b73`)

- Plan hash: `f4c16676a1c37b7f4b73fed951dd517551a8fcbad14a7e1a41506de7c044c816`
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

### Implement Update docs/agent-backends-architecture.md (`CPLAN-f90c146cc318db63d085`)

- Plan hash: `f90c146cc318db63d085c7f20836d8287b6bf28b038a69d5a525cb9d8da82df2`
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

### Implement Update docs/autopilot-quickstart.md (`CPLAN-fba755563b046d522741`)

- Plan hash: `fba755563b046d5227413bb13a1e4558a7cd56be089fc484e824c300e03d064b`
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

### Implement Update docs/plans/capture-providers-refactor.md (`CPLAN-fdef42d4bb7b71ef646c`)

- Plan hash: `fdef42d4bb7b71ef646c2cab429f3479f730f7ef3ef0d9137529bfd5051c83d2`
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


## P2

### Implement Trzeba bumpać dependency (`requirements*.txt`). (`CPLAN-4b0b34703669553b489b`)

- Plan hash: `4b0b34703669553b489b0f603c35dcc03cdf406778a1cf140608d2eeff26d136`
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
