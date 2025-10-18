#!/bin/bash
# Install hyprmode and optional daemon

set -e

echo "=== HyprMode Installation ==="
echo ""

# Check if running on Hyprland
if ! command -v hyprctl &> /dev/null; then
    echo "Warning: hyprctl not found. Are you running Hyprland?"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install main script
echo "Installing hyprmode..."
sudo cp hyprmode.py /usr/local/bin/hyprmode
sudo chmod +x /usr/local/bin/hyprmode
echo "✓ Main script installed to /usr/local/bin/hyprmode"
echo ""

# Install daemon (optional)
read -p "Install automatic lid-handling daemon? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing daemon..."
    sudo cp hyprmode-daemon.py /usr/local/bin/hyprmode-daemon
    sudo chmod +x /usr/local/bin/hyprmode-daemon
    echo "✓ Daemon installed to /usr/local/bin/hyprmode-daemon"
    echo ""
    
    # Optional systemd service
    read -p "Install systemd service for auto-start? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing systemd service..."
        mkdir -p ~/.config/systemd/user/
        cp hyprmode-daemon.service ~/.config/systemd/user/
        systemctl --user daemon-reload
        systemctl --user enable hyprmode-daemon.service
        systemctl --user start hyprmode-daemon.service
        echo "✓ Systemd service installed and started!"
        echo ""
        echo "Service commands:"
        echo "  Status:  systemctl --user status hyprmode-daemon"
        echo "  Stop:    systemctl --user stop hyprmode-daemon"
        echo "  Restart: systemctl --user restart hyprmode-daemon"
        echo "  Disable: systemctl --user disable hyprmode-daemon"
    else
        echo ""
        echo "To start daemon manually: hyprmode-daemon &"
    fi
else
    echo "Skipping daemon installation."
fi

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "Usage:"
echo "  Manual mode:    hyprmode"
echo "  Start daemon:   hyprmode-daemon &"
echo ""
echo "Press Super+P or run 'hyprmode' to switch display modes."

