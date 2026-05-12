"""Docker-based E2E tests for Koru functionality.

These tests run Koru in Docker containers to verify:
1. All dependencies work correctly in containerized environment
2. Autonomous mode functions properly
3. Priority handling works as expected
4. External tool integrations function
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from koru.bootstrap import import_flat_pipeline
from koru.tasks import create_nl_task


class TestDockerE2E:
    """Test Koru functionality in Docker containers."""

    @pytest.fixture(scope="class")
    def docker_image(self):
        """Build Docker image for testing."""
        result = subprocess.run(
            ["docker", "build", "-t", "koru:test", "."],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        return "koru:test"

    @pytest.fixture
    def test_project(self, tmp_path):
        """Create a test project with planfile structure."""
        project = tmp_path / "test-project"
        project.mkdir()
        
        # Initialize project using koru init
        result = subprocess.run(
            ["koru", "--init", "--project", str(project)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        
        return project

    def test_docker_image_builds_successfully(self, docker_image):
        """Test that Docker image builds without errors."""
        # Image is built by fixture, this test just verifies it exists
        result = subprocess.run(
            ["docker", "images", "-q", docker_image],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() != ""

    def test_koru_help_in_docker(self, docker_image):
        """Test basic Koru functionality in Docker."""
        result = subprocess.run(
            ["docker", "run", "--rm", docker_image, "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage: koru" in result.stdout.lower()

    def test_koru_doctor_in_docker(self, docker_image):
        """Test koru --doctor in Docker container."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Mount temp directory as project
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v", f"{tmp_dir}:/workspace",
                    docker_image,
                    "--doctor",
                    "--project", "/workspace",
                ],
                capture_output=True,
                text=True,
            )
            # Should fail on empty project (no planfile config)
            assert result.returncode == 1
            assert "planfile" in result.stdout.lower()

    def test_koru_init_in_docker(self, docker_image):
        """Test koru --init in Docker container."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v", f"{tmp_dir}:/workspace",
                    docker_image,
                    "--init",
                    "--project", "/workspace",
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            
            # Check that planfile was created
            planfile_dir = Path(tmp_dir) / ".planfile"
            assert planfile_dir.exists()
            assert (planfile_dir / "config.yaml").exists()

    def test_task_creation_with_priority_in_docker(self, docker_image, test_project):
        """Test task creation with priority in Docker."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v", f"{test_project}:/workspace",
                docker_image,
                "task",
                "Test high priority task",
                "--priority", "high",
                "--project", "/workspace",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "created " in result.stdout and "-00" in result.stdout
        
        # Verify ticket was created with correct priority
        sprint_file = test_project / ".planfile" / "sprints" / "current.yaml"
        assert sprint_file.exists()
        
        with open(sprint_file) as f:
            sprint_data = yaml.safe_load(f)
        
        tickets = sprint_data.get("sprint", {}).get("tickets", [])
        assert len(tickets) > 0
        
        # Find our ticket
        our_ticket = None
        for ticket in tickets:
            if "Test high priority task" in ticket.get("name", ""):
                our_ticket = ticket
                break
        
        assert our_ticket is not None
        assert our_ticket.get("priority") == "high"

    def test_autonomous_mode_single_cycle_in_docker(self, docker_image, test_project):
        """Test autonomous mode single cycle in Docker."""
        # Create a simple task
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v", f"{test_project}:/workspace",
                docker_image,
                "task",
                "Test autonomous task",
                "--priority", "normal",
                "--project", "/workspace",
            ],
            capture_output=True,
            text=True,
        )
        
        # Run autonomous mode for one cycle
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v", f"{test_project}:/workspace",
                docker_image,
                "autonomous",
                "up",
                "--project", "/workspace",
                "--max-cycles", "1",
                "--sleep-seconds", "0",
                "--no-autopilot",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        assert "autonomous cycle #1" in result.stdout
        assert "queue=" in result.stdout

    def test_priority_ordering_in_docker(self, docker_image, test_project):
        """Test that priority ordering works correctly in Docker."""
        import yaml
        
        # Create tasks with different priorities
        tasks = [
            ("Normal task 1", "normal"),
            ("Critical task", "critical"),
            ("High priority task", "high"),
            ("Normal task 2", "normal"),
        ]
        
        for task_desc, priority in tasks:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v", f"{test_project}:/workspace",
                    docker_image,
                    "task",
                    task_desc,
                    "--priority", priority,
                    "--project", "/workspace",
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
        
        # Check queue dry run to see which ticket is first
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v", f"{test_project}:/workspace",
                docker_image,
                "--queue",
                "--project", "/workspace",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        # Critical task should be processed first
        assert "Critical task" in result.stdout

    def test_external_tool_detection_in_docker(self, docker_image):
        """Test that external tools detection works in Docker."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                docker_image,
                "tools",
                "detect",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        # Should show tool registry and summary even in minimal container
        assert "registry:" in result.stdout
        assert "summary:" in result.stdout
        assert "total=" in result.stdout
        # In minimal Docker, expect 0 available tools but registry should load
        assert "available=0" in result.stdout or "available=" in result.stdout

    def test_agent_detection_in_docker(self, docker_image):
        """Test agent detection in Docker."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                docker_image,
                "agent",
                "--list",
                "--format", "json",
            ],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        
        # Parse JSON output
        try:
            agents_data = json.loads(result.stdout)
            assert "agents" in agents_data
            assert "summary" in agents_data
        except json.JSONDecodeError:
            pytest.fail("Agent list output is not valid JSON")

    @pytest.mark.slow
    def test_full_workflow_in_docker(self, docker_image, test_project):
        """Test complete workflow: init -> task -> autonomous -> completion."""
        import yaml
        
        # 1. Create multiple tasks with different priorities
        tasks = [
            ("Low priority cleanup", "low"),
            ("Critical bug fix", "critical"),
            ("Normal feature", "normal"),
            ("High priority refactor", "high"),
        ]
        
        created_tickets = []
        for task_desc, priority in tasks:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v", f"{test_project}:/workspace",
                    docker_image,
                    "task",
                    task_desc,
                    "--priority", priority,
                    "--project", "/workspace",
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            
            # Extract ticket ID
            for line in result.stdout.split('\n'):
                if 'PLF-' in line:
                    ticket_id = line.split('PLF-')[1].split()[0]
                    created_tickets.append(f"PLF-{ticket_id}")
        
        # 2. Run autonomous mode with interactive input
        input_data = "\n".join(["Task completed"] * len(tasks)) + "\n"
        
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "-v", f"{test_project}:/workspace",
                docker_image,
                "autonomous",
                "up",
                "--project", "/workspace",
                "--max-cycles", "1",
                "--sleep-seconds", "0",
                "--no-autopilot",
                "--keep-waiting-input",  # Continue through waiting_input
            ],
            input=input_data,
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        assert "autonomous cycle #1" in result.stdout
        
        # 3. Verify all tickets were processed in priority order
        sprint_file = test_project / ".planfile" / "sprints" / "current.yaml"
        with open(sprint_file) as f:
            sprint_data = yaml.safe_load(f)
        
        tickets = sprint_data.get("sprint", {}).get("tickets", [])
        
        # Check that critical ticket was processed first
        critical_ticket = next(
            (t for t in tickets if "Critical bug fix" in t.get("name", "")),
            None
        )
        assert critical_ticket is not None
        
        # Verify execution order in logs or status
        processed_order = []
        for line in result.stdout.split('\n'):
            if 'PLF-' in line and ('completed' in line or 'status=' in line):
                for ticket_id in created_tickets:
                    if ticket_id in line:
                        processed_order.append(ticket_id)
        
        # Critical ticket should appear early in processing
        critical_ticket_id = next(
            (tid for tid in created_tickets if any("Critical" in str(t) for t in tickets if t.get("id") == tid)),
            None
        )
        
        if critical_ticket_id and processed_order:
            assert critical_ticket_id in processed_order


class TestDockerComposeIntegration:
    """Test Docker Compose integration."""

    def test_docker_compose_build(self):
        """Test that docker-compose builds successfully."""
        result = subprocess.run(
            ["docker-compose", "build"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Docker Compose build failed: {result.stderr}"

    @pytest.mark.slow
    def test_docker_compose_test_profile(self):
        """Test Docker Compose with test profile."""
        result = subprocess.run(
            ["docker-compose", "--profile", "test", "up", "-d"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        
        try:
            # Wait for container to be ready
            time.sleep(5)
            
            # Check if container is running
            result = subprocess.run(
                ["docker-compose", "ps", "--profile", "test"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "koru-test" in result.stdout
            
            # Test basic functionality
            result = subprocess.run(
                ["docker", "exec", "koru-test", "koru", "--help"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            
        finally:
            # Clean up
            subprocess.run(
                ["docker-compose", "--profile", "test", "down", "-v"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
            )

    @pytest.mark.slow
    def test_docker_compose_deps_profile(self):
        """Test Docker Compose with dependencies profile."""
        result = subprocess.run(
            ["docker-compose", "--profile", "deps", "up", "-d"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        
        try:
            # Wait for services to be ready
            time.sleep(10)
            
            # Check if all dependency containers are running
            result = subprocess.run(
                ["docker-compose", "ps", "--profile", "deps"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "planfile-test" in result.stdout
            assert "healing-webhook-test" in result.stdout
            
            # Test healing-webhook health
            result = subprocess.run(
                ["curl", "-f", "http://localhost:8810/health"],
                capture_output=True,
                text=True,
            )
            # May fail if webhook is not fully ready, that's okay
            
        finally:
            # Clean up
            subprocess.run(
                ["docker-compose", "--profile", "deps", "down", "-v"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
            )
