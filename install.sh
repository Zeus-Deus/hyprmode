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

# Refresh any legacy copies in /usr/bin so stale code can't shadow this install
for pair in "hyprmode:hyprmode.py" "hyprmode-daemon:hyprmode-daemon.py" "hyprmode-daemon-wrapper:hyprmode-daemon-wrapper"; do
    dest="/usr/bin/${pair%%:*}"
    src="${pair#*:}"
    if [ -f "$dest" ]; then
        sudo cp "$src" "$dest"
        sudo chmod +x "$dest"
        echo "✓ Refreshed legacy copy: $dest"
    fi
done

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

# Omarchy ships its own lid handling (external-guarded, reload-based).
# A second set of lid bindings would conflict with it (both fire on lid
# events), so defer to Omarchy entirely when it is installed.
if [ -d "$HOME/.local/share/omarchy" ]; then
    echo "✓ Omarchy detected - deferring lid handling to Omarchy"
    LID_CONF="$HOME/.config/hypr/lid-switch.conf"
    if [ -f "$LID_CONF" ] && grep -q "switch:" "$LID_CONF"; then
        # Neutralize a lid config left behind by an older hyprmode install.
        # The file is kept (comments only) so an existing
        # "source = ~/.config/hypr/lid-switch.conf" line stays valid.
        cat > "$LID_CONF" << 'EOF'
# hyprmode - lid handling disabled on this machine
#
# Omarchy was detected (~/.local/share/omarchy). Omarchy ships its own
# external-guarded, reload-based lid handling, and a second set of lid
# bindings would conflict with it (both fire on lid events).
#
# This file is intentionally empty so an existing
# "source = ~/.config/hypr/lid-switch.conf" line in hyprland.conf
# stays valid.
EOF
        echo "✓ Neutralized old lid-switch.conf (Omarchy owns lid events now)"
        echo "  Run 'hyprctl reload' to apply"
    fi
# Check if Hyprland is running
elif ! pgrep -x Hyprland > /dev/null; then
    echo "⚠ Hyprland is not running - skipping lid detection"
    echo "  Run installer again after starting Hyprland to enable lid handling"
else
    # Use Python to detect the laptop monitor name
    LAPTOP_MONITOR=$(hyprctl monitors all -j 2>/dev/null | python3 -c "
import sys, json
try:
    monitors = json.load(sys.stdin)
    # Find first monitor with eDP, LVDS, or DSI in name
    laptop = next((m for m in monitors if any(x in m['name'].upper() for x in ['EDP', 'LVDS', 'DSI'])), None)
    print(laptop['name'] if laptop else 'NOTFOUND')
except:
    print('ERROR')
" 2>/dev/null)

    if [ "$LAPTOP_MONITOR" = "NOTFOUND" ] || [ "$LAPTOP_MONITOR" = "ERROR" ] || [ -z "$LAPTOP_MONITOR" ]; then
        echo "⚠ No laptop monitor detected (desktop system?)"
        echo "  Skipping lid-switch configuration"
    else
        echo "✓ Detected laptop monitor: $LAPTOP_MONITOR"

        # Create Hyprland config directory if needed
        mkdir -p ~/.config/hypr/

        # Create lid-switch.conf
        # - Lid close only disables the panel if an external monitor is
        #   actually connected (never drop to 0 displays).
        # - Lid open restores via "hyprctl reload": "keyword monitor" is a
        #   no-op on a disabled connector, a config reload re-lights it.
        cat > ~/.config/hypr/lid-switch.conf << EOF
# hyprmode - Automatic lid switch detection
# Generated for laptop monitor: $LAPTOP_MONITOR

# When lid closes - disable laptop display, but ONLY if an external
# monitor is actually connected (otherwise you'd have 0 displays)
bindl = , switch:on:Lid Switch, exec, sh -c 'for s in /sys/class/drm/card*-*/status; do case "\$s" in *eDP*|*LVDS*|*DSI*) continue;; esac; [ "\$(cat "\$s")" = connected ] && exec hyprctl keyword monitor "$LAPTOP_MONITOR,disable"; done'

# When lid opens - restore laptop display via config reload
# (NOTE: "hyprctl keyword monitor" cannot re-enable a disabled connector)
bindl = , switch:off:Lid Switch, exec, hyprctl reload
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
