from __future__ import annotations

import subprocess
from importlib import metadata

from coru import cli as coru_cli


def test_heuristic_plan_auto() -> None:
    plan = coru_cli._heuristic_plan("run auto for windsurf-main in windsurf")
    assert plan.action == "auto"
    assert plan.ide == "windsurf"


def test_execute_text_uses_heuristic(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_lane_status(ide: str, instance: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)
    rc = coru_cli.main(["text", "status for cursor-main in cursor"])

    assert rc == 0
    assert called["ide"] == "cursor"


def test_ensure_without_install_missing(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_cmd_exists", lambda _name: False)
    monkeypatch.setattr(coru_cli, "_python_module_exists", lambda _name: False)
    rc = coru_cli.main(["ensure"])
    assert rc == 1


def test_ensure_with_install_calls_pip(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_exists(name: str) -> bool:
        return name == "koru"

    def fake_run(cmd, check):
        called["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(coru_cli, "_cmd_exists", fake_exists)
    monkeypatch.setattr(coru_cli, "_python_module_exists", lambda _name: False)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: None)
    monkeypatch.setattr(coru_cli.subprocess, "run", fake_run)

    rc = coru_cli.main(["ensure", "--install"])
    assert rc == 0
    assert called["cmd"][0:4] == [coru_cli.sys.executable, "-m", "pip", "install"]


def test_ensure_with_install_prefers_project_venv_python(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_exists(name: str) -> bool:
        return name == "koru"

    def fake_run(cmd, check):
        called["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(coru_cli, "_cmd_exists", fake_exists)
    monkeypatch.setattr(coru_cli, "_python_module_exists", lambda _name: False)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: "/tmp/repo/.venv/bin/python")
    monkeypatch.setattr(coru_cli.subprocess, "run", fake_run)

    rc = coru_cli.main(["ensure", "--install"])
    assert rc == 0
    assert called["cmd"][0:4] == ["/tmp/repo/.venv/bin/python", "-m", "pip", "install"]


def test_setup_runs_environment_prepare(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_ensure_commands", lambda install: 0)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: "/tmp/repo/.venv/bin/python")
    rc = coru_cli.main(["setup"])
    assert rc == 0


def test_distribution_version_not_installed(monkeypatch) -> None:
    def fake_version(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(coru_cli.metadata, "version", fake_version)
    assert coru_cli._distribution_version("missing-pkg") == "not-installed"


def test_print_runtime_versions(monkeypatch, capsys) -> None:
    monkeypatch.setattr(coru_cli, "_distribution_version", lambda name: "0.1.0" if name == "coru" else "0.1.308")
    coru_cli._print_runtime_versions()
    out = capsys.readouterr().out.strip()
    assert out == "versions: coru=0.1.0 koru=0.1.308"


def test_version_flag_prints_and_exits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(coru_cli, "_distribution_version", lambda name: "0.1.0" if name == "coru" else "0.1.308")
    rc = coru_cli.main(["-V"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "versions: coru=0.1.0 koru=0.1.308"


def test_verbose_no_args_enters_chat_verbose(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_chat_loop(*, use_llm: bool, shell: str, single_action: bool, verbose: bool = False) -> int:
        called["use_llm"] = use_llm
        called["shell"] = shell
        called["single_action"] = single_action
        called["verbose"] = verbose
        return 0

    monkeypatch.setattr(coru_cli, "_chat_loop", fake_chat_loop)
    rc = coru_cli.main(["--verbose"])
    assert rc == 0
    assert called == {"use_llm": False, "shell": "bash", "single_action": False, "verbose": True}


def test_local_install_target_koruenv() -> None:
    target = coru_cli._local_install_target("koruenv")
    assert target is not None
    assert target.endswith("/packages/koruenv")


def test_build_plan_chain_for_auto_intent() -> None:
    plans = coru_cli._build_plan_chain("run auto for cursor-main in cursor")
    assert [p.action for p in plans] == ["ensure", "lane", "status", "auto"]


def test_build_plan_chain_for_polish_refactor_intent() -> None:
    plans = coru_cli._build_plan_chain("start refaktoryzacje")
    assert [p.action for p in plans] == ["ensure", "lane", "status", "auto"]


def test_text_executes_chain(monkeypatch) -> None:
    called: list[str] = []

    def fake_execute(plans, **_kwargs):
        called.extend([p.action for p in plans])
        return 0

    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute)
    rc = coru_cli.main(["text", "start auto for windsurf-main in windsurf"])
    assert rc == 0
    assert called == ["ensure", "lane", "status", "auto"]


def test_main_shorthand_routes_to_text(monkeypatch) -> None:
    called: list[str] = []

    def fake_execute(plans, **_kwargs):
        called.extend([p.action for p in plans])
        return 0

    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute)
    rc = coru_cli.main(["run", "auto", "for", "cursor-main", "in", "cursor"])
    assert rc == 0
    assert called == ["ensure", "lane", "status", "auto"]


def test_auto_without_lane_uses_defaults(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["extra_args"] = list(extra_args)
        return 0

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.delenv("CHROME_DESKTOP", raising=False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)
    rc = coru_cli.main(["auto"])
    assert rc == 0
    assert called["ide"] == "auto"
    assert called["instance"] == "main"
    assert called["extra_args"] == []


def test_auto_without_lane_uses_terminal_hint(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setenv("CURSOR_AGENT", "1")
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)
    rc = coru_cli.main(["auto"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main"}


def test_polish_refactor_defaults_without_windsurf(monkeypatch) -> None:
    resolved: list[tuple[str, str, str]] = []

    def fake_execute(plans, **_kwargs):
        for plan in plans:
            resolved_plan = coru_cli._resolve_defaults(plan)
            resolved.append((resolved_plan.action, resolved_plan.ide, resolved_plan.instance))
        return 0

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)
    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute)
    rc = coru_cli.main(["text", "start refaktoryzacje"])
    assert rc == 0
    assert resolved[-1] == ("auto", "auto", "main")


def test_lane_status_defaults_can_use_env(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_lane_status(ide: str, instance: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor-main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)
    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)

    rc = coru_cli.main(["lane-status"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main"}


def test_terminal_hint_overrides_stale_env_ide(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_lane_status(ide: str, instance: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "windsurf")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "windsurf-main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)

    rc = coru_cli.main(["status"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main"}


def test_stale_instance_not_reused_for_different_ide(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "windsurf-main")
    assert coru_cli._infer_default_instance(ide="cursor") == "cursor-main"


def test_generic_main_not_reused_when_ide_auto(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    assert coru_cli._infer_default_instance(ide="auto") == "jetbrains-main"


def test_terminal_ide_hint_jetbrains_from_emulator(monkeypatch) -> None:
    monkeypatch.setenv("TERMINAL_EMULATOR", "JetBrains-JediTerm")
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.delenv("WINDSURF_CASCADE_TERMINAL", raising=False)
    monkeypatch.delenv("CHROME_DESKTOP", raising=False)
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    assert coru_cli._terminal_ide_hint() == "jetbrains"


def test_warns_when_stale_main_lane_overridden(monkeypatch, capsys) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    coru_cli._resolve_defaults(coru_cli.Plan(action="status"))
    err = capsys.readouterr().err
    assert "stale lane overridden: main -> jetbrains-main" in err


def test_warns_only_once_per_chat_context(monkeypatch, capsys) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    ctx = coru_cli.SessionContext()
    coru_cli._resolve_defaults(coru_cli.Plan(action="status"), context=ctx)
    coru_cli._resolve_defaults(coru_cli.Plan(action="auto"), context=ctx)
    err_lines = [line for line in capsys.readouterr().err.splitlines() if "stale lane overridden" in line]
    assert len(err_lines) == 1


def test_no_args_starts_chat(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_chat_loop(*, use_llm: bool, shell: str, single_action: bool, verbose: bool = False) -> int:
        called["use_llm"] = use_llm
        called["shell"] = shell
        called["single_action"] = single_action
        called["verbose"] = verbose
        return 0

    monkeypatch.setattr(coru_cli, "_chat_loop", fake_chat_loop)
    rc = coru_cli.main([])
    assert rc == 0
    assert called == {"use_llm": False, "shell": "bash", "single_action": False, "verbose": False}


def test_status_alias_routes_to_lane_status(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_lane_status(ide: str, instance: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)
    rc = coru_cli.main(["status", "cursor", "cursor-main"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main"}


def test_status_failure_continues_to_auto_for_refactor(monkeypatch) -> None:
    called: list[str] = []

    def fake_ensure(install: bool) -> int:
        called.append("ensure")
        return 0

    def fake_lane_env(ide: str, instance: str, shell: str) -> int:
        called.append("lane")
        return 0

    def fake_lane_status(ide: str, instance: str) -> int:
        called.append("status")
        return 1

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called.append("auto")
        return 0

    monkeypatch.setattr(coru_cli, "_ensure_commands", fake_ensure)
    monkeypatch.setattr(coru_cli, "_lane_env", fake_lane_env)
    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)

    rc = coru_cli.main(["text", "refaktoryzuj"])
    assert rc == 0
    assert called == ["ensure", "lane", "status", "auto"]


def test_chat_refaktoryzuj_continues_past_status_when_daemon_down(monkeypatch) -> None:
    called: dict[str, str] = {}
    inputs = iter(["refaktoryzuj", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main", "prompt": "refaktoryzuj"}


def test_chat_uses_llm_rewrite_when_configured(monkeypatch) -> None:
    called: dict[str, str] = {}
    inputs = iter(["zrob refakotryzacje", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: True)
    monkeypatch.setattr(coru_cli, "_llm_rewrite_chat_prompt", lambda text, **_k: f"IDE PROMPT: {text}")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == {
        "ide": "jetbrains",
        "instance": "jetbrains-main",
        "prompt": "IDE PROMPT: zrob refakotryzacje",
    }


def test_chat_slash_command_executes_coru_actions(monkeypatch) -> None:
    called: list[str] = []
    inputs = iter(["/refaktoryzuj", "quit"])

    def fake_ensure(install: bool) -> int:
        called.append("ensure")
        return 0

    def fake_lane_env(ide: str, instance: str, shell: str) -> int:
        called.append("lane")
        return 0

    def fake_lane_status(ide: str, instance: str) -> int:
        called.append("status")
        return 1

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called.append("auto")
        return 0

    monkeypatch.setattr(coru_cli, "_ensure_commands", fake_ensure)
    monkeypatch.setattr(coru_cli, "_lane_env", fake_lane_env)
    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == ["ensure", "lane", "status", "auto"]


def test_status_failure_stops_without_auto_chain(monkeypatch) -> None:
    def fake_lane_status(ide: str, instance: str) -> int:
        return 1

    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)
    rc = coru_cli.main(["text", "status for cursor-main in cursor"])
    assert rc == 1


def test_build_plan_chain_refaktoryzuj() -> None:
    plans = coru_cli._build_plan_chain("refaktoryzuj")
    assert [p.action for p in plans] == ["ensure", "lane", "status", "auto"]


def test_heuristic_plan_refakotryzuj_typo() -> None:
    plan = coru_cli._heuristic_plan("refakotryzuj")
    assert plan.action == "auto"


def test_build_plan_chain_refakotryzuj_typo() -> None:
    plans = coru_cli._build_plan_chain("refakotryzuj")
    assert [p.action for p in plans] == ["ensure", "lane", "status", "auto"]


def test_status_failure_continues_to_auto_for_refakotryzuj_typo(monkeypatch) -> None:
    called: list[str] = []

    def fake_ensure(install: bool) -> int:
        called.append("ensure")
        return 0

    def fake_lane_env(ide: str, instance: str, shell: str) -> int:
        called.append("lane")
        return 0

    def fake_lane_status(ide: str, instance: str) -> int:
        called.append("status")
        return 1

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called.append("auto")
        return 0

    monkeypatch.setattr(coru_cli, "_ensure_commands", fake_ensure)
    monkeypatch.setattr(coru_cli, "_lane_env", fake_lane_env)
    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)

    rc = coru_cli.main(["text", "refakotryzuj"])
    assert rc == 0
    assert called == ["ensure", "lane", "status", "auto"]


def test_chat_refakotryzuj_typo_continues_past_status(monkeypatch) -> None:
    called: dict[str, str] = {}
    inputs = iter(["refakotryzuj", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main", "prompt": "refakotryzuj"}


def test_env_alias_routes_to_lane(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_lane_env(ide: str, instance: str, shell: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["shell"] = shell
        return 0

    monkeypatch.setattr(coru_cli, "_lane_env", fake_lane_env)
    rc = coru_cli.main(["env", "vscode", "vscode-main", "--shell", "zsh"])
    assert rc == 0
    assert called == {"ide": "vscode", "instance": "vscode-main", "shell": "zsh"}


def test_lane_chat_prompt_uses_ide_not_instance(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["koru"])

    def fake_tool_argv(binary: str, module: str, args):
        captured["binary"] = binary
        captured["module"] = module
        captured["args"] = list(args)
        return ["koruenv", *args]

    monkeypatch.setattr(coru_cli, "_tool_argv", fake_tool_argv)
    monkeypatch.setattr(coru_cli, "_run", lambda _cmd: 0)

    rc = coru_cli._lane_chat_prompt("cursor", "cursor-main", "hello")
    assert rc == 0
    assert captured["args"][0:3] == ["run", "cursor", "cursor-main"]
    assert captured["args"][5:8] == ["autopilot", "drive", "--ide"]
    assert captured["args"][8] == "cursor"
