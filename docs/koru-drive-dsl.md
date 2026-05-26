# Koru Drive DSL — transparent integration trace

The **Koru Drive DSL** is a one-line-per-step textual description of what
the autopilot plugin (`koru-autopilot-cursor`, `koru-autopilot-vscode`,
etc.) did during a single `chat.send`/`chat.send_with_verification`
drive. It exists because the previous logs (`autopilot: failed (autopilot
daemon unreachable: timed out)`, `drive wynik: ok=False backend=None`)
hid the actual decisions inside opaque ack fields — so when Cursor
"wkleil prompt do okna chat ale nie wyslal", nothing in the log
explained *why* the submit candidate failed or which routes were even
tried.

The DSL is generated from the structured `operation_trace` the plugin
already sends with every ack. The daemon renders it after each drive
and writes it to the daemon log; the CLI mirrors it through
`koru.activity_log.activity("DSL", ...)` so it ends up in
`koru autonomous` output too.

## Format

One step per line:

```text
[DSL] #NNN act=<op> intent="<human readable goal>" route=<route>[:<command>] ok=<true|false|ambiguous> [reason="..."] [detail="..."]
```

The line is terminated by a Unix newline. Every field is grep-friendly:

| Field      | Meaning                                                                 |
| ---------- | ----------------------------------------------------------------------- |
| `#NNN`     | Zero-padded sequence number inside the drive (`#001`, `#002`, ...).     |
| `act`      | Operation kind from the plugin trace (`focus_open`, `paste`, `submit`). |
| `intent`   | Human-readable intent the daemon assigns from a stable lookup table.    |
| `route`    | Strategy family (`command`, `host-clipboard`, `host-key`, ...).         |
| `:command` | Concrete VS Code/Cursor command id that was invoked, when applicable.   |
| `ok`       | `true` if verified, `false` if the route refused, `ambiguous` otherwise. |
| `reason`   | Quoted free-form text explaining `ok=false`/`ambiguous`.                 |
| `detail`   | Optional small dict with `empty`, `matched`, `tail`, `rowid`, `ide`.    |

The drive's final verdict is emitted as a special `#999` line:

```text
[DSL] #999 act=drive intent="top-level autopilot drive pipeline" delivered=<true|false> verification=<probe> winners=focus=<cmd>|paste=<cmd>|submit=<cmd> [reason="..."]
```

Operator diagnosis lines are emitted after the verdict:

```text
[DSL] #900 act=diagnose severity=<ok|warning|error> code=<diagnosis> because="..."
[DSL] #901 act=next owner=<koru|operator> action="..."
[DSL] #902 act=replay shell="KORU_AUTOPILOT_INSTANCE=<ide> koru autopilot drive --ide <ide> --require-plugin --prompt-file <path>"
[DSL] #903 act=validate shell="koru autopilot trace --project <project> --format drive-dsl --limit 30"
```

`#902` is intentionally a complete copy-paste shell command. The daemon
stores the exact prompt in `.planfile/.koru/replay/<corr>.prompt`, so
the replay command does not depend on fragile shell quoting.

## Stable intent vocabulary

The daemon maps every plugin `op` to a stable intent string so different
plugin versions describe the same step the same way:

| `act` (op)         | `intent`                                                            |
| ------------------ | ------------------------------------------------------------------- |
| `focus_open`       | make the chat panel the foreground surface                          |
| `focus_input`      | land the caret inside the chat input                                |
| `input_busy_probe` | check whether the chat input is empty before pasting                |
| `paste`            | write the prompt text into the chat input                           |
| `submit`           | send the prompt as a user message                                   |
| `submit_verify`    | verify a fresh user message was actually committed                  |
| `submit_host`      | send via host-level key/click after registered commands failed     |
| `host_clipboard`   | stage the prompt via OS clipboard                                   |
| `drive`            | top-level autopilot drive pipeline                                  |

Unknown ops appear as `intent="plugin-internal step '<op>'"`.

## Example trace

A failed drive on Cursor where paste succeeded but submit was rejected
by `composer.sendToAgent` (no fresh `type=1` bubble) and then by
`composer.acceptComposerStep` (`executeCommand` returned `false`):

```text
[DSL] #001 act=focus_open intent="make the chat panel the foreground surface" route=command:composer.openComposer ok=true
[DSL] #002 act=focus_input intent="land the caret inside the chat input" route=command:composer.focusComposer ok=true
[DSL] #003 act=input_busy_probe intent="check whether the chat input is empty before pasting" route=select-copy ok=true detail="{'empty': True}"
[DSL] #004 act=paste intent="write the prompt text into the chat input" route=command:editor.action.clipboardPasteAction ok=true
[DSL] #005 act=submit intent="send the prompt as a user message" route=command:composer.sendToAgent ok=ambiguous reason="no fresh type=1 bubble after 2.5s"
[DSL] #006 act=submit intent="send the prompt as a user message" route=command:composer.acceptComposerStep ok=false reason="executeCommand returned false"
[DSL] #999 act=drive intent="top-level autopilot drive pipeline" delivered=false verification=submit_unverified winners=focus=composer.openComposer|paste=editor.action.clipboardPasteAction|submit=- reason="no fresh type=1 bubble after 2.5s"
[DSL] #900 act=diagnose severity=error code=submit_not_verified because="no fresh type=1 bubble after 2.5s"
[DSL] #901 act=next owner=operator action="do not redrive blindly; inspect replay trace and retry after submit strategy fix"
[DSL] #902 act=replay shell="KORU_AUTOPILOT_INSTANCE=cursor koru autopilot drive --ide cursor --require-plugin --prompt-file /repo/.planfile/.koru/replay/cli-drive.prompt"
[DSL] #903 act=validate shell="koru autopilot trace --project /repo --format drive-dsl --limit 30"
```

A successful drive on the same IDE looks like:

```text
[DSL] #001 act=focus_open intent="make the chat panel the foreground surface" route=command:composer.openComposer ok=true
[DSL] #002 act=paste intent="write the prompt text into the chat input" route=command:editor.action.clipboardPasteAction ok=true
[DSL] #003 act=submit intent="send the prompt as a user message" route=command:composer.sendToAgent ok=true
[DSL] #999 act=drive intent="top-level autopilot drive pipeline" delivered=true verification=cursorDiskKV_bubble winners=focus=composer.openComposer|paste=editor.action.clipboardPasteAction|submit=composer.sendToAgent
[DSL] #900 act=diagnose severity=ok code=submit_verified because="plugin ack carried required focus/paste/submit proofs"
[DSL] #901 act=next owner=koru action="wait for IDE/LLM response or ticket state transition"
```

## How to consume it

- **Operator (live)**: `koru auto` prints `[DSL]` lines inline with the
  rest of the autonomous loop output.
- **Operator (postmortem)**: grep the daemon log for `[DSL]` to see the
  full ladder of every drive in a session:

  ```bash
  rg '\[DSL\]' /tmp/koru-autopilot-cursor.log | less -SR
  ```

- **Operator (last drive DSL)**: print the persisted recent drive trace:

  ```bash
  koru autopilot trace --format drive-dsl --limit 30
  ```

- **Dashboard / autonomous**: the relayed ack envelope now carries
  `drive_dsl: string[]`, `drive_dsl_outcome: string`, and
  `drive_dsl_operator: string[]`. Any consumer that already inspects
  `verification` / `winning_*` can also read these fields without further
  parsing.

## Tuning the drive timeout

Cursor's worst-case ladder (focus_open + input_busy_probe + paste +
submit + bubble-DB verification) can legitimately take 15-25 seconds.
The CLI used to give up after 8 s with
`autopilot: failed (autopilot daemon unreachable: timed out)` even when
the plugin was *still working* and would have produced a real ack with
useful DSL lines a few seconds later.

The current default is **45 s**. Override per-shell with:

```bash
export KORU_AUTOPILOT_DRIVE_TIMEOUT_SECONDS=60
koru auto
```

A late ack that arrives after the CLI has already given up is still
logged on the daemon side (with full `[DSL]` lines), so even a
timed-out drive leaves a transparent record of what was tried.
