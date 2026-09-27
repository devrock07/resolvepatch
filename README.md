# resolvepatch — devrock07's personal Blackpink branch

Personal customization branch for my Windows Resolve setup. **Public fork, personal branch; no upstream merge intended.** The existing patch command now validates and applies my saved Blackpink theme after its original patch operation succeeds.

Verified for **DaVinci Resolve Studio 21.1.0.14, Windows x64** only: black panels, pink/rose controls, Fusion colors, pink Project Manager selection borders/tab graphics, and the anime banner with violet eyes and a layered pink bob.

![Personal loading artwork](personal/banner-pink-bob.png)

Some timeline clip colors and other embedded orange icons remain independent of this theme. This is not a claim that every Resolve pixel is pink.

## Build and run

Requires Windows, Python 3.10+ (standard library only), and nightly Rust with MSVC build tools. Applying the saved theme needs no API key or network connection.

```powershell
git switch personal-blackpink
rustup toolchain install nightly --profile minimal
.\build-personal.ps1

# Inspect an existing installation without writes:
.\target\personal-bundle\resolvepatch.exe --theme-only --dry-run "F:\davinci\Resolve.exe"

# Close Resolve, then reapply just the theme:
.\target\personal-bundle\resolvepatch.exe --theme-only "F:\davinci\Resolve.exe"

# Fresh compatible installation: original patch, then theme automatically:
.\target\personal-bundle\resolvepatch.exe "F:\davinci\Resolve.exe"
```

Keep `personal/` beside the distributed executable. A direct `cargo +nightly build --release --locked` also works inside this checkout. `RESOLVEPATCH_PERSONAL_DIR` selects a custom profile folder; `RESOLVEPATCH_PYTHON` selects a Python executable.

`--dry-run` validates without writes. `--theme-only` is safe to repeat. `--no-theme` preserves the original patch workflow for versions without a personal profile. Combining `--theme-only` and `--no-theme` is rejected.

The original patch still rejects already-patched executables. Use **`--theme-only`** on your current installation. Original patch details and historical compatibility notes are in [LEGACY.md](LEGACY.md).

## Automatic application and compatibility

The theme runs automatically after a successful patch on this personal branch. Reapplying restores the saved theme after reinstalling the **same supported build**. It does not update Resolve, monitor installations, or guess offsets for future releases. A new Resolve build needs a newly inspected profile; unknown builds fail before patching unless `--no-theme` was explicitly selected.

Preflight validates file sizes, all unmodified bytes against known build fingerprints, every replacement span, and the Fusion archive. Both the locally verified original and previously patched executable are recognized. Unrelated edits or a different theme are rejected.

All theme files are validated before writes, backed up, and staged on the installation drive. Each replacement is atomic. If replacement fails, completed theme replacements are rolled back when their hashes still match. This is not a single atomic transaction across three files: interruption can require recovery from the saved manifest. If the original patch succeeds but theming fails, the original patch remains applied; fix the reported issue and rerun `--theme-only`.

## Restore

Backups stay under `.blackpink-backups/<session>/` in the Resolve installation. The command prints the exact manifest path. Sessions are never overwritten. Close Resolve and run:

```powershell
python .\personal\theme.py "F:\davinci\Resolve.exe" --restore "F:\davinci\.blackpink-backups\SESSION\state.json"
```

Restore verifies backup and current-file hashes, refuses unexpected changes, and creates an undo backup. It returns files to their state before that theme session, preserving any earlier original patch. The original patch's `Resolve.exe.bak` is separate.

## Contents and checks

Includes scripts, a build-specific recipe, compressed replacement fragments, and generated artwork. **No full Resolve executables, DLLs, Fusion archives, projects, license files, or backups are included.** Theme code does not change licensing; it retains the fork's existing patch behavior.

```powershell
cargo +nightly fmt -- --check
cargo +nightly test --locked
python -m unittest discover -s personal -p test_theme.py -v
.\build-personal.ps1
```

Tests cover repeat application, unknown inputs, corrupt assets, archive preservation, failed-replacement rollback, and restore refusal after unrelated edits. See [personal/README.md](personal/README.md) for profile/artwork details.
