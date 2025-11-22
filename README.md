# hyprmode

**Super+P style display mode switcher for Hyprland**

A fast, minimal TUI tool for switching display modes on Hyprland (Wayland compositor). Replicates Windows' Super+P functionality with automatic lid-close handling.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

## Components

This project consists of two tools that work together:

1. **hyprmode** - Interactive TUI for switching display modes
   - Laptop Only: Only laptop screen active
   - External Only: Only external monitor active
   - Extend: Both screens active

2. **hyprmode-daemon** - Emergency recovery daemon
   - Monitors for external display disconnection
   - Automatically restores laptop screen if all monitors are lost
   - Prevents black screen scenarios

Both components are installed together and work seamlessly.

## Features

- 🖥️ **4 Display Modes**: Laptop Only, External Only, Extend, Mirror
- ⚡ **Instant Switching**: Fast mode application with `hyprctl` commands
- 🎨 **Beautiful TUI**: Built with python-textual framework
- ⌨️ **Vim Keybinds**: Navigate with j/k, select with Enter, quit with q
- 🤖 **Automatic Mode**: Optional daemon for lid-aware display switching
- 🔍 **Smart Detection**: Handles disabled monitors gracefully
- 🔔 **Desktop Notifications**: Visual feedback for mode changes
- 🪶 **Lightweight**: Single Python file, minimal dependencies

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/hyprmode.git
cd hyprmode

# Run installer (installs both main tool AND daemon)
chmod +x install.sh
./install.sh
```

The installer will:
1. Install `hyprmode` main tool to `/usr/local/bin/`
2. Install `hyprmode-daemon` emergency recovery system
3. Install `hyprmode-daemon-wrapper` (bytecode cache bypass)
4. Set up systemd service for automatic daemon startup
5. Enable daemon service (starts on boot)
6. Verify installation with version check
7. Show status summary

**Files installed:**
- `/usr/local/bin/hyprmode` - Main TUI tool
- `/usr/local/bin/hyprmode-daemon` - Emergency recovery daemon
- `/usr/local/bin/hyprmode-daemon-wrapper` - Python wrapper script
- `~/.config/systemd/user/hyprmode-daemon.service` - Systemd service

**To uninstall everything:**
```bash
cd ~/Documents/hyprmode
chmod +x uninstall.sh
./uninstall.sh
```

### Manual Installation

If you prefer manual installation:

```bash
# Install main script
sudo cp hyprmode.py /usr/local/bin/hyprmode
sudo chmod +x /usr/local/bin/hyprmode

# Install daemon (recommended)
sudo cp hyprmode-daemon.py /usr/local/bin/hyprmode-daemon
sudo chmod +x /usr/local/bin/hyprmode-daemon
```

### Dependencies

#### Arch Linux

```bash
sudo pacman -S python-textual
```

Optional: Omarchy theme support (Python < 3.11 only). Python 3.11+ has built-in `tomllib`, but older versions require `tomli`:

```bash
sudo pacman -S python-tomli  # or: pip install tomli
```

#### Other distros

```bash
pip install textual
```

Optional for other distros (Python < 3.11):

```bash
pip install tomli  # Only needed for Python < 3.11
```

## Usage

### Manual Mode

Run `hyprmode` to open the interactive menu:

```bash
hyprmode
```

**Keybinds:**
- `j` / `Down` - Move down
- `k` / `Up` - Move up
- `Enter` - Apply selected mode
- `q` - Quit

**Display Modes:**

1. **💻 Laptop Only** - Disable external displays, laptop screen active
2. **🖥️ External Only** - Disable laptop screen, external display active
3. **↔️ Extend** - Both displays active, external positioned to the right
4. **🔄 Mirror** - Both displays show identical content

### Automatic Lid Handling

Lid detection is handled by Hyprland's native `bindl` (bind lid switch) feature for instant, event-driven detection with zero CPU overhead.

**How it works:**
1. Kernel detects lid close → Hyprland receives event instantly
2. Hyprland triggers display mode switch via `bindl` binding
3. No polling, no delay, zero CPU usage

**Configuration:**

The installer **auto-detects your laptop monitor** and creates `~/.config/hypr/lid-switch.conf`:
```conf
# hyprmode - Automatic lid switch detection
# Generated for laptop monitor: eDP-2  (auto-detected!)

# When lid closes - disable laptop display
bindl = , switch:on:Lid Switch, exec, hyprctl keyword monitor "eDP-2,disable"

# When lid opens - restore laptop display with your current settings
bindl = , switch:off:Lid Switch, exec, hyprctl keyword monitor "eDP-2,1920x1200@165,auto,1.25"
```

**Features:**
- ✅ Works with any laptop (eDP-1, eDP-2, LVDS-1, DSI-1, etc.)
- ✅ Preserves your exact current monitor settings
- ✅ Graceful fallback if detection fails

After installation, reload Hyprland: `hyprctl reload`

### Emergency Recovery Daemon

#### Overview

The emergency recovery daemon is a **production-tested safety system** that prevents black screens when external monitors are disconnected in "External Only" mode. It has survived extensive reboot testing and handles edge cases like Hyprland startup timing.

#### Why It's Critical

**Problem:** Unplugging HDMI in "External Only" mode → Complete black screen, no recovery possible  
**Solution:** Daemon detects monitor loss and restores laptop screen **within 1 second**

#### Installation & Verification

The daemon is installed automatically by `install.sh`. Verify it's working:

```bash
# Check daemon is running
systemctl --user status hyprmode-daemon

# Should show: Active: active (running)

# Verify correct version is loaded
journalctl --user -u hyprmode-daemon | grep "VERSION"

# Should show: HyprMode Daemon VERSION: 2025-10-19-PRODUCTION-v1
```

#### Testing Emergency Recovery

1. **Plug in external monitor** via HDMI
2. **Run hyprmode** and switch to "External Only" mode
3. **Unplug the HDMI cable**
4. **Expected:** Laptop screen restores within 1 second
5. **Check logs:** Should show emergency recovery message

```bash
# Watch live recovery event
journalctl --user -u hyprmode-daemon -f

# Expected output when unplugging:
# ⚠️ EMERGENCY: No active monitors detected!
# ✓ Emergency recovery executed
```

#### Daemon Commands

```bash
# View current status
systemctl --user status hyprmode-daemon

# Check if daemon is active
systemctl --user is-active hyprmode-daemon

# View live logs (shows monitoring activity)
journalctl --user -u hyprmode-daemon -f

# View logs from current boot only
journalctl --user -u hyprmode-daemon -b

# Check which version is running
journalctl --user -u hyprmode-daemon | grep "VERSION"

# Restart daemon
systemctl --user restart hyprmode-daemon

# Stop daemon (not recommended)
systemctl --user stop hyprmode-daemon

# Disable auto-start (not recommended)
systemctl --user disable hyprmode-daemon
```

#### Understanding the Logs

**Normal operation (healthy daemon):**
```
✓ Hyprland is ready
HyprMode Daemon VERSION: 2025-10-19-PRODUCTION-v1
hyprmode emergency recovery daemon started
Monitoring for external display disconnect...
HEARTBEAT
Detected: 2 monitors, has_laptop=True
Previous: 2 monitors, previous_has_laptop=True
```

**First boot attempt (normal behavior):**
```
Waiting for Hyprland to start...
ERROR: Hyprland failed to start after 30 seconds
hyprmode-daemon.service: Failed with result 'exit-code'.
Scheduled restart job, restart counter is at 1.
```
This is **expected** on boot - systemd automatically retries and succeeds.

**Emergency recovery in action:**
```
Detected: 1 monitors, has_laptop=False     # External Only mode
Detected: 0 monitors, has_laptop=False     # HDMI unplugged!
⚠️ EMERGENCY: No active monitors detected!
✓ Emergency recovery executed
Detected: 1 monitors, has_laptop=True      # Laptop restored
```

#### Troubleshooting

##### Daemon not starting after reboot

**Check version loaded:**
```bash
journalctl --user -u hyprmode-daemon -b | grep "VERSION"
```

If wrong version or no version appears:
```bash
# Verify files match
diff ~/Documents/hyprmode/hyprmode-daemon.py /usr/local/bin/hyprmode-daemon

# If different, reinstall
cd ~/Documents/hyprmode
./uninstall.sh
./install.sh
```

##### Emergency recovery not working

**Verify daemon is monitoring:**
```bash
journalctl --user -u hyprmode-daemon -f
```

You should see:
- `HEARTBEAT` messages every second (daemon is alive)
- `Detected: X monitors` showing current monitor state

If no HEARTBEAT:
```bash
# Restart daemon
systemctl --user restart hyprmode-daemon

# Check for errors
journalctl --user -u hyprmode-daemon -n 50
```

##### Daemon crashes or restarts frequently

View error logs:
```bash
journalctl --user -u hyprmode-daemon --since "10 minutes ago"
```

Look for:
- `ERROR in get_monitor_count()` - hyprctl communication issue
- `Emergency recovery failed` - monitor enable command failed

##### Version mismatch after update

The daemon uses Python bytecode bypass to prevent stale cached code:
```bash
# Force clean reinstall
cd ~/Documents/hyprmode
./uninstall.sh
sudo find /usr/local/bin -name "*.pyc" -delete
sudo find ~/.cache -name "*hyprmode*.pyc" -delete
./install.sh

# Verify correct version
journalctl --user -u hyprmode-daemon | grep "VERSION"
```

#### Technical Details

**Monitor Detection Method:**
- Uses `hyprctl monitors -j` with **dpmsStatus field**
- Checks if display is actually powered on (`dpmsStatus == True`)
- More reliable than the `disabled` field which can be inaccurate

**Startup Behavior:**
- Waits up to 30 seconds for Hyprland to be ready
- Auto-retries via systemd if first attempt fails
- Typical success on 2nd attempt (6 seconds after boot)

**Performance:**
- Polls every 1 second (negligible CPU usage)
- Memory footprint: ~6-7MB
- Log storage: ~10MB per week
- Response time: < 1 second for emergency recovery

**Safety Features:**
- Python bytecode caching bypass (prevents stale code)
- Version tracking (verify correct code is running)
- Comprehensive error logging
- Automatic systemd restart on failure

## Debugging Commands

These commands were used during development and testing. Useful if you need to diagnose issues:

### Check Hyprland Monitor State

```bash
# View all monitors (including disabled)
hyprctl monitors all -j | jq

# View only active monitors
hyprctl monitors -j | jq

# Check specific monitor's dpmsStatus
hyprctl monitors -j | jq '.[] | {name, dpmsStatus, disabled}'
```

### Monitor Daemon in Real-Time

```bash
# Follow daemon logs live
journalctl --user -u hyprmode-daemon -f

# Show last 100 lines
journalctl --user -u hyprmode-daemon -n 100

# Show logs from specific time
journalctl --user -u hyprmode-daemon --since "5 minutes ago"

# Show only emergency events
journalctl --user -u hyprmode-daemon | grep "EMERGENCY"
```

### Verify Installation

```bash
# Check all installed files exist
ls -la /usr/local/bin/hyprmode*
ls -la ~/.config/systemd/user/hyprmode-daemon.service

# Verify service is enabled
systemctl --user is-enabled hyprmode-daemon

# Check what systemd is actually executing
systemctl --user show hyprmode-daemon | grep ExecStart
```

### Force Clean Reinstall

If something is broken and you need a complete fresh start:

```bash
cd ~/Documents/hyprmode

# Complete uninstall
./uninstall.sh

# Clean any cached Python bytecode
sudo find /usr/local/bin -name "*.pyc" -delete
find ~/.cache -name "*hyprmode*.pyc" -delete

# Reinstall
./install.sh

# Verify version
journalctl --user -u hyprmode-daemon | grep "VERSION"

# Test emergency recovery
# (plug monitor → external only → unplug → laptop should restore)
```

## Configuration

### Hyprland Config

#### For Omarchy Users (Recommended)

Omarchy uses separate config files for better organization. Follow these steps:

**Step 1: Add the keybind**

Edit `~/.config/hypr/bindings.conf`:

```bash
nano ~/.config/hypr/bindings.conf
```

Add this line (Omarchy uses `bindd` with descriptions):

```bash
bindd = SUPER, P, Display switcher, exec, alacritty --class hyprmode -e hyprmode
```

**Step 2: Create window rules**

Create `~/.config/hypr/windows.conf`:

```bash
cat > ~/.config/hypr/windows.conf << 'EOF'
# HyprMode - Float and center
windowrulev2 = float, class:(hyprmode)
windowrulev2 = center, class:(hyprmode)
windowrulev2 = size 600 530, class:(hyprmode)
windowrulev2 = opacity 0.95, class:(hyprmode)
EOF
```

**Step 3: Source the window rules**

Add the source line to your `hyprland.conf` (only if not already present):

```bash
# Check if already added
if ! grep -q "windows.conf" ~/.config/hypr/hyprland.conf; then
    echo "source = ~/.config/hypr/windows.conf" >> ~/.config/hypr/hyprland.conf
fi
```

**Step 4: Reload and test**

```bash
hyprctl reload
```

Now press **Super+P** - hyprmode should appear as a centered floating window!

**Why the special launch command?**

TUI apps run inside terminals, so Hyprland can't distinguish them from regular terminal windows. The `alacritty --class hyprmode` command creates a terminal with a unique class that window rules can target.

#### For Standard Hyprland Users

Add to your `~/.config/hypr/hyprland.conf`:

```conf
# Display mode switcher (like Windows Super+P)
bind = SUPER, P, exec, alacritty --class hyprmode -e hyprmode

# Window rules for floating mode
windowrulev2 = float, class:(hyprmode)
windowrulev2 = center, class:(hyprmode)
windowrulev2 = size 600 530, class:(hyprmode)
windowrulev2 = opacity 0.95, class:(hyprmode)
```

Then reload: `hyprctl reload`

#### Customizing Window Size

The default size is 600x530 pixels. To adjust:

```bash
nano ~/.config/hypr/windows.conf
```

Change the size line:
```bash
windowrulev2 = size 600 530, class:(hyprmode)  # Default
windowrulev2 = size 550 400, class:(hyprmode)  # Smaller
windowrulev2 = size 700 600, class:(hyprmode)  # Larger
```

Then reload: `hyprctl reload`

### Auto-start Daemon

Enable systemd service during installation, or manually:

```bash
systemctl --user enable hyprmode-daemon.service
```

## Technical Details

### Monitor Detection

- Uses `hyprctl monitors all -j` to detect all monitors (including disabled)
- Falls back to `hyprctl monitors -j` for older Hyprland versions
- Identifies laptop display by "eDP" in monitor name
- Handles multiple external monitors (uses first detected)

### Display Commands

```bash
# Disable monitor
hyprctl keyword monitor "MONITOR_NAME,disable"

# Enable with auto-detection
hyprctl keyword monitor "MONITOR_NAME,preferred,auto,1"

# Extend mode
hyprctl keyword monitor "LAPTOP,preferred,0x0,1"
hyprctl keyword monitor "EXTERNAL,preferred,auto-right,1"

# Mirror mode
hyprctl keyword monitor "EXTERNAL,WIDTHxHEIGHT@REFRESH,0x0,1,mirror,LAPTOP"
```

## Troubleshooting

### "hyprctl not found"
Make sure you're running Hyprland. This tool only works on Hyprland.

### "No monitors detected"
Check that Hyprland is running and monitors are connected:
```bash
hyprctl monitors -j
```

### Daemon not switching automatically
1. Check if daemon is running:
   ```bash
   systemctl --user status hyprmode-daemon
   ```
2. Check lid state detection:
   ```bash
   cat /proc/acpi/button/lid/LID/state
   ```
3. View daemon logs:
   ```bash
   journalctl --user -u hyprmode-daemon -f
   ```

### Laptop screen still active after "External Only"
The monitor is properly disabled in Hyprland. If you see artifacts, it's a display driver issue, not hyprmode.

### Multiple external monitors
Currently, hyprmode uses the first detected external monitor. Multi-monitor support may be added in the future.

## Development

### Project Structure

```
hyprmode/
├── hyprmode.py              # Main TUI application
├── hyprmode-daemon.py       # Emergency recovery daemon
├── hyprmode-daemon.service  # Systemd service unit
├── install.sh               # Installation script (auto-detects monitors)
├── uninstall.sh             # Uninstallation script
├── README.md                # This file
└── LICENSE                  # MIT License
```

### Running from Source

```bash
# Manual mode
python hyprmode.py

# Daemon mode
python hyprmode-daemon.py
```

### Code Style

- Minimal and readable Python code
- Type hints for all functions
- Clean error handling
- No duplicate code
- Follows python-textual patterns

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Credits

- Built with [Textual](https://textual.textualize.io/) TUI framework
- Inspired by Windows Super+P functionality
- Made for [Hyprland](https://hyprland.org/) Wayland compositor

## Links

- **Repository**: https://github.com/Zeus-Deus/hyprmode
- **Issues**: https://github.com/Zeus-Deus/hyprmode/issues
- **Hyprland**: https://hyprland.org/
- **Textual**: https://textual.textualize.io/
