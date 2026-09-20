# Install Research Retro

Research Retro uses your existing strong Agent for scientific reconstruction. It
does not require a particular Agent SDK, developer checkout or migrated project.
Python 3.11+ and POSIX are required; the tested platform is Linux x86_64 with
CPython 3.14.4. Other Python/POSIX combinations and native Windows are untested.

## Ordinary installation

Use a separate environment and the wheel in this directory:

```sh
python3 -m venv retro-env
retro-env/bin/python -m pip install ./research_retro-3.6.0-py3-none-any.whl
retro-env/bin/retro start /path/to/project --workspace /path/to/project.retro
```

Give `/path/to/project.retro/START_HERE.md` and your actual research goal to your
Agent. It contains the installed workflow and input examples. The source project
stays read-only; investigations, scripts and scientific state live in the separate
workspace. Run the same `start` command to resume. Add `retro-env/bin` to your
shell PATH if you want the shorter `retro` command.

For a configured cheap worker and local Jev judgments, use:

```sh
retro start /path/to/project --workspace /path/to/project.retro --worker dsh --jev
retro -w /path/to/project.retro discover
```

The second command handles preparation, candidate generation and authorized local
judgments, then writes `discovery/latest.md`. Run it again for the next batch.
The Agent follows useful candidates into original checks and records understanding.
It need not hand-wire the low-level packet commands. `--question` explores a new
scientific question; `--overview` shows only material families without model calls.

Codex, Claude Code, Pi, OpenCode and other shell-capable hosts can use the same CLI.
`retro tools` provides JSON functions and `retro skill --destination NEW_DIRECTORY`
copies the host skill. Actual Agent evaluation used the current Codex host only;
other hosts have interface compatibility, not an empirical acceptance claim.

## Offline installation on the tested platform

`wheelhouse-linux-cp314.tar.gz` contains the product, pip and all runtime dependency
wheels. Its binary dependency requires ordinary CPython 3.14 on Linux x86_64,
not the free-threaded 3.14 build. For another platform, prepare matching dependency
wheels separately; the product wheel is pure Python.

```sh
tar -xzf wheelhouse-linux-cp314.tar.gz
python3.14 -m venv retro-env
retro-env/bin/python -m pip install --no-index --find-links ./wheelhouse research-retro
retro-env/bin/retro start /path/to/project --workspace /path/to/project.retro
```

On systems without `ensurepip`, create the environment with `--without-pip` and
bootstrap from the included pip wheel:

```sh
python3.14 -m venv --without-pip retro-env
retro-env/bin/python -I -c 'import runpy,sys;sys.path.insert(0,"wheelhouse/pip-26.2.1-py3-none-any.whl");sys.argv=["pip","--isolated","install","--no-index","--find-links","wheelhouse","research-retro"];runpy.run_module("pip",run_name="__main__")'
```

These offline wheels were installed and exercised without the developer home,
source checkout or network. See `acceptance.json` and `receipts.tar.gz`.

## Use and hand off

The host surveys material families, gives bounded packets to a cheap worker, and
uses Jev to judge proposed local relations before scientific synthesis. The strong
host follows that queue into original checks and saves understanding with `record`.
`spine` selects a short reading order. The generated protocol contains complete JSON
examples; users do not need to fill in a graph before work can begin.

```sh
retro -w /path/to/project.retro discover
retro -w /path/to/project.retro workflow publish
retro -w /path/to/project.retro export
retro inspect /path/to/exported-bundle
```

Read `current/SPINE.md` or `current/index.html` first; `RESEARCH_MAP.md` has the
details and `SOURCE_INDEX.json` resolves original bytes and retained checks.
An export is a frozen handoff. Continue revisions in the active workspace; add a
new read-only evidence directory with `retro -w WORKSPACE add-source DIRECTORY`.

Jev is optional. `start --jev` authorizes explicitly chosen state/questions to
TypeSafe using `TYPESAFE_API_KEY`; enter credentials locally, never in a handoff.
Configured discovery and explicit `triage judge`, `triage impact`, `judge` or `semantic-review` calls send selected data. Calls and failures are
retained; the model's probability does not block or certify scientific claims.

Any host worker can return the candidate JSON. `triage generate` also runs an
explicit JSON stdin/stdout command; the packaged protocol includes an optional
`dsh --profile headless` example. The actual development run used dsh's configured
`deepseek-flash` (DeepSeek-V41-Flash), then Jev, then a fresh strong Agent. dsh is not
a product dependency. Configure the intended worker model in your host; Retro does
not alter its defaults. Without Jev, use the same original-check and record loop
directly. For later material, `add-source` followed by `triage impact` produces
candidate effects before the host decides which interpretations/actions to revise.

`example-handoff.tar.gz` is a small **synthetic software-acceptance example**. Unpack
it, run `retro inspect example-handoff`, and open its `START_HERE.md`. It is not the
real research evaluation dataset or a scientific benchmark result.
