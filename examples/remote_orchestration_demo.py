#!/usr/bin/env python3
"""Example script demonstrating multi-node remote orchestration with Koru.

This script connects to multiple remote machines in the local network running Koru
and orchestrates prompts across their active IDE instances simultaneously.
"""

import sys
from pathlib import Path

# Insert repository src path for local development import
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from koru.remote import KoruRemoteClient


def run_multi_node_orchestration():
    # Define remote nodes in your network (IP addresses or hostnames)
    REMOTE_NODES = [
        {"name": "Frontend-Dev-PC", "host": "127.0.0.1", "port": 8765},  # Local simulation
        {"name": "Backend-Server-Node", "host": "127.0.0.1", "port": 8766},  # Simulation Node 2
    ]

    print("=============================================================")
    print(" 🚀 KORU NETWORK-WIDE MULTI-NODE ORCHESTRATOR")
    print("=============================================================\n")

    for node in REMOTE_NODES:
        name = node["name"]
        host = node["host"]
        port = node["port"]
        
        print(f"📡 Connecting to {name} ({host}:{port})...")
        client = KoruRemoteClient(host=host, port=port)
        
        try:
            status = client.get_status()
            project = status.get("project", "Unknown")
            print(f"  [OK] Connected. Active Project: '{project}'")
            
            # List all detected IDEs
            ides = client.list_running_ides()
            running_names = [ide.get("id") for ide in ides if ide.get("running")]
            print(f"  [IDE] Running IDEs on host: {', '.join(running_names) if running_names else 'None'}")
            
            # List all connected plugins
            plugins = client.list_connected_plugins()
            plugin_names = [p.get("ide") for p in plugins]
            print(f"  [Autopilot] Connected active plugins: {', '.join(plugin_names) if plugin_names else 'None'}")
            
            # If there is an active connected plugin, let's drive it!
            if plugins:
                target_ide = plugins[0]["ide"]
                prompt = "Refactor and optimize aggregate error handling in active project"
                print(f"  👉 [Drive] Dispatching remote prompt to {target_ide} on {name}...")
                
                # Remote injection!
                res = client.send_drive_command(ide=target_ide, text=prompt)
                print(f"  👉 [Success] Remote drive status: {res.get('ok')}")
            else:
                print("  ⚠️ [Skip] No active autopilot plugins connected on this host.")
                
        except Exception as exc:
            print(f"  ❌ [Error] Failed to communicate with {name}: {exc}")
        print("-" * 60)


if __name__ == "__main__":
    run_multi_node_orchestration()
