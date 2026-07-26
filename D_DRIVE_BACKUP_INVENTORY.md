# D: Drive Backup Inventory

Use this checklist before merging or reformatting D:. The destination below is intentionally a placeholder; replace it with the drive letter and folder for the 1 TB storage device.

```powershell
$backup = "E:\D-drive-backup"
New-Item -ItemType Directory -Force $backup
```

Do not delete or merge D: until the copy has completed, the verification commands pass, and the backup is readable from another machine if possible.

## Priority backup list

| Priority | D: path | Approx. size | Why keep it | Backup treatment |
| --- | --- | ---: | --- | --- |
| Required | `D:\Jon\Documents\software_eng\floof-matcher-3d-pipeline` | 1.1 GB | Existing computer-vision project and outputs | Back up the whole folder. Push source/history to a private GitHub branch after removing secrets and generated data. |
| Required | `D:\Jon\Documents\software_eng\floof-matcher-3d-pipeline\orchestrator\.env` | <1 MB | Project credentials/configuration | Copy only to encrypted/private storage. Never commit or push it. |
| Required | `D:\Jon\PS2_games` | 20.3 GB | Personal game collection | Copy the whole folder. Confirm the storage device has enough room. |
| Required | `D:\SteamLibrary` | 31 GB | Installed Steam games | Copy the whole library, or use Steam's backup/move workflow. Keep `steamapps` manifests. |
| Required | `D:\Jon\n64` | 0.1 GB | ROMs and emulator installer | Copy the whole folder and verify legal ownership of ROMs. |
| Required | `D:\Jon\Documents\Sound recordings` | unknown | Personal recordings | Copy the whole folder; inspect hidden files and subfolders. |
| Required | `D:\Jon\Johns Music`, `D:\Jon\Johns YouTube`, `D:\Jon\Music`, `D:\Jon\Pictures`, `D:\Jon\Videos` | currently near-empty in the scan | Personal media locations | Copy entire folders even if they appear empty; media may be hidden or added later. |
| Recommended | `D:\Jon\Documents\huggingface_cache` | 6.7 GB | Downloaded Qwen models and tokenizers | Copy if local AI work should continue without re-downloading. |
| Recommended | `D:\Jon\Downloads` | 5.7 GB | Includes the 5.7 GB AI4MARS dataset ZIP | Review contents, then copy wanted installers/datasets. |
| Optional | `D:\Jon\Blender` | 0.02 GB | Blender projects and assets | Copy the whole folder if the 3D assets are still wanted. |
| Optional | `D:\Jon\Unity`, `D:\Jon\Unity Hub` | negligible | Unity configuration/projects | Copy only if those projects are still active. |

The Windows folders (`Recovery`, `System`, `System64`, `WindowsApps`, `Program Files`, `SoftwareDistribution`, and similar) should not be manually copied as personal backups. Reinstall applications after the merge instead.

## Floof project GitHub handoff

Before pushing, inspect the project for secrets and generated data. The `.env` file and image/model outputs must remain offline. A safe source-only branch can be created from the project directory:

```powershell
Set-Location "D:\Jon\Documents\software_eng\floof-matcher-3d-pipeline"
git status
git switch -c backup/floof-matcher-before-drive-merge
git add .
git diff --cached --check
git commit -m "Backup Floof matcher before drive merge"
git push -u origin backup/floof-matcher-before-drive-merge
```

If the project is not already a Git repository, initialize it only after creating a `.gitignore` that excludes `.env`, `output/`, model weights such as `*.pt`, datasets, and other private data. Keep a separate offline copy of the `.env`.

## Copy commands

Use `robocopy` so interrupted copies can resume. Replace `E:` with the actual backup-drive letter:

```powershell
$backup = "E:\D-drive-backup"

robocopy "D:\Jon\Documents\software_eng\floof-matcher-3d-pipeline" "$backup\floof-matcher-3d-pipeline" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\PS2_games" "$backup\PS2_games" /E /Z /R:2 /W:5 /XJ
robocopy "D:\SteamLibrary" "$backup\SteamLibrary" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\n64" "$backup\n64" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\Documents\Sound recordings" "$backup\Sound recordings" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\Johns Music" "$backup\Johns Music" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\Johns YouTube" "$backup\Johns YouTube" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\Music" "$backup\Music" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\Pictures" "$backup\Pictures" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\Videos" "$backup\Videos" /E /Z /R:2 /W:5 /XJ
robocopy "D:\Jon\Documents\huggingface_cache" "$backup\huggingface_cache" /E /Z /R:2 /W:5 /XJ
```

Copy the Floof `.env` separately into a clearly marked private location, for example `$backup\PRIVATE\floof-matcher-3d-pipeline.env`, and restrict access to the backup drive.

## Verification checklist

- [ ] The backup drive has at least 70 GB free for the required items, plus room for optional datasets/models.
- [ ] Every `robocopy` command finished with an exit code below 8.
- [ ] Compare file counts and sizes:

  ```powershell
  robocopy "D:\Jon\Documents\software_eng\floof-matcher-3d-pipeline" "$backup\floof-matcher-3d-pipeline" /E /L /BYTES /NJH /NJS
  ```

- [ ] Open representative game, media, project, and model files directly from the backup drive.
- [ ] Confirm the private `.env` exists on the backup drive and is not in the GitHub branch.
- [ ] Keep the backup disconnected or read-only until the D: merge is complete and the restored files are tested.
