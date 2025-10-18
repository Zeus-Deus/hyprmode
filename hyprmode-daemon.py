#!/usr/bin/env python3
"""
hyprmode-daemon - Automatic display mode switching based on lid state
Runs in background and monitors lid state changes
"""

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


def monitor_lid_state() -> None:
    """Continuously monitor lid state changes"""
    previous_state = get_lid_state()
    
    while True:
        try:
            current_state = get_lid_state()
            
            # Only act on actual state changes (and ignore "unknown" state)
            if current_state != previous_state and current_state != "unknown":
                handle_lid_change(current_state)
                previous_state = current_state
            
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

