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

# Install daemon (recommended for safety)
echo "=== Emergency Recovery Daemon ==="
echo "Prevents black screens if external monitor is unplugged"
echo "Recommended for safety (minimal resource usage)"
echo ""
read -p "Install emergency recovery daemon? (Y/n) " -n 1 -r
echo
REPLY=${REPLY:-Y}  # Default to Y if just Enter pressed
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing daemon..."
    sudo cp hyprmode-daemon.py /usr/local/bin/hyprmode-daemon
    sudo chmod +x /usr/local/bin/hyprmode-daemon
    echo "✓ Daemon installed to /usr/local/bin/hyprmode-daemon"
    echo ""
    
    # Setup Hyprland lid switch bindings
    echo "Setting up Hyprland lid switch bindings..."
    
    LID_CONF="$HOME/.config/hypr/lid-switch.conf"
    
    # Auto-detect laptop monitor name
    echo "Detecting laptop monitor..."
    LAPTOP_MONITOR=$(hyprctl monitors all -j 2>/dev/null | jq -r '.[] | select(.name | test("eDP|LVDS|DSI")) | .name' | head -n 1)
    
    if [[ -z "$LAPTOP_MONITOR" ]]; then
        echo "⚠ Warning: Could not auto-detect laptop monitor"
        echo "  Trying common names: eDP-1, eDP-2, LVDS-1"
        LAPTOP_MONITOR="eDP-1"
    else
        echo "✓ Detected laptop monitor: $LAPTOP_MONITOR"
    fi
    
    # Get current monitor settings for restore
    LAPTOP_SETTINGS=$(hyprctl monitors all -j 2>/dev/null | jq -r ".[] | select(.name == \"$LAPTOP_MONITOR\") | \"\(.width)x\(.height)@\(.refreshRate | floor),auto,\(.scale)\"")
    
    if [[ -z "$LAPTOP_SETTINGS" ]]; then
        echo "  Using default settings: preferred,auto,1.25"
        LAPTOP_SETTINGS="preferred,auto,1.25"
    else
        echo "✓ Current settings: $LAPTOP_SETTINGS"
    fi
    
    # Create lid-switch.conf with detected values
    cat > "$LID_CONF" << EOF
# hyprmode - Automatic lid switch detection
# Generated for laptop monitor: $LAPTOP_MONITOR

# When lid closes, disable laptop screen
bindl = , switch:on:Lid Switch, exec, hyprctl keyword monitor "$LAPTOP_MONITOR,disable"

# When lid opens, restore laptop screen
bindl = , switch:off:Lid Switch, exec, hyprctl keyword monitor "$LAPTOP_MONITOR,$LAPTOP_SETTINGS"
EOF
    
    echo "✓ Created $LID_CONF"
    echo "  Lid close → Disables $LAPTOP_MONITOR"
    echo "  Lid open → Restores $LAPTOP_MONITOR at $LAPTOP_SETTINGS"
    
    # Source it in hyprland.conf if not already sourced
    HYPR_CONF="$HOME/.config/hypr/hyprland.conf"
    if [ -f "$HYPR_CONF" ]; then
        if ! grep -q "source.*lid-switch.conf" "$HYPR_CONF"; then
            echo "" >> "$HYPR_CONF"
            echo "# hyprmode lid switch bindings" >> "$HYPR_CONF"
            echo "source = ~/.config/hypr/lid-switch.conf" >> "$HYPR_CONF"
            echo "✓ Added source line to hyprland.conf"
        else
            echo "✓ Already sourced in hyprland.conf"
        fi
    fi
    
    echo ""
    
    # Install systemd service
    read -p "Enable auto-start with systemd? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing systemd service..."
        mkdir -p ~/.config/systemd/user/
        cp hyprmode-daemon.service ~/.config/systemd/user/
        systemctl --user daemon-reload
        systemctl --user enable hyprmode-daemon.service
        systemctl --user start hyprmode-daemon.service
        echo "✓ Emergency recovery daemon enabled!"
    fi
else
    echo ""
    echo "⚠ Warning: Without daemon, unplugging external monitor while laptop"
    echo "  screen is disabled may leave you with a black screen!"
    echo ""
fi

echo ""
echo "=== Installation Summary ==="
if [ -f /usr/local/bin/hyprmode ]; then
    echo "✓ Main script:      /usr/local/bin/hyprmode"
fi
if [ -f /usr/local/bin/hyprmode-daemon ]; then
    echo "✓ Daemon:           /usr/local/bin/hyprmode-daemon"
fi
if [ -f ~/.config/hypr/lid-switch.conf ]; then
    echo "✓ Lid config:       ~/.config/hypr/lid-switch.conf"
fi
if [ -f ~/.config/systemd/user/hyprmode-daemon.service ]; then
    echo "✓ Systemd service:  ~/.config/systemd/user/hyprmode-daemon.service"
fi
echo ""
echo "=== What Was Added ==="
echo "1. hyprmode command - Manual display mode switching (Super+P)"
echo "2. Lid detection - Auto-disable laptop screen when lid closes"
echo "3. Emergency daemon - Prevents black screens on external unplug"
if systemctl --user is-active hyprmode-daemon &>/dev/null; then
    echo "4. Systemd service - Auto-starts daemon on login [RUNNING]"
else
    echo "4. Systemd service - Run 'systemctl --user start hyprmode-daemon' to start"
fi
echo ""
echo "Next steps:"
echo "  • Reload Hyprland: hyprctl reload"
echo "  • Try it: Press Super+P or run 'hyprmode'"
echo "  • To uninstall: ./uninstall.sh"
echo ""
