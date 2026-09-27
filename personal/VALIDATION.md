# Local validation — 2026-09-27

- Rust formatting, three existing Rust regression tests, and release build passed.
- Six installer tests passed: idempotence and unknown-build checks, asset integrity, invalid ranges/paths, Fusion preservation, simulated replacement-failure rollback, and verified restore.
- The bundled executable's `--theme-only --dry-run` recognized the installed theme and reported zero changes.
- The combined `--dry-run` command validated the personal profile and the existing patch signatures against a separate copy of the original 21.1.0.14 executable.
- On isolated copies of the earlier patched executable, original shared UI DLL and original Fusion skin, applying this profile produced SHA-256 matches for all three currently installed themed files.
- Reapplying generated no changes. Restoring recovered all three baseline files byte for byte.
- Live application files were not modified by these repository integration tests. The original patch was dry-run only; theme transactions were exercised on the isolated copies.

Earlier manual application checks verified startup with the current pink-bob banner and pink Project Manager selection border/Local underline. Automated tests do not establish compatibility with newer Resolve builds or verify every editing/rendering feature.
