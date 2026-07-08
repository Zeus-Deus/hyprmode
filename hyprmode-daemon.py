#!/usr/bin/env python3
# VERSION: 2026-07-08-v0.2.0
"""
hyprmode-daemon - Emergency laptop screen recovery

Monitors for external display disconnect and re-enables laptop screen
if user would otherwise be stuck with a black screen.

Recovery uses `hyprctl reload`: `hyprctl keyword monitor <name>,<settings>`
does NOT re-enable a connector that is currently disabled (Hyprland won't
re-modeset a disabled output that way), but a config reload re-lights it.
"""

import subprocess
import time
import sys
import json
import os


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

        # Count monitors that are configured (non-zero resolution) and not explicitly disabled.
        # DPMS only represents power state, so we ignore it to keep sleeping panels in the tally.
        enabled_monitors = [
            m for m in monitors
            if m.get('width', 0) > 0
            and m.get('height', 0) > 0
            and m.get('disabled', False) is not True
        ]

        monitor_count = len(enabled_monitors)

        # Check if laptop monitor exists in the enabled list
        has_laptop = any(
            'eDP' in m['name'] or 'LVDS' in m['name'] or 'DSI' in m['name']
            for m in enabled_monitors
        )
        
        return monitor_count, has_laptop
    except Exception as e:
        print(f"ERROR in get_monitor_count(): {e}")
        import traceback
        traceback.print_exc()
        return 0, False  # Return 0 monitors to be safe (prevents masking issues)


def emergency_enable_laptop() -> None:
    """Emergency: Re-enable displays via `hyprctl reload`.

    `hyprctl keyword monitor <name>,<settings>` is a no-op on a connector
    that is currently disabled - it cannot bring a display back. A config
    reload re-reads the monitor configuration and re-lights disabled
    connectors, so it is the only reliable recovery path.
    """
    try:
        send_notification("⚠️ No active displays - restoring via config reload", urgent=True)

        # Clear Omarchy's internal-display disable toggle if present,
        # otherwise the reload would re-apply "monitor=<name>,disable"
        # and the panel would stay dark.
        omarchy_toggle = os.path.expanduser(
            "~/.local/state/omarchy/toggles/hypr/internal-monitor-disable.conf"
        )
        try:
            os.remove(omarchy_toggle)
            print("Cleared Omarchy internal-monitor-disable toggle")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Could not clear Omarchy toggle: {e}")

        subprocess.run(
            ["hyprctl", "reload"],
            timeout=5,
            check=False,
            capture_output=True
        )

        print("✓ Emergency recovery executed (hyprctl reload)")

    except Exception as e:
        print(f"✗ Emergency recovery failed: {e}")


def wait_for_hyprland(max_wait: int = 30) -> bool:
    """Wait for Hyprland to be ready"""
    for i in range(max_wait):
        try:
            result = subprocess.run(
                ['hyprctl', 'monitors', '-j'], 
                capture_output=True,
                check=True,
                timeout=2
            )
            print("✓ Hyprland is ready")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            if i == 0:
                print("Waiting for Hyprland to start...")
            time.sleep(1)
    print("ERROR: Hyprland failed to start after 30 seconds")
    return False


def monitor_hotplug() -> None:
    """Monitor for external display disconnect and provide emergency recovery"""
    # Wait for Hyprland to be ready before starting monitoring
    if not wait_for_hyprland():
        sys.exit(1)
    
    print("HyprMode Daemon VERSION: 2026-07-08-v0.2.0")
    
    previous_count, previous_has_laptop = get_monitor_count()
    
    # Debounce and cooldown state
    zero_monitor_count = 0
    debounce_threshold = 3  # Require 3 consecutive 0-monitor readings
    cooldown_seconds = 10
    last_recovery_time = 0.0
    cooldown_until = 0.0
    in_cooldown = False
    
    print("hyprmode emergency recovery daemon started")
    print("Monitoring for external display disconnect...")
    
    while True:
        print("HEARTBEAT")
        try:
            now = time.time()
            
            # Automatically clear cooldown when period expires
            if in_cooldown and now >= cooldown_until:
                in_cooldown = False
                print("Cooldown period ended; recovery re-enabled")
            
            current_count, current_has_laptop = get_monitor_count()
            print(f"Detected: {current_count} monitors, has_laptop={current_has_laptop}")
            print(f"Previous: {previous_count} monitors, previous_has_laptop={previous_has_laptop}")
            
            # CRITICAL: No monitors active = BLACK SCREEN!
            # This happens when:
            # 1. Laptop was disabled (External Only mode)
            # 2. External monitor unplugged
            # Result: 0 monitors in hyprctl list
            if current_count == 0:
                zero_monitor_count += 1
                print(f"0 monitors detected ({zero_monitor_count} consecutive)")
                
                if zero_monitor_count >= debounce_threshold:
                    if in_cooldown:
                        print("[DEBUG] In cooldown period, skipping recovery")
                    else:
                        print("⚠️ EMERGENCY: No active monitors detected!")
                        emergency_enable_laptop()
                        last_recovery_time = now
                        cooldown_until = now + cooldown_seconds
                        in_cooldown = True
                        readable_until = time.strftime("%H:%M:%S", time.localtime(cooldown_until))
                        print(f"Cooldown active until {readable_until}")
            else:
                if zero_monitor_count > 0:
                    print("Monitors restored, resetting zero-monitor counter")
                zero_monitor_count = 0
            
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
