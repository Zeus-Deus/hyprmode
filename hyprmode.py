#!/usr/bin/env python3
"""
hyprmode - Display Mode Switcher for Hyprland
Phase 1: Monitor detection, lid state detection, and basic TUI display
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from textual.app import App
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Static


def get_monitors() -> dict:
    """
    Execute hyprctl monitors -j and parse monitor data.
    Returns: {
        'laptop': {'name': 'eDP-1', 'width': 1920, 'height': 1080, 'refreshRate': 60.0},
        'external': {'name': 'HDMI-A-1', 'width': 2560, 'height': 1440, 'refreshRate': 144.0} or None
    }
    """
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        monitors_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to execute hyprctl: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse hyprctl output: {e}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("hyprctl command timed out")
    except FileNotFoundError:
        raise RuntimeError("hyprctl not found - is Hyprland running?")
    
    if not monitors_data:
        raise RuntimeError("No monitors detected")
    
    laptop: Optional[dict] = None
    external: Optional[dict] = None
    
    for monitor in monitors_data:
        monitor_info = {
            'name': monitor.get('name', 'Unknown'),
            'width': monitor.get('width', 0),
            'height': monitor.get('height', 0),
            'refreshRate': monitor.get('refreshRate', 0.0)
        }
        
        # Identify laptop monitor (contains "eDP")
        if "eDP" in monitor_info['name']:
            laptop = monitor_info
        else:
            external = monitor_info
    
    return {
        'laptop': laptop,
        'external': external
    }


def get_lid_state() -> str:
    """
    Check laptop lid state from /proc/acpi/button/lid/
    Returns: 'open', 'closed', or 'unknown'
    """
    lid_paths = [
        Path("/proc/acpi/button/lid/LID/state"),
        Path("/proc/acpi/button/lid/LID0/state")
    ]
    
    for lid_path in lid_paths:
        try:
            content = lid_path.read_text()
            if "closed" in content.lower():
                return "closed"
            elif "open" in content.lower():
                return "open"
        except FileNotFoundError:
            continue
        except Exception as e:
            # Other errors (permissions, etc.) - try next path
            continue
    
    # No lid file found - likely a desktop
    return "unknown"


class HyprModeApp(App):
    """Hyprland display mode switcher TUI"""
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    Container {
        min-width: 60;
        max-width: 80;
        height: auto;
        padding: 2 4;
        border: solid $accent;
    }
    
    Static {
        margin: 1 0;
        min-width: 50;
    }
    
    .title {
        text-style: bold;
        color: $accent;
    }
    
    .error {
        color: $error;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]
    
    def compose(self):
        """Display detected monitors and lid state"""
        try:
            monitors = get_monitors()
            lid_state = get_lid_state()
            
            with Container():
                yield Static("🖥️  HyprMode - Display Detection", classes="title")
                yield Static("")
                yield Static(f"Lid State: {lid_state.upper()}")
                yield Static("")
                
                if monitors['laptop']:
                    laptop = monitors['laptop']
                    yield Static(
                        f"Laptop: {laptop['name']} "
                        f"({laptop['width']}x{laptop['height']}@{laptop['refreshRate']:.0f}Hz)"
                    )
                
                if monitors['external']:
                    external = monitors['external']
                    yield Static(
                        f"External: {external['name']} "
                        f"({external['width']}x{external['height']}@{external['refreshRate']:.0f}Hz)"
                    )
                else:
                    yield Static("No external monitor detected")
                
                yield Static("")
                yield Static("Press 'q' to quit", classes="dim")
                
        except RuntimeError as e:
            with Container():
                yield Static("❌ Error", classes="title error")
                yield Static("")
                yield Static(str(e), classes="error")
                yield Static("")
                yield Static("Press 'q' to quit", classes="dim")


if __name__ == "__main__":
    app = HyprModeApp()
    app.run()

