# Photo-entry improvements: upgrading the existing app

Update the existing project, run its normal setup/build command, and restart it with the **same data directory / QC_DATA_DIR**. Do not replace the data folder. This is an incremental update of the existing app; it does not require a new library or model retraining. Existing model class identifiers remain unchanged.

## Database and files

Startup migrates SQLite schema 1 to 2 automatically. Before altering schema 1 it makes a SQLite-consistent backup at `data/migration-backups/before-v2.db` (under your configured data directory). The migration adds nullable trash timestamps to vehicles, photos, and training memberships, plus analysis context and two tables: `shot_types` and `dealer_sequences`. Existing rows, labels, IDs, rule snapshots, analyses, original photos, thumbnails, dataset manifests, and model files remain intact. Repeated startup is safe. Unknown schema versions are rejected rather than reset.

The database-only migration backup is not a replacement for your normal full backup. Stop the app before updating; the existing backup script includes photos and models. Use the updated app with schema 2; the old app is not designed to open it.

## Faster entry

- New training examples start with all quality fields **Good**, using the normal shot type. Existing labels are untouched. New uploads now start approved; the checkbox can be cleared. Existing approvals remain unchanged.
- **Copy Settings** copies current quality labels and the note, including unsaved edits. **Paste settings…** lets you choose one or many photos in a vehicle. The clipboard survives closing a vehicle within the same browser session, so you can paste into another vehicle. Both normal and training shot types are preserved. Pasting clears approval and uses revision checks to avoid overwriting another editor's changes.
- Pending thumbnails have individual remove buttons and selection controls for bulk removal. No stored files are deleted by these controls.
- Changing a normal shot type populates its training shot type. A later manual training-shot choice remains until the normal shot changes again. These label changes clear training approval.
- Upload shot types follow the dealership's last-used sequence, then its required sequence, then the standard eight exterior shots, then Unassigned. Sequence memory is independent for each dealership and new/used inventory. Changes to required shots/order invalidate old memory; edits to an older vehicle cannot reintroduce that obsolete sequence. Manual selections remain editable.
- The full master category list is seeded into the shared database catalog. Add future categories in **Dealership Setup → Shot types**. Legacy categories stay available so older data and trained models still work. Adding categories does not expand an existing trained model's vocabulary; train a future model explicitly when you have enough examples.

## Trash

Delete a photo or a vehicle from its detail window. Both actions ask for confirmation and retain files. Deleting in Training Library removes training membership only; deleting in the analysis/photo library removes the record from all active storage. Whole-vehicle removal covers its photos. The Trash page restores records; restore a vehicle before separately deleted photos.

Deleted items disappear from active lists, review queues, counts, and future dataset exports. Deleted or no-longer-approved examples are also excluded when the training command reads an older snapshot against this data directory. Historical manifests stay byte-for-byte unchanged, and holdout evaluation of existing model snapshots remains reproducible. Restoring does not automatically approve training examples: review and save approval again. Retained files are not reclaimed from disk by this release.

## Banners and existing analysis

Dealership/group rules now support None, First photo only, and All applicable photos, plus an optional category list (empty means all). The guide and per-photo analysis context honor that scope. As before, existing vehicles retain the rules saved when imported. Old positive-height banner rules keep their prior all-photos behavior.

**Automatic object/vehicle overlap judgment remains unavailable:** the existing app has no vehicle/object detector or geometry model. This update separates banner applicability from future geometry evidence, so detection can be added without redesigning the rule system. It does not claim that an overlap is acceptable or unacceptable without that evidence. Technical quality checks and the existing shot classifier continue unchanged.

## Checks to try with your own workflow

Upload two consecutive vehicles for one dealership; confirm the second receives the first vehicle's corrected sequence. Copy an exposure label to several different exterior angles and confirm their shot types stay distinct. Try a pending removal, a Training Library deletion and restoration, and first-photo-only banner guides. Confirm your existing photos and model selection are still present after restart.
