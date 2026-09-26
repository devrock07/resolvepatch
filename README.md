# resolvepatch

A Windows research patcher for DaVinci Resolve Studio, with patch paths for versions 18 through 21.

## Compatibility

| Version | Status |
| --- | --- |
| 18.6.2 and 20.0.49 | Previously reported working by upstream; not retested for this change. |
| Other 18.x–20.x builds | Existing patch paths; compatibility depends on matching signatures. |
| 21.0.0 / 21.0.4+ | Existing v21 signature variants; not separately tested for this change. |
| **21.1.0.14 (Windows)** | **A local patch run succeeded:** the v21 dialog pattern, all five render-guard patterns, and the Dolby Vision patch completed. Application startup, editing, rendering, and Dolby Vision output have **not** been verified. |
| Earlier than 18 or later than 21 | Rejected; no compatibility claim. |

Version 21 support was already present in the source. This update documents it and improves execution safety; it does not introduce or independently validate those signatures. A successful patch run is not proof that every Studio feature works. Missing or ambiguous required signatures abort before the executable is written. Already-patched executables are rejected rather than reported as newly patched.

## Build

Install [Rust](https://rustup.rs/) on Windows with the MSVC build prerequisites. The `coolfindpattern` dependency requires nightly Rust.

```powershell
rustup toolchain install nightly --profile minimal
cargo +nightly build --release --locked
```

The executable is `target\release\resolvepatch.exe`. Nightly Rust 1.100.0 (2026-09-26 toolchain) was used for this change.

## Usage

Close Resolve before applying changes. Installations under Program Files may require an elevated terminal for file access.

```powershell
# Inspect a custom installation without writing files or registry settings:
.\target\release\resolvepatch.exe --dry-run "D:\Apps\DaVinci Resolve\Resolve.exe"

# Apply to that installation:
.\target\release\resolvepatch.exe "D:\Apps\DaVinci Resolve\Resolve.exe"

# Or use automatic detection (file associations, then the default install path):
.\target\release\resolvepatch.exe
```

`--help` prints usage. Exit code 0 means the requested operation completed; errors return a nonzero exit code. Dry runs still require an original, unpatched executable.

## Backups and configuration

- A backup is created as `Resolve.exe.bak` before writing the executable. Existing backups are never overwritten: move a verified backup to a separate safe location before deliberately patching a fresh installation again.
- The license file is written alongside Resolve, preserving prior behavior for legacy versions as well.
- `RLM_LICENSE` is configured in the current user's environment using the license file's absolute path. Sign out and back in so applications inherit the new value. This replaces the previous attempt to write through a read-only machine registry handle.
- License configuration failure returns an error even if the executable has already been modified. The backup remains available. Executable writes are not atomic; restore the backup if a write is interrupted.

To restore, close Resolve and copy the verified `Resolve.exe.bak` over `Resolve.exe`. Remove this tool's license file and user environment setting if no longer needed; preserve any unrelated configuration.

## Development checks

```powershell
cargo +nightly fmt -- --check
cargo +nightly test --locked
cargo +nightly build --release --locked
```

Regression tests cover signed relative-call bounds, malformed file-association commands, and refusal to overwrite an existing backup. They do not validate Resolve's runtime behavior.

## Disclaimer

This is a research project and is not intended to allow piracy.
