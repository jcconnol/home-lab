# D: Drive Backup Checklist

This is an inventory only. No files have been copied. The intended backup destination is:

`F:\Moving Desktop Backup`

Do not merge, reformat, or delete D: until the items below have been copied and checked from the external drive.

## Back up these items

### Floof project

- [ ] `D:\Jon\Documents\software_eng\floof-matcher-3d-pipeline`
- [ ] `D:\Jon\Documents\software_eng\floof-matcher-3d-pipeline\orchestrator\.env`

Keep the `.env` only on the private external backup. Do not commit or push it to GitHub. The Floof source can also be pushed to a private branch after removing `.env`, generated `output/` data, model weights, and other secrets.

### Games

- [ ] `D:\SteamLibrary` — Steam games and manifests
- [ ] `D:\Jon\PS2_games` — PS2 game files
- [ ] `D:\Jon\n64` — N64 files and emulator installer

### Personal media

- [ ] `D:\Jon\Documents\Sound recordings`
- [ ] `D:\Jon\Johns Music`
- [ ] `D:\Jon\Johns YouTube`
- [ ] `D:\Jon\Music`
- [ ] `D:\Jon\Pictures`
- [ ] `D:\Jon\Videos`

Copy the folders even when they appear empty so the personal-media locations are preserved.

## Explicitly do not back up

- `D:\Jon\Documents\huggingface_cache` (AI models can be redownloaded)
- `D:\Jon\Downloads\ai4mars-dataset-merged-0.1.zip` and other disposable datasets
- Windows/system folders: `Recovery`, `System`, `System64`, `WindowsApps`, `Program Files`, `SoftwareDistribution`, and similar
- Installers you no longer need, caches, generated outputs, and temporary files

## Destination layout

Use this layout on the external drive:

```text
F:\Moving Desktop Backup\
├── Floof\
│   ├── floof-matcher-3d-pipeline\
│   └── PRIVATE\floof-matcher-3d-pipeline.env
├── Games\
│   ├── SteamLibrary\
│   ├── PS2_games\
│   └── n64\
├── Personal Media\
│   ├── Sound recordings\
│   ├── Johns Music\
│   ├── Johns YouTube\
│   ├── Music\
│   ├── Pictures\
│   └── Videos\
```

## Final checks

- [ ] The external drive opens and the expected folders are present.
- [ ] Open representative Floof files, game files, and personal media directly from `F:\Moving Desktop Backup`.
- [ ] Confirm the private `.env` exists on the external drive and is absent from the GitHub branch.
- [ ] Keep the external drive disconnected or read-only until the D: merge is complete.
