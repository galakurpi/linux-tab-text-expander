# Linux Tab Text Expander

A small X11 text replacement daemon for Ubuntu / Pop!_OS. It watches typed shortcuts, shows a small hint when a shortcut is ready or when 3+ characters match a shortcut prefix, and expands the prompt when you press `Tab`.

`Tab` works normally unless a hint is visible. When a shortcut is active, the daemon grabs `Tab` at X11 level, clears the typed trigger, and inserts the expansion. If you just type a shortcut and keep typing, nothing is pasted.

## Install

Use an X11 desktop session. On Ubuntu, choose "Ubuntu on Xorg" from the login screen gear menu.

```bash
git clone https://github.com/galakurpi/linux-tab-text-expander.git
cd linux-tab-text-expander
./install.sh
```

The installer writes:

- `~/.local/bin/linux-tab-text-expander`
- `~/.config/linux-tab-text-expander/replacements.json`
- `~/.config/systemd/user/linux-tab-text-expander.service`

It installs system packages with `sudo` or `pkexec`, enables the user service, and imports the current X11 environment into systemd.

## Use

Type a trigger, wait for the hint, then press `Tab`.

Example: type `jr`, then press `Tab` to paste the junior-dev instruction prompt.

For longer triggers, hints also appear on partial matches after 3 typed characters. Example: `bug` shows the `bug` hint, `spa` shows the `spawn` hint, and pressing `Tab` expands the prompt.

## Edit Triggers

Edit:

```bash
~/.config/linux-tab-text-expander/replacements.json
```

Then restart:

```bash
systemctl --user restart linux-tab-text-expander
```

## Current Triggers

| Trigger | Label | Expansion |
| --- | --- | --- |
| `bug` | Fix a bug end to end | Reproduce the exact issue, then create a regression test. Then read all the code and logs that you need to read to pinpoint the exact issue precisely. Then make the smallest safe fix and actually test end to end if it is fixed. Iterate on this. Testing and checking and debugging until it works perfect. Once it does, add necessary documentation, follow karpathy skill. |
| `qa` | Browser dogfood QA | Use browser-harness/dogfood QA for this. Test the real user flow end to end with the project test account or documented credentials, capture screenshots/evidence, fix any scoped issues you find, then re-test until the flow works. Also when all finished and tested run a subagent with the autoreview skill to check the diffs, wait for it, apply the highest gains it finds, if it finds any being worth it. |
| `skill` | Use the right skill | Use the relevant YekarOS skill for this task. Read its SKILL.md first, follow its workflow, use its scripts/assets if present, and say briefly which skill you used and why. |
| `bloat` | Avoid bloat | Before adding anything, check for existing code/docs/data that already do this. Prefer reusing or simplifying existing paths, remove duplication if it is safely in scope, and avoid adding parallel systems. |
| `thorough` | Manual thorough check | Be thorough here. Do not sample if the task requires exhaustive checking. Read the relevant rows/files/items yourself, track what range you covered, list suspicious cases, and continue in batches until the whole scope is checked. |
| `explain` | Explain for a junior dev | Explain this in plain language for a junior dev and be concise. No long background unless it changes the decision. |
| `ship` | Implement and ship code | Take all the time you need to understand the requirements, read code, documentation, find patterns in other projects, etc. Implement the change end to end. Keep it scoped, follow existing patterns, push to main and deploy to production, once in production, run the relevant tests/build/lint, verify the real behavior actually end to end and in the closest way possible to reality, browser harness if it includes frontend changes, iterate until it works perfect. Update docs/memory only if durable, and leave a concise summary with evidence. |
| `absorb` | Absorb the code | Absorb this code deeply, truly understand how it works. Soak in the code and the features. |
| `jr` | Junior developer instruction | Actually imagine you're writing an instruction message for a junior developer to go work on this. Write something extremely clear and specific, including what files to look at for the change and what ones need to be fixed. |
| `spawn` | Spawn parallel agents | Spawn multiple agents in parallel - as many as you need to accomplish this task better and faster. Break the work into independent pieces, dispatch them concurrently, and synthesize the results when they return. Don't execute yet, show me a diagram of steps to take and what agent does each, and make sure that the logic is right so we don't mess it up with agents missing information etc, no logic fails in the diagram etc. |

## Terminal Notes

Terminal apps need special handling because `Tab` often means "submit", "queue", or "complete". This daemon consumes `Tab` at X11 level when a shortcut is active, clears the typed trigger, and types the expansion directly into the terminal.

If a terminal leaves one character from the trigger behind, set `TEXT_EXPANDER_TERMINAL_EXTRA_BACKSPACES=2` in the systemd service and restart it.

## Limitations

- X11 only.
- Wayland support is not implemented.
- The daemon reads trigger changes on restart.
