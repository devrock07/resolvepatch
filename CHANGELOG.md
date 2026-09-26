# Changelog

## Unreleased

- Document existing Resolve 21 support and the limited 21.1.0.14 patch-run validation.
- Accept explicit executable paths and offer `--dry-run` / `--help`.
- Refuse unsupported major versions and abort on missing or ambiguous required signatures.
- Resolve signed relative-call displacements with checked arithmetic and validate the function search window.
- Preserve existing backups, use meaningful process exit codes, and propagate configuration errors.
- Configure the user environment with a writable registry handle and an absolute license path.
- Parse quoted file-association commands without unchecked string slicing.
- Document nightly Rust and add regression coverage for failure-prone helpers.
