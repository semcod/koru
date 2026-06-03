"""Tagi integration for Koru - change analysis and prioritization."""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TagiChangeAnalysis:
    """Analysis result from Tagi."""

    changes: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    priority_order: list[str]
    risk_assessment: dict[str, float]
    recommendations: list[str]


class TagiIntegration:
    """Integration with Tagi for change analysis and prioritization."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
    
    def _run_tagi_command(self, command: list[str]) -> dict[str, Any]:
        """Run tagi command and return parsed output."""
        try:
            result = subprocess.run(
                command,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Tagi command failed: {result.stderr}")
                return {}
            
            # Try to parse JSON output
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                # If not JSON, return raw output
                return {"output": result.stdout}
                
        except subprocess.TimeoutExpired:
            logger.error("Tagi command timed out")
            return {}
        except Exception as e:
            logger.error(f"Error running tagi command: {e}")
            return {}
    
    def scan_changes(self) -> list[dict[str, Any]]:
        """Scan changes using tagi scan."""
        result = self._run_tagi_command(["python", "-m", "tagi", "scan", ".", "--format", "json"])
        
        if "changes" in result:
            return result["changes"]
        elif "output" in result:
            # Parse text output if JSON not available
            return self._parse_text_scan_output(result["output"])
        
        return []
    
    def analyze_priorities(self) -> TagiChangeAnalysis:
        """Analyze change priorities using tagi."""
        # Get scan results
        changes = self.scan_changes()
        
        if not changes:
            return TagiChangeAnalysis(
                changes=[],
                groups=[],
                priority_order=[],
                risk_assessment={},
                recommendations=["No changes found"]
            )
        
        # Get grouped analysis
        groups_result = self._run_tagi_command(
            ["python", "-m", "tagi", "list-groups", ".", "--format", "json"]
        )
        groups = groups_result.get("groups", [])
        
        # Get priority analysis
        self._run_tagi_command(["python", "-m", "tagi", "safe", ".", "--format", "json"])
        
        # Build priority order based on tagi's analysis
        priority_order = []
        risk_assessment = {}
        
        # Extract priority from groups
        for group in groups:
            group_name = group.get("name", "")
            priority_order.append(group_name)
            risk_assessment[group_name] = group.get("avg_risk", 0.0)
        
        # Sort by risk (safest first)
        priority_order.sort(key=lambda x: risk_assessment.get(x, 0.0))
        
        # Generate recommendations
        recommendations = []
        
        # Check for risky changes
        risky_groups = [g for g in groups if g.get("avg_risk", 0.0) > 0.7]
        if risky_groups:
            recommendations.append(
                f"⚠️ {len(risky_groups)} high-risk groups detected - deploy with caution"
            )
        
        # Check for large changes
        large_groups = [g for g in groups if g.get("total_lines", 0) > 100]
        if large_groups:
            recommendations.append(f"📊 {len(large_groups)} large change groups detected")
        
        # Check for safe changes
        safe_groups = [g for g in groups if g.get("avg_risk", 0.0) < 0.3]
        if safe_groups:
            recommendations.append(f"✅ {len(safe_groups)} safe groups ready for deployment")
        
        if not recommendations:
            recommendations.append("✓ All changes analyzed successfully")
        
        return TagiChangeAnalysis(
            changes=changes,
            groups=groups,
            priority_order=priority_order,
            risk_assessment=risk_assessment,
            recommendations=recommendations
        )
    
    def get_deployment_plan(self) -> dict[str, Any]:
        """Get deployment plan using tagi analysis."""
        priority_report = self.analyze_priorities()
        
        # Build deployment plan
        deployment_plan = {
            "analysis": {
                "total_changes": len(priority_report.changes),
                "total_groups": len(priority_report.groups),
                "priority_order": priority_report.priority_order,
                "risk_assessment": priority_report.risk_assessment,
                "recommendations": priority_report.recommendations
            },
            "deployment_groups": [],
            "strategy": "tagi_priority"
        }
        
        # Create deployment groups based on tagi analysis
        for group_name in priority_report.priority_order:
            group = next((g for g in priority_report.groups if g.get("name") == group_name), None)
            if group:
                deployment_group = {
                    "name": group_name,
                    "changes": group.get("changes", []),
                    "priority": len(deployment_plan["deployment_groups"]) + 1,
                    "risk_score": group.get("avg_risk", 0.0),
                    "total_lines": group.get("total_lines", 0),
                    "deployment_strategy": self._get_deployment_strategy(
                        group_name,
                        group.get("avg_risk", 0.0),
                    )
                }
                deployment_plan["deployment_groups"].append(deployment_group)
        
        return deployment_plan
    
    def _get_deployment_strategy(self, group_name: str, risk_score: float) -> str:
        """Get deployment strategy based on group name and risk."""
        if risk_score > 0.7:
            return "manual_approval_required"
        elif risk_score > 0.5:
            return "incremental_deployment"
        elif "risky" in group_name.lower() or "config" in group_name.lower():
            return "careful_deployment"
        else:
            return "automated_deployment"
    
    def commit_changes(self, group_name: str, message: str | None = None) -> bool:
        """Commit changes for a specific group using tagi."""
        if not message:
            message = f"Deploy {group_name} changes via Koru"
        
        result = self._run_tagi_command([
            "python", "-m", "tagi", "send", ".", group_name, 
            "--template", "conventional", "--push"
        ])
        
        return result.get("success", False)
    
    def auto_commit_all(self, message: str | None = None) -> bool:
        """Auto-commit all changes using tagi auto."""
        if not message:
            message = "Auto-commit all changes via Koru"
        
        result = self._run_tagi_command([
            "python", "-m", "tagi", "auto", ".", 
            "--template", "conventional"
        ])
        
        return result.get("success", False)
    
    def _parse_text_scan_output(self, output: str) -> list[dict[str, Any]]:
        """Parse text output from tagi scan."""
        changes = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.strip() and not line.startswith('#'):
                # Simple parsing - assume format: file_path | type | lines | tags
                parts = line.split('|')
                if len(parts) >= 3:
                    changes.append({
                        "path": parts[0].strip(),
                        "type": parts[1].strip() if len(parts) > 1 else "unknown",
                        "lines": (
                            int(parts[2].strip())
                            if len(parts) > 2 and parts[2].strip().isdigit()
                            else 0
                        ),
                        "tags": parts[3].strip().split(',') if len(parts) > 3 else []
                    })
        
        return changes
    
    def is_available(self) -> bool:
        """Check if tagi is available."""
        try:
            result = subprocess.run(
                ["python", "-m", "tagi", "--help"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and "tagi - Git change orchestrator" in result.stdout
        except Exception:
            return False


# Integration functions for Koru workflows
def analyze_project_changes(project_path: Path) -> dict[str, Any]:
    """Analyze project changes using Tagi integration."""
    tagi = TagiIntegration(project_path)
    
    if not tagi.is_available():
        return {
            "error": "Tagi not available",
            "message": "Install tagi: pip install tagi"
        }
    
    return tagi.get_deployment_plan()


def commit_safe_changes(project_path: Path, message: str | None = None) -> bool:
    """Commit safe changes using Tagi."""
    tagi = TagiIntegration(project_path)
    
    if not tagi.is_available():
        logger.error("Tagi not available")
        return False
    
    # Get analysis
    priority_report = tagi.analyze_priorities()
    
    # Find safe groups (risk < 0.3)
    safe_groups = [
        group for group in priority_report.groups
        if group.get("avg_risk", 0.0) < 0.3
    ]
    
    if not safe_groups:
        logger.info("No safe changes to commit")
        return True
    
    # Commit each safe group
    for group in safe_groups:
        group_name = group.get("name", "")
        if group_name:
            success = tagi.commit_changes(group_name, message)
            if not success:
                logger.error(f"Failed to commit group: {group_name}")
                return False
    
    return True


def auto_commit_all_changes(project_path: Path, message: str | None = None) -> bool:
    """Auto-commit all changes using Tagi."""
    tagi = TagiIntegration(project_path)
    
    if not tagi.is_available():
        logger.error("Tagi not available")
        return False
    
    return tagi.auto_commit_all(message)
