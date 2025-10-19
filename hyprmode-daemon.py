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
import os
import re


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
    """Get count of enabled monitors and check if laptop exists"""
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        
        monitors = json.loads(result.stdout)
        monitor_count = len(monitors)
        
        # Check if laptop monitor exists in the list
        has_laptop = any(
            'eDP' in m['name'] or 'LVDS' in m['name'] or 'DSI' in m['name']
            for m in monitors
        )
        
        return monitor_count, has_laptop
    except Exception:
        return 1, True  # Safe default


def emergency_enable_laptop() -> None:
    """Emergency: Re-enable laptop screen with correct settings"""
    try:
        send_notification("⚠️ External display lost - enabling laptop screen", urgent=True)
        
        # Read laptop settings from lid-switch.conf if it exists
        laptop_settings = "preferred,auto,1.25"  # Safe default
        
        try:
            lid_conf = os.path.expanduser("~/.config/hypr/lid-switch.conf")
            if os.path.exists(lid_conf):
                with open(lid_conf, 'r') as f:
                    for line in f:
                        # Find the "lid open" line with monitor settings
                        if 'switch:off' in line and 'monitor' in line:
                            # Extract settings from: monitor "eDP-2,1920x1200@165,auto,1.25"
                            match = re.search(r'"([^"]+)"', line)
                            if match:
                                full_setting = match.group(1)
                                # Extract just the settings part (after monitor name)
                                if ',' in full_setting:
                                    parts = full_setting.split(',', 1)
                                    if len(parts) == 2:
                                        laptop_settings = parts[1]  # Get "1920x1200@165,auto,1.25"
                                        break
        except Exception:
            pass  # Use default if reading fails
        
        # Try common laptop monitor names with settings
        laptop_names = ['eDP-1', 'eDP-2', 'LVDS-1', 'DSI-1']
        
        for name in laptop_names:
            try:
                subprocess.run(
                    ["hyprctl", "keyword", "monitor", f"{name},{laptop_settings}"],
                    timeout=2,
                    check=False,
                    capture_output=True
                )
            except Exception:
                continue
        
        print("✓ Emergency recovery executed")
        
    except Exception as e:
        print(f"✗ Emergency recovery failed: {e}")


def monitor_hotplug() -> None:
    """Monitor for external display disconnect and provide emergency recovery"""
    previous_count, previous_has_laptop = get_monitor_count()
    
    print("hyprmode emergency recovery daemon started")
    print("Monitoring for external display disconnect...")
    
    while True:
        try:
            current_count, current_has_laptop = get_monitor_count()
            
            # CRITICAL: No monitors active = BLACK SCREEN!
            # This happens when:
            # 1. Laptop was disabled (External Only mode)
            # 2. External monitor unplugged
            # Result: 0 monitors in hyprctl list
            if current_count == 0:
                print("⚠️ EMERGENCY: No active monitors detected!")
                emergency_enable_laptop()
            
            previous_count = current_count
            previous_has_laptop = current_has_laptop
            
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
