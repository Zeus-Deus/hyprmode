#!/usr/bin/env python3
"""
hyprmode-daemon - Automatic display mode switching based on lid state
Runs in background and monitors lid state changes
"""

import subprocess
import time
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from hyprmode import (
    get_lid_state,
    get_monitors,
    apply_laptop_only,
    apply_external_only,
    apply_extend,
    send_notification
)


def handle_lid_change(lid_state: str) -> None:
    """Handle lid state change and apply appropriate mode"""
    try:
        monitors = get_monitors()
        laptop = monitors['laptop']
        external = monitors['external']
        
        if lid_state == "closed":
            if external:
                # Lid closed with external - use external only
                apply_external_only(laptop, external)
                send_notification("Lid closed - switched to external display")
            # If no external, do nothing (let system sleep)
        
        elif lid_state == "open":
            if external:
                # Lid opened with external - extend mode
                if laptop:
                    apply_extend(laptop, external)
                    send_notification("Lid opened - extended display")
            else:
                # Lid opened without external - laptop only
                if laptop:
                    apply_laptop_only(laptop, external)
                    send_notification("Lid opened - laptop display active")
    
    except Exception as e:
        # Don't crash daemon on errors - just notify
        send_notification(f"Display mode switch failed: {e}", urgent=True)


def get_monitor_count() -> tuple[int, bool]:
    """
    Get count of connected monitors and check if laptop is disabled.
    Returns: (total_monitor_count, laptop_is_disabled)
    """
    try:
        monitors = get_monitors()
        laptop = monitors.get('laptop')
        external = monitors.get('external')
        
        # Count active monitors
        count = 0
        if laptop and not laptop.get('disabled', False):
            count += 1
        if external and not external.get('disabled', False):
            count += 1
        
        laptop_disabled = laptop and laptop.get('disabled', False)
        
        return (count, laptop_disabled)
    except Exception:
        return (0, False)


def emergency_enable_laptop() -> None:
    """
    Emergency recovery: re-enable laptop screen when no displays are active.
    Prevents complete blackout when external monitor unplugged in External Only mode.
    """
    try:
        monitors = get_monitors()
        laptop = monitors.get('laptop')
        
        if not laptop:
            return
        
        # Force enable laptop screen with its settings
        laptop_config = f"{laptop['name']},{laptop['width']}x{laptop['height']}@{laptop['refreshRate']:.0f},auto,{laptop['scale']}"
        
        subprocess.run(
            ["hyprctl", "keyword", "monitor", laptop_config],
            check=True,
            timeout=5
        )
        
        send_notification("External monitor disconnected - laptop screen re-enabled", urgent=True)
    
    except Exception as e:
        # Last resort - use generic enable command for common laptop display names
        try:
            subprocess.run(
                ["hyprctl", "keyword", "monitor", "eDP-1,preferred,auto,1"],
                timeout=5
            )
            subprocess.run(
                ["hyprctl", "keyword", "monitor", "eDP-2,preferred,auto,1"],
                timeout=5
            )
        except Exception:
            pass


def monitor_lid_state() -> None:
    """Continuously monitor lid state changes and monitor hotplug"""
    previous_state = get_lid_state()
    previous_monitor_count, previous_laptop_disabled = get_monitor_count()
    
    while True:
        try:
            current_state = get_lid_state()
            current_monitor_count, current_laptop_disabled = get_monitor_count()
            
            # Check for lid state change
            if current_state != previous_state and current_state != "unknown":
                handle_lid_change(current_state)
                previous_state = current_state
            
            # CRITICAL: Check for external monitor disconnect while laptop disabled
            if (previous_laptop_disabled and 
                current_laptop_disabled and 
                current_monitor_count == 0):
                # Laptop disabled AND no monitors active = emergency recovery
                emergency_enable_laptop()
            
            # Update tracking
            previous_monitor_count = current_monitor_count
            previous_laptop_disabled = current_laptop_disabled
            
            time.sleep(1)  # Check every second
        
        except KeyboardInterrupt:
            send_notification("HyprMode daemon stopped")
            break
        except Exception as e:
            # Log error but keep daemon running
            send_notification(f"Daemon error: {e}", urgent=True)
            time.sleep(5)  # Wait longer on error


if __name__ == "__main__":
    send_notification("HyprMode daemon started - monitoring lid state")
    monitor_lid_state()

