#!/usr/bin/env python3
"""
hyprmode-daemon - Emergency laptop screen recovery

Monitors for external display disconnect and re-enables laptop screen
if user would otherwise be stuck with a black screen.
"""

import subprocess
import time
import sys
import json


def send_notification(message: str, urgent: bool = False) -> None:
    """Send desktop notification"""
    try:
        urgency = "critical" if urgent else "normal"
        subprocess.run(
            ["notify-send", "-u", urgency, "HyprMode", message],
            timeout=2
        )
    except Exception:
        pass  # Notifications are optional


def get_monitors() -> dict:
    """Get connected monitors from hyprctl"""
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        
        monitors_data = json.loads(result.stdout)
        
        laptop = None
        external = None
        
        for monitor in monitors_data:
            name = monitor['name']
            if 'eDP' in name or 'LVDS' in name or 'DSI' in name:
                laptop = monitor
            else:
                external = monitor
        
        return {'laptop': laptop, 'external': external}
    except Exception:
        return {'laptop': None, 'external': None}


def apply_laptop_only(laptop: dict, external: dict) -> None:
    """Enable laptop display only"""
    if not laptop:
        return
    
    try:
        laptop_name = laptop['name']
        width = laptop['width']
        height = laptop['height']
        refresh = laptop.get('refreshRate', 60)
        scale = laptop.get('scale', 1.0)
        
        # Enable laptop with its settings
        subprocess.run(
            ["hyprctl", "keyword", "monitor", 
             f"{laptop_name},{width}x{height}@{int(refresh)},auto,{scale}"],
            timeout=5,
            check=True
        )
        
        # Disable external if present
        if external:
            subprocess.run(
                ["hyprctl", "keyword", "monitor", f"{external['name']},disable"],
                timeout=5
            )
    except Exception:
        pass


def get_monitor_count() -> tuple:
    """Get count of enabled monitors and laptop disabled state"""
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        
        monitors = json.loads(result.stdout)
        enabled_count = len([m for m in monitors if not m.get('disabled', False)])
        
        # Check if laptop (eDP/LVDS/DSI) is disabled
        laptop_disabled = not any(
            'eDP' in m['name'] or 'LVDS' in m['name'] or 'DSI' in m['name']
            for m in monitors if not m.get('disabled', False)
        )
        
        return enabled_count, laptop_disabled
    except Exception:
        return 1, False  # Safe default


def emergency_enable_laptop() -> None:
    """Emergency: Re-enable laptop screen to prevent black screen"""
    try:
        send_notification("⚠️ External display lost - enabling laptop screen", urgent=True)
        monitors = get_monitors()
        if monitors['laptop']:
            apply_laptop_only(monitors['laptop'], None)
    except Exception:
        # Last resort: just enable laptop with preferred settings
        try:
            subprocess.run(
                ["hyprctl", "keyword", "monitor", ",preferred,auto,1"],
                timeout=5
            )
        except Exception:
            pass


def monitor_hotplug() -> None:
    """Monitor for external display disconnect and provide emergency recovery"""
    previous_count, previous_laptop_disabled = get_monitor_count()
    
    print("hyprmode emergency recovery daemon started")
    print("Monitoring for external display disconnect...")
    
    while True:
        try:
            current_count, current_laptop_disabled = get_monitor_count()
            
            # CRITICAL: External unplugged while laptop disabled = BLACK SCREEN!
            if (previous_laptop_disabled and 
                current_laptop_disabled and 
                current_count == 0):
                emergency_enable_laptop()
            
            previous_count = current_count
            previous_laptop_disabled = current_laptop_disabled
            
            time.sleep(1)  # Check every second
            
        except KeyboardInterrupt:
            print("\nStopping emergency recovery daemon")
            break
        except Exception:
            time.sleep(5)  # Back off on errors


if __name__ == "__main__":
    try:
        monitor_hotplug()
    except KeyboardInterrupt:
        print("\nDaemon stopped")
        sys.exit(0)
