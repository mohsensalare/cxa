# cxa

Switch between Codex CLI accounts from your terminal, and see how much of each one is left.

Codex keeps exactly one signed-in account in `~/.codex/auth.json`. `cxa` snapshots that file
per account and swaps it back in on demand, so changing accounts costs no browser round trip
and never needs `codex logout`.

```
$ cxa status
                                                5h             weekly
  account       email                     plan  left  resets   left  resets   credits     role     seen
~ work          you@example.com           plus    2%  3h 30m    59%  Sep 13   3 Sep 21             1h ago
* spare         other@example.com         plus     -             43%  Sep 15   -           reserve  11m ago
  * active   ~ next up   |   percentages are what is LEFT, not what you used
```

```
$ cxa
codex accounts
                                          5h             weekly
                                          left  resets   left  resets   credits
> * work    you@example.com     plus        2%  3h 30m    59%  Sep 13   3 Sep 21
    spare   other@example.com   plus         -             43%  Sep 15   -
  ~ rotate to the account with the most headroom
  s refresh every account from ChatGPT
  o mark an account as reset
  + log in to a new account
  x delete an account
type to search  ·  tab refreshes a line  ·  enter switches  ·  esc quits
```

## Install

One file, no dependencies, Python 3.8 or newer. macOS, Linux and Windows.

### macOS and Linux

```bash
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/mohsensalare/cxa/main/cxa -o ~/.local/bin/cxa
chmod +x ~/.local/bin/cxa
```

If `cxa` is not found afterwards, `~/.local/bin` is not on your `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
```

> On macOS, keep the file outside `~/Documents`, `~/Desktop` and `~/Downloads`. Those folders
> are TCC-protected, and a Homebrew Python is refused permission to read a script inside them.

### Windows

Run in PowerShell. This installs to your user profile and needs no administrator rights.

```powershell
$dir = "$env:LOCALAPPDATA\Programs\cxa"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Invoke-WebRequest -UseBasicParsing `
  -Uri https://raw.githubusercontent.com/mohsensalare/cxa/main/cxa `
  -OutFile "$dir\cxa.py"

@'
@echo off
where py >nul 2>nul
if %errorlevel%==0 (py -3 "%~dp0cxa.py" %*) else (python "%~dp0cxa.py" %*)
'@ | Set-Content -Encoding ASCII "$dir\cxa.cmd"

$path = [Environment]::GetEnvironmentVariable("Path", "User")
if ($path -notlike "*$dir*") {
    [Environment]::SetEnvironmentVariable("Path", "$path;$dir", "User")
}
```

Open a new terminal, then run `cxa`. Windows Terminal is worth using over the old console
window: cxa switches on VT processing either way, but Windows Terminal renders colour properly
and is not stuck at 80 columns.

> If you run Codex inside WSL, install `cxa` **inside WSL** with the Linux instructions above.
> Codex keeps its login in the filesystem it runs in, and a Windows-side `cxa` would be looking
> at a different `.codex` directory.

## Use

Run `cxa` with no arguments and pick from the menu — it holds everything below, so there is
nothing to memorise. The verbs are there for when you are in a hurry.

| Command | What it does |
| --- | --- |
| `cxa` | menu: type to search, arrows to move, enter to pick |
| `cxa <name>` | switch straight to a saved account |
| `cxa save [name]` | save the current login (name defaults to the email prefix) |
| `cxa login [name]` | log in to another account and save it |
| `cxa status` | usage and reset time per account |
| `cxa sync [name]` | refresh usage from ChatGPT — all accounts, or one |
| `cxa auto` | switch to the account with the most headroom |
| `cxa reset <name>` | you used that account's reset — clear its cached usage |
| `cxa resets <name> <count> [YYYY-MM-DD]` | record reset credits and their expiry |
| `cxa rm <name>` | delete a saved account |

Adding a second account: run `cxa`, pick **log in to a new account**. Your current login is
snapshotted first, so it survives. Open the login link in a private window — otherwise the
browser signs you straight back into the account you are already using.

In the menu, **Tab** refreshes whatever line you are sitting on without leaving it.

Every percentage in `cxa` is what is **left**, matching the Codex usage panel — `0%` means that
window is used up, not untouched. Each window carries its own reset, as a countdown while it is
close and a date once it is not:

```
                                                5h             weekly
  account       email                     plan  left  resets   left  resets   credits     role    seen
  work          you@example.com           team    0%  3h 18m    58%  Sep 13   3 Sep 21    spent   10m ago
* spare         other@example.com         plus   32%  2h 55m     0%  Sep 12   -           spent   4m ago
```

## How the usage numbers work

Codex records its rate-limit windows in its own session logs under `~/.codex/sessions`:

```json
{"primary":   {"used_percent": 98, "window_minutes": 300,   "resets_at": 1788656092},
 "secondary": {"used_percent": 41, "window_minutes": 10080, "resets_at": 1789205425}}
```

`cxa` reads only the tail of each log, so a 2 GB session directory costs a few megabytes of
reads. Two details make this harder than it looks:

- **Logs do not say which account they belong to.** `cxa` journals every switch it makes and
  attributes each observation to whichever account was active at that moment.
- **`primary` is not always the short window.** On one account `primary` is the 5-hour window;
  on another it is the weekly one. `cxa` sorts windows by `window_minutes`, never by key name.
- **The logs count upwards, the Codex usage panel counts downwards.** `used_percent: 68` is the
  same thing the panel shows as `32%`. `cxa` displays headroom under a `left` heading, so its
  numbers can be read straight against the panel.

This part is entirely offline — it only reads and copies local files.

### Why `cxa sync` exists

Local logs have two blind spots. An account you have not used lately shows numbers from
whenever you last used it, and sessions run from the ChatGPT desktop app leave no local log at
all, so the figures quietly freeze.

`cxa sync` closes both by asking ChatGPT directly, using the access token already in that
account's snapshot:

```
GET https://chatgpt.com/backend-api/wham/usage
GET https://chatgpt.com/backend-api/wham/rate-limit-reset-credits
```

These are the only network calls `cxa` makes, they are read-only, and they only ever run when
you ask — `cxa sync`, or Tab in the menu. Everything else still works with the network off.

Both endpoints are undocumented and may change or disappear without notice. When a call fails,
`cxa` says so on that account's line and falls back to the local logs.

## How rotation picks an account

`cxa auto` ranks accounts best-first:

1. **ready** — has a 5-hour window with room left, lowest usage first
2. **unused** — no data yet
3. **reserve** — weekly-only, no short window
4. **spent** — some window has hit the limit

Short windows refill every few hours, so those accounts are spent first and a weekly-only
account is kept in reserve. Ties on the 5-hour window are broken by the weekly one.

Set `CXA_FULL=95` to treat a window as spent before it reaches 100%, which rotates you off an
almost-empty account instead of squeezing the last few requests out of it.

## Reset credits

ChatGPT sometimes grants a "usage limit reset" under Settings - one credit clears both the 5h
and the weekly window. `cxa sync` reads how many are left and when the first one expires, and
shows them in the `credits` column as `3 Sep 21`.

You can also keep them by hand, which is what you want when you would rather not make network
calls at all:

```bash
cxa resets spare 1 2026-10-05    # one reset, expires Oct 5
cxa reset spare                  # you just used it
```

`cxa reset` zeroes the account's cached usage as well as the counter — without it, `cxa` would
keep ranking on numbers from before the reset.

## Caveats

- A running Codex session keeps the token it already loaded. `cxa` warns when it finds a CLI
  session and notes when the desktop app is up; restart them after switching.
- Without `cxa sync`, usage figures come from the last time you actually used each account —
  and sessions run from the ChatGPT desktop app never write local logs at all.
- `cxa sync` needs each account's stored access token to still be valid. If it has expired,
  switch to that account once so Codex refreshes it.
- Switching outside `cxa` (a manual `codex login`, say) breaks the journal's attribution until
  the next switch through `cxa`.
- The table drops the email column when the terminal is too narrow for it, which an 80-column
  Windows console is. Widen the window to get it back.

## Security

`~/.codex/accounts` (`%USERPROFILE%\.codex\accounts` on Windows) holds live OAuth tokens, one
file per account. Anything that can read those files can act as you.

On macOS and Linux they are written `chmod 600` inside a `700` directory. Windows has no
equivalent worth calling from a script, so they inherit the profile's ACL — private to your
user account, but readable by an administrator.

Keep that directory out of git, Dropbox, OneDrive, iCloud, and any dotfiles repo.

## Development

`cxa` is one file with no dependencies, so there is nothing to build. The Windows branches can
be checked from macOS or Linux, which is how they were written:

```bash
python3 test_windows.py
```

## License

MIT
