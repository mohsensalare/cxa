# cxa

Switch between Codex CLI accounts from your terminal, and see how much of each one is left.

Codex keeps exactly one signed-in account in `~/.codex/auth.json`. `cxa` snapshots that file
per account and swaps it back in on demand, so changing accounts costs no browser round trip
and never needs `codex logout`.

```
$ cxa status
  account       email                     5h    weekly  next reset  resets   role     seen
~ work          you@example.com           98%   41%     3h 30m      -                 1h ago
* spare         other@example.com         -     57%     5d 12h      1·10/05  reserve  11m ago
  * active   ~ next up
```

```
$ cxa
codex account
> * work    you@example.com     plus   5h 98% · wk 41% resets 3h 30m
    spare   other@example.com   plus   wk 57% resets 5d 12h
  ~ rotate to the account with the most headroom
  o mark an account as reset
  + log in to a new account
  x delete an account
type to search, up/down, enter, esc
```

## Install

One file, no dependencies, Python 3.8+, macOS or Linux.

```bash
curl -fsSL https://raw.githubusercontent.com/mohsensalare/cxa/main/cxa -o ~/.local/bin/cxa
chmod +x ~/.local/bin/cxa
```

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

ChatGPT sometimes grants a "usage limit reset" under Settings. `cxa sync` reads how many are
left and when they expire, and shows them in the `resets` column as `1·10/05`.

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

## Security

`~/.codex/accounts` holds live OAuth tokens, one file per account, `chmod 600` inside a `700`
directory. Anything that can read those files can act as you.

Keep that directory out of git, Dropbox, iCloud, and any dotfiles repo.

## License

MIT
