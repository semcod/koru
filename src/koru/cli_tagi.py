"""CLI commands for Tagi integration in Koru."""

import click
from pathlib import Path
from typing import Optional

from .tagi_integration import (
    TagiChangeAnalysis,
    TagiIntegration,
    auto_commit_all_changes,
    commit_safe_changes,
)


@click.group()
def tagi():
    """Tagi integration commands for change analysis and deployment."""
    pass


def tagi_main(argv: list[str]) -> int:
    """Main entry point for koru tagi commands."""
    try:
        return tagi.main(standalone_mode=False, args=argv)
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


def _load_priorities(tagi: TagiIntegration) -> TagiChangeAnalysis:
    """Single entry point for Tagi priority analysis."""
    return tagi.analyze_priorities()


def _priorities_payload(
    priorities: TagiChangeAnalysis,
    *,
    include_risk: bool = False,
    compact: bool = False,
) -> dict:
    if compact:
        return {
            "changes": len(priorities.changes),
            "groups": len(priorities.groups),
            "priority_order": priorities.priority_order,
            "recommendations": priorities.recommendations,
        }
    payload = {
        "total_changes": len(priorities.changes),
        "total_groups": len(priorities.groups),
        "priority_order": priorities.priority_order,
        "recommendations": priorities.recommendations,
    }
    if include_risk:
        payload["risk_assessment"] = priorities.risk_assessment
    return payload


def _render_analysis_summary(
    priorities: TagiChangeAnalysis,
    title: str = "Change Analysis",
    order_label: str = "Priority Order",
) -> None:
    click.echo(f"\n📊 {title}:")
    click.echo(f"Total changes: {len(priorities.changes)}")
    click.echo(f"Total groups: {len(priorities.groups)}")
    _render_priority_order(priorities, label=order_label)
    _render_recommendations(priorities.recommendations)


def _render_status_snapshot(priorities: TagiChangeAnalysis) -> None:
    click.echo(f"📊 {len(priorities.changes)} changes detected")
    click.echo(f"📋 {len(priorities.groups)} groups found")
    if priorities.recommendations:
        click.echo(f"\n💡 Quick recommendations:")
        for rec in priorities.recommendations[:3]:
            click.echo(f"  • {rec}")


@tagi.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--format", type=click.Choice(["json", "table"]), default="table", help="Output format")
def analyze(project_path: str, format: str):
    """Analyze project changes using Tagi."""
    project = Path(project_path).resolve()

    click.echo(f"Analyzing changes in {project}...")

    tagi = TagiIntegration(project)

    if not tagi.is_available():
        click.echo("Error: Tagi not available", err=True)
        click.echo("Install tagi: pip install tagi", err=True)
        return

    priorities = _load_priorities(tagi)

    if format == "json":
        import json

        output = {"analysis": _priorities_payload(priorities, include_risk=True)}
        click.echo(json.dumps(output, indent=2))
    else:
        _render_analysis_summary(priorities)


@tagi.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--dry-run", is_flag=True, help="Preview deployment without executing")
@click.option("--format", type=click.Choice(["json", "table"]), default="table", help="Output format")
def deploy(project_path: str, dry_run: bool, format: str):
    """Deploy changes using Tagi's intelligent prioritization."""
    project = Path(project_path).resolve()

    click.echo(f"Deploying changes in {project}...")

    tagi = TagiIntegration(project)

    if not tagi.is_available():
        click.echo("Error: Tagi not available", err=True)
        click.echo("Install tagi: pip install tagi", err=True)
        return

    deployment_plan = tagi.get_deployment_plan()

    if format == "json":
        import json

        output = {"dry_run": dry_run, "deployment_plan": deployment_plan}
        click.echo(json.dumps(output, indent=2))
    else:
        priorities = _load_priorities(tagi)
        _render_deployment_plan_table(priorities, deployment_plan.get("deployment_groups", []))

    if dry_run:
        click.echo(f"\n🔍 DRY RUN - No deployment actions taken")
        return

    # Execute deployment
    if not click.confirm("\nProceed with deployment?"):
        click.echo("Deployment cancelled")
        return

    success, deployed_groups = _execute_deployment_plan(tagi, deployment_plan)
    if success:
        click.echo(f"\n✅ Deployment completed successfully")
        click.echo(f"Deployed groups: {', '.join(deployed_groups)}")
    else:
        click.echo(f"\n❌ Deployment failed")


def _render_deployment_plan_table(priorities: TagiChangeAnalysis, deployment_groups: list):
    click.echo(f"\n📊 Deployment Analysis:")
    click.echo(f"Total changes: {len(priorities.changes)}")
    click.echo(f"Total groups: {len(priorities.groups)}")
    _render_priority_order(priorities, label="Deployment Order")
    _render_deployment_groups(deployment_groups)
    _render_recommendations(priorities.recommendations)


def _render_priority_order(priorities: TagiChangeAnalysis, label: str = "Priority Order") -> None:
    if not priorities.priority_order:
        return
    click.echo(f"\n🎯 {label}:")
    for i, group in enumerate(priorities.priority_order, 1):
        risk = priorities.risk_assessment.get(group, 0.0)
        click.echo(f"  {i}. {group} (risk: {risk:.2f})")


def _render_deployment_groups(deployment_groups: list):
    if not deployment_groups:
        return
    click.echo(f"\n🚀 Deployment Groups:")
    for group in deployment_groups:
        click.echo(f"\n  {group['name'].upper()} (Priority: {group['priority']})")
        click.echo(f"  Strategy: {group['deployment_strategy']}")
        click.echo(f"  Files: {len(group['changes'])}")
        click.echo(f"  Risk score: {group['risk_score']:.2f}")


def _render_recommendations(recommendations: list):
    if not recommendations:
        return
    click.echo(f"\n💡 Recommendations:")
    for rec in recommendations:
        click.echo(f"  • {rec}")


def _execute_deployment_plan(tagi: TagiIntegration, deployment_plan: dict) -> tuple[bool, list[str]]:
    click.echo(f"\n🚀 Starting deployment...")
    deployed_groups = []
    for group in deployment_plan.get("deployment_groups", []):
        group_name = group.get("name", "")
        if not group_name:
            continue
        click.echo(f"  Deploying {group_name}...")
        if not tagi.commit_changes(group_name):
            click.echo(f"  ✗ {group_name} failed")
            return False, deployed_groups
        click.echo(f"  ✓ {group_name} deployed")
        deployed_groups.append(group_name)
    return True, deployed_groups


@tagi.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--message", help="Commit message")
@click.option("--dry-run", is_flag=True, help="Preview without committing")
@click.option("--format", type=click.Choice(["json", "table"]), default="table", help="Output format")
def auto(project_path: str, message: Optional[str], dry_run: bool, format: str):
    """Auto-commit all changes using Tagi's auto-ordering."""
    project = Path(project_path).resolve()

    click.echo(f"Auto-committing changes in {project}...")

    tagi = TagiIntegration(project)

    if not tagi.is_available():
        click.echo("Error: Tagi not available", err=True)
        click.echo("Install tagi: pip install tagi", err=True)
        return

    if dry_run:
        priorities = _load_priorities(tagi)

        if format == "json":
            import json

            output = {
                "dry_run": True,
                "analysis": _priorities_payload(priorities, compact=True),
            }
            click.echo(json.dumps(output, indent=2))
        else:
            _render_analysis_summary(
                priorities,
                title="Auto-commit Analysis",
                order_label="Commit Order",
            )

        click.echo(f"\n🔍 DRY RUN - No commits made")
        return

    # Execute auto-commit
    if not message:
        message = "Auto-commit changes via Koru"

    if not click.confirm(f"Commit all changes with message: '{message}'?"):
        click.echo("Auto-commit cancelled")
        return

    success = auto_commit_all_changes(project, message)

    if success:
        click.echo(f"\n✅ Auto-commit completed")
        click.echo(f"Message: {message}")
    else:
        click.echo(f"\n❌ Auto-commit failed")


@tagi.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--message", help="Commit message")
def safe(project_path: str, message: Optional[str]):
    """Commit only safe changes using Tagi."""
    project = Path(project_path).resolve()

    click.echo(f"Committing safe changes in {project}...")

    if not message:
        message = "Commit safe changes via Koru"

    success = commit_safe_changes(project, message)

    if success:
        click.echo(f"\n✅ Safe changes committed")
        click.echo(f"Message: {message}")
    else:
        click.echo(f"\n❌ Failed to commit safe changes")


@tagi.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
def status(project_path: str):
    """Check Tagi integration status."""
    project = Path(project_path).resolve()

    tagi = TagiIntegration(project)

    if tagi.is_available():
        click.echo(f"✅ Tagi integration available")
        _render_status_snapshot(_load_priorities(tagi))
    else:
        click.echo(f"❌ Tagi integration not available")
        click.echo(f"Install tagi: pip install tagi")
