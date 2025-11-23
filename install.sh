#!/bin/bash

echo "Clearing Python cache..."
# Clear local project cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Clear user cache directories that might have stale bytecode
rm -rf ~/.cache/textual/ 2>/dev/null || true

echo "Installing HyprMode and Emergency Recovery Daemon..."

# Check if running from correct directory
if [ ! -f "hyprmode.py" ] || [ ! -f "hyprmode-daemon.py" ]; then
    echo "Error: Required files not found. Run this script from ~/Documents/hyprmode/"
    exit 1
fi

# Install main HyprMode tool
echo "Installing HyprMode main tool..."
sudo cp hyprmode.py /usr/local/bin/hyprmode || exit 1
sudo chmod +x /usr/local/bin/hyprmode

# Install daemon files
echo "Installing emergency recovery daemon..."
sudo cp hyprmode-daemon.py /usr/local/bin/hyprmode-daemon || exit 1
sudo cp hyprmode-daemon-wrapper /usr/local/bin/hyprmode-daemon-wrapper || exit 1
sudo chmod +x /usr/local/bin/hyprmode-daemon
sudo chmod +x /usr/local/bin/hyprmode-daemon-wrapper

# Verify daemon file is correct
echo "Verifying daemon installation..."
diff hyprmode-daemon.py /usr/local/bin/hyprmode-daemon
if [ $? -eq 0 ]; then
    echo "✓ Daemon file verified"
else
    echo "✗ Warning: Daemon files don't match!"
    exit 1
fi

# Create systemd user directory if it doesn't exist
mkdir -p ~/.config/systemd/user/

# Copy systemd service file
echo "Installing systemd service..."
cp hyprmode-daemon.service ~/.config/systemd/user/hyprmode-daemon.service || exit 1

# Reload systemd daemon
systemctl --user daemon-reload

# Enable and start daemon service
echo "Enabling and starting daemon service..."
systemctl --user enable hyprmode-daemon
systemctl --user restart hyprmode-daemon

# ========================================
# AUTO-DETECT LAPTOP MONITOR AND CREATE LID CONFIG
# ========================================

echo ""
echo "Detecting laptop monitor for lid handling..."

# Check if Hyprland is running
if ! pgrep -x Hyprland > /dev/null; then
    echo "⚠ Hyprland is not running - skipping lid detection"
    echo "  Run installer again after starting Hyprland to enable lid handling"
else
    # Use Python to detect laptop monitor and get specs in one shot
    MONITOR_DATA=$(hyprctl monitors all -j 2>/dev/null | python3 -c "
import sys, json
try:
    monitors = json.load(sys.stdin)
    # Find first monitor with eDP, LVDS, or DSI in name
    laptop = next((m for m in monitors if any(x in m['name'].upper() for x in ['EDP', 'LVDS', 'DSI'])), None)
    if laptop:
        print(f\"{laptop['name']}\")
        print(f\"{laptop['width']}x{laptop['height']}@{int(laptop['refreshRate'])},auto,{laptop['scale']}\")
    else:
        print('NOTFOUND')
except:
    print('ERROR')
" 2>/dev/null)

    # Parse the output
    LAPTOP_MONITOR=$(echo "$MONITOR_DATA" | head -1)
    MONITOR_SPEC=$(echo "$MONITOR_DATA" | tail -1)

    if [ "$LAPTOP_MONITOR" = "NOTFOUND" ] || [ "$LAPTOP_MONITOR" = "ERROR" ] || [ -z "$LAPTOP_MONITOR" ]; then
        echo "⚠ No laptop monitor detected (desktop system?)"
        echo "  Skipping lid-switch configuration"
    else
        echo "✓ Detected laptop monitor: $LAPTOP_MONITOR"
        echo "✓ Detected specs: $MONITOR_SPEC"

        # Create Hyprland config directory if needed
        mkdir -p ~/.config/hypr/

        # Create lid-switch.conf
        cat > ~/.config/hypr/lid-switch.conf << EOF
# hyprmode - Automatic lid switch detection
# Generated for laptop monitor: $LAPTOP_MONITOR

# When lid closes - disable laptop display
bindl = , switch:on:Lid Switch, exec, hyprctl keyword monitor "$LAPTOP_MONITOR,disable"

# When lid opens - restore laptop display with detected settings
bindl = , switch:off:Lid Switch, exec, hyprctl keyword monitor "$LAPTOP_MONITOR,$MONITOR_SPEC"
EOF

        echo "✓ Created ~/.config/hypr/lid-switch.conf"

        # Add source line to hyprland.conf if not present
        HYPR_CONF=~/.config/hypr/hyprland.conf
        if [ -f "$HYPR_CONF" ]; then
            if ! grep -q "lid-switch.conf" "$HYPR_CONF"; then
                echo "" >> "$HYPR_CONF"
                echo "# HyprMode - Lid switch handling" >> "$HYPR_CONF"
                echo "source = ~/.config/hypr/lid-switch.conf" >> "$HYPR_CONF"
                echo "✓ Added source line to hyprland.conf"
            else
                echo "✓ hyprland.conf already sources lid-switch.conf"
            fi
        else
            echo "⚠ hyprland.conf not found - you need to manually add:"
            echo "  source = ~/.config/hypr/lid-switch.conf"
        fi

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "To activate lid handling, reload Hyprland:"
        echo "  hyprctl reload"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
fi

echo ""

# Wait for service to start
sleep 2

# Show status
echo ""
echo "✓ Installation complete!"
echo ""
echo "Main tool: /usr/local/bin/hyprmode"
echo "Daemon: Running as systemd service"
echo ""
systemctl --user status hyprmode-daemon --no-pager -l | head -20

echo ""
echo "Check daemon version: journalctl --user -u hyprmode-daemon | grep VERSION"
