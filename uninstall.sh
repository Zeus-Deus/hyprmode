#!/bin/bash
# Uninstall hyprmode

set -e

echo "=== HyprMode Uninstallation ==="
echo ""

# Stop and disable daemon if running
if systemctl --user is-active hyprmode-daemon &>/dev/null; then
    echo "Stopping daemon..."
    systemctl --user stop hyprmode-daemon
    systemctl --user disable hyprmode-daemon
    echo "✓ Daemon stopped"
fi

# Remove systemd service
if [ -f ~/.config/systemd/user/hyprmode-daemon.service ]; then
    rm ~/.config/systemd/user/hyprmode-daemon.service
    systemctl --user daemon-reload
    echo "✓ Removed systemd service"
fi

# Remove lid-switch.conf
if [ -f ~/.config/hypr/lid-switch.conf ]; then
    rm ~/.config/hypr/lid-switch.conf
    echo "✓ Removed lid-switch.conf"
fi

# Remove source line from hyprland.conf
if [ -f ~/.config/hypr/hyprland.conf ]; then
    if grep -q "source.*lid-switch.conf" ~/.config/hypr/hyprland.conf; then
        sed -i '/source.*lid-switch.conf/d' ~/.config/hypr/hyprland.conf
        sed -i '/# hyprmode lid switch bindings/d' ~/.config/hypr/hyprland.conf
        echo "✓ Removed source line from hyprland.conf"
    fi
fi

# Remove binaries
if [ -f /usr/local/bin/hyprmode ]; then
    sudo rm /usr/local/bin/hyprmode
    echo "✓ Removed /usr/local/bin/hyprmode"
fi

if [ -f /usr/local/bin/hyprmode-daemon ]; then
    sudo rm /usr/local/bin/hyprmode-daemon
    echo "✓ Removed /usr/local/bin/hyprmode-daemon"
fi

echo ""
echo "=== Uninstallation Complete ==="
echo "hyprmode has been completely removed from your system"
echo ""
echo "Note: Reload Hyprland to apply changes: hyprctl reload"

