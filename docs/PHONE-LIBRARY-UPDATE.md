# Phone viewing and library workflow update

This update extends the existing app. It keeps the same database, photos, training labels, datasets, model files and Cloudflare configuration. Do not create a new data directory or retrain your models for this update.

## Changes

- The photo viewer fits portrait phones and landscape screens without expanding beyond its column. Library tiles show the entire image rather than cropping the bottom.
- Each carousel thumbnail displays its provisional technical score and photo number. Open review concerns have an amber outline. **Show only photos needing review** filters navigation to those photos; whole-shoot concerns apply to all photos.
- Tap/click the left or right side of the main image to go backward or forward. The existing arrow controls remain available.
- Search shot types when labeling uploads or stored photos. Selecting a result closes the picker and dismisses its text input.
- In **Dealership Setup → Shot types → Manage categories**, rename, move up/down, or delete categories. Deletion hides them from new choices; restore them under Deleted categories. Remove references from current dealership/group rules first. Other and Unassigned remain available as fallbacks. Renaming keeps the permanent category key; use it for wording corrections, not to change the category's meaning. Existing labels, model classes and exported datasets are retained. Remembered/default sequences replace deleted categories with Unassigned in the same positions.
- The home priority card becomes quiet when no reviews are open and remains a link to the queue.
- Use the **••• → Edit vehicle** menu in either library, or **Edit vehicle** inside a shoot, to correct its metadata. Changing dealership, inventory type or QC mode queues analysis using the corrected dealership's current standards. Previous analysis runs retain their original policy snapshots. Other edits do not reanalyze or alter labels.
- **Use all photos for training** adds all active photos in the shoot. Clear it to remove all memberships; an individual photo's **Add to Training Library** checkbox only changes that photo. A mixed checkbox means some photos are selected. Clicking it adds the remaining photos; clicking the checked checkbox clears all. Original evaluation photos remain available. Removed memberships retain their labels in Training Trash. Re-adding an existing example preserves its labels and leaves approval off for review; newly added examples use the existing Good/approved defaults. Already included photos are left alone.
- Training views show only the selected training photos and link to the full vehicle in Photo Library. Green training approval is explicitly separate from review resolution: an approved defect example can still have an unresolved concern. Resolved reviews retain their concern text and resolution.
- Readable names use year, make, model, dealership/source, stock and sequence number (where entered), for example `2024_Ford_Escape_Example_Dealer_U123_001.jpg`. They appear in the viewer and on **Download**. Original filename remains in Photo & vehicle details. Stored UUID paths and original image bytes are unchanged. Correcting metadata updates the readable name without moving a file.
- Home and Training Library show collection guidance. Targets of 50 unique approved photos per selected shot category and 10+ vehicle groups are rough starting goals, not proof of readiness. Exact duplicates count once. Defect collection bars target 20 human-labeled examples per problem category for future quality models; the current ML model only learns shot types. Dealership coverage is informational because the classifier is shared. Actual training still requires independent train/validation/test coverage and evaluation.

## Database migration and compatibility

On first startup, schema 2 migrates to schema 3. The app makes `migration-backups/before-v3.db` within the existing data directory before adding:

- `shot_types.archived` (false for existing categories).
- `vehicle_shoots.metadata_revision` (0 for existing vehicles), to reject conflicting metadata saves from different users.

No existing rows are removed or rewritten by this migration. Schema 1 installations migrate through schema 2 first. Keep a complete backup of the data folder: the migration backup is database-only, not a copy of photos or models. Do not run old schema-2 code against the upgraded database. For rollback, stop the app and restore the matching code and your complete pre-update backup together.

## Update your Windows PC

Your domain and tunnel do not need to be recreated. Phone users do not install a new app; refresh their browsers after the PC update.

1. Finish active uploads and evaluations. In the PowerShell window running the app, press **Ctrl+C**. **Keep that window open**: it holds your working Cloudflare environment settings.
2. Confirm you are in your existing project folder:

   ```powershell
   Set-Location "G:\vehicle-photo-qc-main\vehicle-photo-qc-main"
   ```

3. In that same window, check the current data location:

   ```powershell
   $env:QC_DATA_DIR
   ```

   If it prints a path, that is the folder to back up. If it is blank, the default is the `data` folder directly inside the project. With the app stopped, copy the **entire data folder** to a safe backup location. Keep the existing folder in place.
4. Download the latest project ZIP from GitHub (**Code → Download ZIP**) and extract it to a temporary folder. Copy the **contents** of the extracted project folder into the existing project folder above, replacing code files. The folder containing `pyproject.toml`, `app`, and `scripts` is the project root. Do not create another nested project folder. Preserve your `data` folder, `.venv`, and any `remote-config.json` file. The GitHub download does not contain your private data or remote configuration.
5. In the same original PowerShell window, run these commands one at a time. They do not require executing a PowerShell script or changing execution policy:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
   .\.venv\Scripts\python.exe -m pip install --no-deps -e .
   Push-Location app\frontend
   npm.cmd ci
   npm.cmd run build
   Pop-Location
   ```

   If any command fails, stop and report the error before restarting.
6. Check that the working remote configuration is still present, without printing your AUD:

   ```powershell
   $env:QC_PUBLIC_URL
   $env:QC_ACCESS_TEAM_DOMAIN
   [bool]$env:QC_ACCESS_AUD
   ```

   For your setup these should show `https://app.stagenowqcs.com`, `stagenowqcs.cloudflareaccess.com`, and `True`. If any are missing, restore the same working values using the remote-access guide before continuing. An existing `remote-config.json` is only loaded by the remote startup script, not by the manual command below.
7. Start the app in that same window, keeping the same data-folder setting:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn qc.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
   ```

8. Wait for **Application startup complete**. Refresh `https://app.stagenowqcs.com` on the PC and phone. If a browser retains the previous interface, reload it (Ctrl+F5 on PC). Leave the host PC awake and the app window open.

## Checks on your devices

- Open an existing vehicle in both libraries with the phone upright. Check that the entire image fits, the carousel scrolls sideways, and side taps change photos without jumping the page.
- Search for a shot type using the Android keyboard, select it and confirm the keyboard closes. Physical keyboard behavior still needs a real Android test.
- In a test shoot, add all photos to training, deselect one, and confirm only the remaining photos appear in Training Library. Follow the full-vehicle link to verify all original evaluation photos remain.
- Edit a test vehicle's stock/year; confirm its readable filename changes. Changing its dealership should queue fresh analysis.
- On the PC, check library photo framing, score/date/dealer information, hover details, and review outlines.
- Try adding, renaming, moving, deleting and restoring a temporary shot category.

Automated checks cover original-byte and historical-label preservation, migration from schemas 1 and 2, metadata concurrency, dataset export, shot-category lifecycle, membership isolation, remote authentication/uploads, and desktop/mobile browser workflows. Existing trained models are not retrained by this update; their predictive accuracy still needs validation on your real collection.
