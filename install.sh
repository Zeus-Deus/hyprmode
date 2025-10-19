#!/bin/bash

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
