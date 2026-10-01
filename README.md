# herdr-pane-pull

Pull panes from any workspace into the tab you are in, and send one back out
when you are done. A [herdr](https://herdr.dev) plugin.

Most pane movers send the focused pane somewhere else, so gathering three
sessions means visiting each one. This one works from where you already are:
open the picker, mark the sessions you want, and they arrive next to you.

Panes are relocated with `herdr pane move`, never respawned. Agents and shells
keep running.

## Requirements

- herdr `>= 0.7.4`. Tested on 0.9.3.
- `python3`
- [`fzf`](https://github.com/junegunn/fzf) on `PATH`

## Install

```bash
herdr plugin install Unayung/herdr-pane-pull
```

The install runs a self-test and stops if `python3` or `fzf` is missing.

Keybindings live in your config, not in the plugin. Add these to
`~/.config/herdr/config.toml`:

```toml
[[keys.command]]
key = "alt+m"
type = "plugin_action"
command = "unayung.pane-pull.open"
description = "pull panes from anywhere into this tab"

[[keys.command]]
key = "alt+shift+m"
type = "plugin_action"
command = "unayung.pane-pull.exile"
description = "send this pane to its own workspace"
```

Then reload:

```bash
herdr server reload-config
```

## Pull panes in

Press `alt+m`. A popup lists every pane outside the current tab with its agent
status, title, workspace, tab and working directory. The lower half previews
the screen of the pane under the cursor.

| key | action |
| --- | --- |
| type | filter |
| `tab` | mark a pane; mark as many as you like |
| `enter` | pull the marked panes in, split right |
| `alt-d` | pull them in, split down |
| `esc` | cancel |

The focused pane and the panes you pull share its space equally, in the order
you marked them. Pull two into a full-width pane and you get three columns.
Focus stays on the pane you started from. A tab or workspace left empty by the
move is closed by herdr.

## Send a pane out

Focus a pane and press `alt+shift+m`. It moves to a new workspace of its own and
you stay in the tab you were in.

## Zoomed tabs

herdr will not move a pane out of or into a zoomed tab. It answers the request
with success and `changed: false`, which looks like nothing happened. The plugin
un-zooms the tab first.

Two things follow from that:

- A source tab you pull from is left un-zoomed.
- Un-zooming a tab switches the view to it, so the screen flickers to the source
  tab and back. There is no flicker when the source was not zoomed.

## Development

```bash
git clone https://github.com/Unayung/herdr-pane-pull
herdr plugin link ./herdr-pane-pull
python3 herdr-pane-pull/pane_pull.py selftest
```

The picker is a popup, which is not a pane, so `herdr pane send-keys` cannot
drive it. To exercise it, run the script in an ordinary pane and supply the
context herdr would have passed:

```bash
HERDR_PLUGIN_CONTEXT_JSON='{"focused_pane_id":"w1:p1","tab_id":"w1:t1"}' python3 pane_pull.py
```

## License

[MIT](LICENSE)
