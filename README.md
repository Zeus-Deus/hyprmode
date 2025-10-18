# hyprmode

**Super+P style display mode switcher for Hyprland**

A fast, minimal TUI tool for switching display modes on Hyprland (Wayland compositor). Replicates Windows' Super+P functionality with automatic lid-close handling.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

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

# Run installer
./install.sh
```

The installer will:
1. Install `hyprmode` to `/usr/local/bin/`
2. Optionally install automatic lid-handling daemon
3. Optionally set up systemd service for auto-start

### Manual Installation

```bash
sudo cp hyprmode.py /usr/local/bin/hyprmode
sudo chmod +x /usr/local/bin/hyprmode
```

### Dependencies

```bash
# Arch Linux
sudo pacman -S python-textual

# Other distros
pip install textual
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

### Automatic Mode (Daemon)

The daemon monitors laptop lid state and automatically switches display modes:

**Start daemon manually:**
```bash
hyprmode-daemon &
```

**Start daemon with systemd:**
```bash
systemctl --user start hyprmode-daemon
systemctl --user enable hyprmode-daemon  # Auto-start on login
```

**Daemon behavior:**

| Lid State | External Monitor | Action |
|-----------|------------------|--------|
| Closed | Connected | Switch to External Only |
| Closed | Not connected | No action (system sleep) |
| Opened | Connected | Switch to Extend mode |
| Opened | Not connected | Switch to Laptop Only |

**Daemon commands:**
```bash
# Check status
systemctl --user status hyprmode-daemon

# Stop daemon
systemctl --user stop hyprmode-daemon

# View logs
journalctl --user -u hyprmode-daemon -f
```

## Configuration

### Hyprland Config

Add keybind to your `~/.config/hypr/hyprland.conf`:

```conf
# Display mode switcher (like Windows Super+P)
bind = SUPER, P, exec, hyprmode
```

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

### Lid State Detection

Reads lid state from:
- `/proc/acpi/button/lid/LID/state`
- `/proc/acpi/button/lid/LID0/state` (fallback)

Returns: `open`, `closed`, or `unknown` (for desktops)

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
├── hyprmode-daemon.py       # Background daemon
├── hyprmode-daemon.service  # Systemd service unit
├── install.sh               # Installation script
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

## Roadmap

- [x] Phase 1: Monitor detection + basic TUI
- [x] Phase 2: Interactive menu + display switching
- [x] Phase 3: Automatic lid-close handling
- [ ] Phase 4: Multi-monitor support (3+ displays)
- [ ] Phase 5: Custom mode profiles
- [ ] Phase 6: GUI configuration tool

## License

MIT License - see LICENSE file for details

## Credits

- Built with [Textual](https://textual.textualize.io/) TUI framework
- Inspired by Windows Super+P functionality
- Made for [Hyprland](https://hyprland.org/) Wayland compositor

## Links

- **Repository**: https://github.com/yourusername/hyprmode
- **Issues**: https://github.com/yourusername/hyprmode/issues
- **Hyprland**: https://hyprland.org/
- **Textual**: https://textual.textualize.io/

---

**Made with ❤️ for the Hyprland community**
