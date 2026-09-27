# Personal theme profile

`profile.json` describes the verified 21.1.0.14 Windows build. `assets/*.z` contains deduplicated zlib-compressed replacement fragments, including three banner sizes and nine Project Manager graphics. PNG padding is reconstructed to preserve original Qt resource lengths. All replacements are SHA-256 verified.

The profile contains 624 binary spans and 61 Fusion color assignments. It themes `Resolve.exe`, `BMDDavUI.dll`, and `Skins/Fusion.fuskin`, preserving bytes/archive members outside those changes. It is tied to this build, not a general patch generator.

Artwork: `banner-pink-bob.png`, created with built-in ImageGen from the earlier banner. Prompt: change only the woman's face and haircut to an adult anime woman with a soft oval face, violet eyes, delicate nose, subtle confident smile, and shoulder-length layered pink bob with wispy bangs. Remove the braid. Preserve the grassy field, cloudy sky, birds, lighting, black suit/tie, pose, wide 2.38:1 composition, right-hand character position and dark left space. No added text, logos, accessories, or people.

Installed artwork and Project Manager pink accents were visually verified after restart. Other orange icons/playheads and existing clip colors can remain. Applying the profile does not regenerate artwork or contact external services.

Run `python theme.py PATH_TO_RESOLVE --dry-run` to validate; omit `--dry-run` to apply. Add `--restore PATH_TO_STATE_JSON` to restore a session. Resolve must be closed for writes. Backups and application/project data stay on the machine. This personal branch remains public on the owner's fork.
