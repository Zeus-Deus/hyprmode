#!/usr/bin/python3
# this is to make sure default python runs instead of a conda env

"""
hyprmode - Display Mode Switcher for Hyprland
Phase 2: Interactive menu with display mode switching
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from textual.app import App
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option


def get_monitors() -> dict:
    """
    Execute hyprctl monitors -j and parse monitor data.
    Also gets disabled monitors from hyprctl monitors all -j
    Returns: {
        'laptop': {'name': 'eDP-1', 'width': 1920, 'height': 1080, 'refreshRate': 60.0} or None,
        'external': {'name': 'HDMI-A-1', 'width': 2560, 'height': 1440, 'refreshRate': 144.0} or None
    }
    """
    try:
        # Try to get all monitors (including disabled)
        result = subprocess.run(
            ["hyprctl", "monitors", "all", "-j"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        monitors_data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired):
        # Fallback to regular monitors command (only active monitors)
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
            'refreshRate': monitor.get('refreshRate', 0.0),
            'scale': monitor.get('scale', 1.0),
            'disabled': monitor.get('disabled', False)
        }
        
        # Identify laptop monitor (contains "eDP")
        if "eDP" in monitor_info['name']:
            laptop = monitor_info
        else:
            # Only set external if it's the first one we find
            if external is None:
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


def send_notification(message: str, urgent: bool = False) -> None:
    """Send desktop notification using notify-send"""
    try:
        cmd = ["notify-send", "HyprMode", message]
        if urgent:
            cmd.insert(1, "-u")
            cmd.insert(2, "critical")
        subprocess.run(cmd, check=False, timeout=2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # notify-send not available or timed out - continue silently
        pass


def clear_mirror_state(laptop: Optional[dict], external: Optional[dict]) -> dict:
    """
    Clear any existing mirror relationship and restore native monitor specs.
    Returns refreshed monitor data after reload.
    """
    try:
        # Disable both monitors to clear mirror state
        if external:
            subprocess.run(
                ["hyprctl", "keyword", "monitor", f"{external['name']},disable"],
                timeout=5,
                stderr=subprocess.DEVNULL
            )
        
        if laptop:
            subprocess.run(
                ["hyprctl", "keyword", "monitor", f"{laptop['name']},disable"],
                timeout=5,
                stderr=subprocess.DEVNULL
            )
        
        # Small delay for state to settle
        import time
        time.sleep(0.3)
        
        # CRITICAL: Reload Hyprland config to restore native monitor settings
        subprocess.run(
            ["hyprctl", "reload"],
            timeout=5,
            stderr=subprocess.DEVNULL
        )
        
        # Small delay for reload to complete
        time.sleep(0.3)
        
        # RE-DETECT monitors to get the restored native specs
        return get_monitors()
    
    except Exception:
        # If error, return original values
        return {'laptop': laptop, 'external': external}


def apply_laptop_only(laptop: Optional[dict], external: Optional[dict]) -> None:
    """Disable external, enable laptop"""
    if not laptop:
        raise RuntimeError("Laptop monitor not detected - cannot enable")
    
    # Clear mirror state and get refreshed monitor specs
    monitors = clear_mirror_state(laptop, external)
    laptop = monitors['laptop']
    external = monitors['external']
    
    try:
        # Enable laptop with REFRESHED settings (native resolution restored!)
        laptop_config = f"{laptop['name']},{laptop['width']}x{laptop['height']}@{laptop['refreshRate']:.0f},auto,{laptop['scale']}"
        subprocess.run(
            ["hyprctl", "keyword", "monitor", laptop_config],
            check=True,
            timeout=5
        )
        # Disable external if it exists
        if external:
            subprocess.run(
                ["hyprctl", "keyword", "monitor", f"{external['name']},disable"],
                check=True,
                timeout=5
            )
        send_notification("Switched to Laptop Only mode")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to apply laptop only mode: {e}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command timed out while applying mode")


def apply_external_only(laptop: Optional[dict], external: dict) -> None:
    """Disable laptop, enable external"""
    if not external:
        raise RuntimeError("External monitor not detected - cannot enable")
    
    # Clear mirror state and get refreshed monitor specs
    monitors = clear_mirror_state(laptop, external)
    laptop = monitors['laptop']
    external = monitors['external']
    
    try:
        # Enable external with actual settings
        external_config = f"{external['name']},{external['width']}x{external['height']}@{external['refreshRate']:.0f},auto,{external['scale']}"
        subprocess.run(
            ["hyprctl", "keyword", "monitor", external_config],
            check=True,
            timeout=5
        )
        # Disable laptop if it exists (might be None on desktop)
        if laptop:
            subprocess.run(
                ["hyprctl", "keyword", "monitor", f"{laptop['name']},disable"],
                check=True,
                timeout=5
            )
        send_notification("Switched to External Only mode")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to apply external only mode: {e}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command timed out while applying mode")


def apply_extend(laptop: Optional[dict], external: dict) -> None:
    """Enable both, position external to the right"""
    if not laptop:
        raise RuntimeError("Laptop monitor not detected - cannot enable")
    if not external:
        raise RuntimeError("External monitor not detected - cannot extend")
    
    # Clear mirror state and get refreshed monitor specs
    monitors = clear_mirror_state(laptop, external)
    laptop = monitors['laptop']
    external = monitors['external']
    
    try:
        # Enable laptop at 0x0 with actual settings
        laptop_config = f"{laptop['name']},{laptop['width']}x{laptop['height']}@{laptop['refreshRate']:.0f},0x0,{laptop['scale']}"
        subprocess.run(
            ["hyprctl", "keyword", "monitor", laptop_config],
            check=True,
            timeout=5
        )
        # Enable external to the right with actual settings
        external_config = f"{external['name']},{external['width']}x{external['height']}@{external['refreshRate']:.0f},auto-right,{external['scale']}"
        subprocess.run(
            ["hyprctl", "keyword", "monitor", external_config],
            check=True,
            timeout=5
        )
        send_notification("Switched to Extend mode")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to apply extend mode: {e}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command timed out while applying mode")


def apply_mirror(laptop: Optional[dict], external: dict) -> None:
    """Enable both displays with same content (mirror mode)"""
    if not laptop:
        raise RuntimeError("Laptop monitor not detected - cannot enable")
    if not external:
        raise RuntimeError("External monitor not detected - cannot mirror")
    
    # Clear any existing mirror state and get refreshed monitor specs
    monitors = clear_mirror_state(laptop, external)
    laptop = monitors['laptop']
    external = monitors['external']
    
    try:
        import time
        
        # Use EXTERNAL's native resolution/refresh rate (what it can actually support)
        # This prevents forcing incompatible specs on the external monitor
        mirror_width = external['width']
        mirror_height = external['height']
        mirror_refresh = external['refreshRate']
        
        # Step 1: Configure laptop to output at external's resolution
        # Laptop will downscale its content to match external
        laptop_config = f"{laptop['name']},{mirror_width}x{mirror_height}@{mirror_refresh:.0f},0x0,{laptop['scale']}"
        subprocess.run(
            ["hyprctl", "keyword", "monitor", laptop_config],
            check=True,
            timeout=5
        )
        
        # Step 2: Wait for laptop to stabilize
        time.sleep(0.3)
        
        # Step 3: Configure external to mirror laptop at its native resolution
        external_config = f"{external['name']},{mirror_width}x{mirror_height}@{mirror_refresh:.0f},0x0,{external['scale']},mirror,{laptop['name']}"
        subprocess.run(
            ["hyprctl", "keyword", "monitor", external_config],
            check=True,
            timeout=5
        )
        
        send_notification(f"Mirror mode applied - using {mirror_width}x{mirror_height}@{mirror_refresh:.0f}Hz")
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to apply mirror mode: {e}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command timed out while applying mode")


class HyprModeApp(App):
    """Hyprland display mode switcher TUI"""
    
    TITLE = "HyprMode"
    
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
    
    OptionList {
        margin: 1 0;
        height: auto;
        min-height: 8;
    }
    
    .title {
        text-style: bold;
        color: $accent;
    }
    
    .error {
        color: $error;
    }
    
    .help {
        color: $text-muted;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]
    
    def __init__(self):
        super().__init__()
        try:
            self.monitors = get_monitors()
            self.lid_state = get_lid_state()
            self.error = None
        except RuntimeError as e:
            self.monitors = None
            self.lid_state = "unknown"
            self.error = str(e)
    
    def compose(self):
        """Display monitor info and interactive menu"""
        with Container():
            if self.error:
                yield Static("❌ HyprMode - Error", classes="title error")
                yield Static("")
                yield Static(self.error, classes="error")
                yield Static("")
                yield Static("Press 'q' to quit", classes="help")
            else:
                yield Static("🖥️  HyprMode - Display Mode Switcher", classes="title")
                yield Static("")
                yield Static(f"Lid State: {self.lid_state.upper()}")
                
                if self.monitors['laptop']:
                    laptop = self.monitors['laptop']
                    yield Static(
                        f"Laptop: {laptop['name']} "
                        f"({laptop['width']}x{laptop['height']}@{laptop['refreshRate']:.0f}Hz)"
                    )
                
                if self.monitors['external']:
                    external = self.monitors['external']
                    yield Static(
                        f"External: {external['name']} "
                        f"({external['width']}x{external['height']}@{external['refreshRate']:.0f}Hz)"
                    )
                else:
                    yield Static("External: None")
                
                yield Static("")
                yield Static("Select Display Mode:", classes="title")
                yield OptionList(
                    Option("💻 Laptop Only", id="laptop"),
                    Option("🖥️  External Only", id="external"),
                    Option("↔️  Extend", id="extend"),
                    Option("🔄 Mirror", id="mirror")
                )
                yield Static("")
                yield Static("j/k: navigate  |  Enter: apply  |  q: quit", classes="help")
    
    def action_cursor_down(self) -> None:
        """Move cursor down in option list"""
        option_list = self.query_one(OptionList)
        option_list.action_cursor_down()
    
    def action_cursor_up(self) -> None:
        """Move cursor up in option list"""
        option_list = self.query_one(OptionList)
        option_list.action_cursor_up()
    
    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle mode selection"""
        if self.error or not self.monitors:
            return
        
        mode = event.option.id
        laptop = self.monitors['laptop']
        external = self.monitors['external']
        
        try:
            if mode == "laptop":
                if not laptop:
                    send_notification("Laptop display not detected. Try: hyprctl keyword monitor 'eDP-2,preferred,auto,1'", urgent=True)
                    return
                apply_laptop_only(laptop, external)
                self.exit()
            elif mode == "external":
                if not external:
                    send_notification("No external monitor detected", urgent=True)
                    return
                apply_external_only(laptop, external)
                self.exit()
            elif mode == "extend":
                if not laptop:
                    send_notification("Laptop display not detected. Try: hyprctl keyword monitor 'eDP-2,preferred,auto,1'", urgent=True)
                    return
                if not external:
                    send_notification("No external monitor detected", urgent=True)
                    return
                apply_extend(laptop, external)
                self.exit()
            elif mode == "mirror":
                if not laptop:
                    send_notification("Laptop display not detected. Try: hyprctl keyword monitor 'eDP-2,preferred,auto,1'", urgent=True)
                    return
                if not external:
                    send_notification("No external monitor detected", urgent=True)
                    return
                apply_mirror(laptop, external)
                self.exit()
        except RuntimeError as e:
            send_notification(str(e), urgent=True)
            # Don't exit on validation errors - let user try another mode


if __name__ == "__main__":
    app = HyprModeApp()
    app.run()

