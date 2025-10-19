#!/bin/bash

echo "Uninstalling HyprMode and Emergency Recovery Daemon..."

# Stop and disable daemon service
echo "Stopping daemon service..."
systemctl --user stop hyprmode-daemon
systemctl --user disable hyprmode-daemon

# Remove systemd service file
echo "Removing systemd service..."
rm -f ~/.config/systemd/user/hyprmode-daemon.service

# Remove all installed files
echo "Removing installed files..."
sudo rm -f /usr/local/bin/hyprmode
sudo rm -f /usr/local/bin/hyprmode-daemon
sudo rm -f /usr/local/bin/hyprmode-daemon-wrapper

# Reload systemd
systemctl --user daemon-reload

echo ""
echo "✓ Uninstallation complete!"
echo ""
echo "Daemon service status:"
systemctl --user status hyprmode-daemon --no-pager 2>&1 | head -5
