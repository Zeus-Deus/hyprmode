# hyprmode — working notes for agents

hyprmode is a Hyprland display-mode switcher (Super+Shift+P TUI: laptop-only /
external-only / extend / mirror) plus a small emergency-recovery daemon.

## The one rule that matters: re-light disabled outputs with `hyprctl reload`

`hyprctl keyword monitor <name>,<settings>` is a **no-op on a connector that is
currently disabled** — Hyprland will not re-modeset a disabled output that way.
To bring a disabled display back you MUST use `hyprctl reload` (it re-reads the
monitor config and re-lights the connector). This was the root cause of the
black-screen-on-lid-open and failed-unplug-recovery bugs. `keyword monitor` is
fine for configuring an already-live output; never rely on it to re-enable one.

## Lid + disconnect handling is Omarchy-aware

- **On Omarchy** (`~/.local/share/omarchy` exists): hyprmode does NOT own lid or
  disconnect handling. Omarchy ships its own external-guarded, reload-based lid
  logic plus a `monitorremoved` watcher, and hyprmode's own lid config would
  conflict (both fire → races / black screen). `install.sh` detects Omarchy,
  skips writing `~/.config/hypr/lid-switch.conf`, and neutralizes any existing one.
- **On plain Hyprland**: hyprmode owns it. `install.sh` writes `lid-switch.conf`
  (external-guarded — only disables eDP when an external is connected, reload-based
  restore) and the recovery daemon watches for the 0-active-output condition and
  re-lights the panel via `hyprctl reload`.

## Don't touch

The Super+Shift+P TUI menu is hyprmode's core value and already recovers via
reload. Leave it intact unless you find a `keyword monitor` re-enable bug in it.
