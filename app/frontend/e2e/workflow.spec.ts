import { test, expect } from "@playwright/test";
import { deflateSync } from "node:zlib";

function crc32(buf: Buffer) {
  let c = 0xffffffff;
  for (const b of buf) {
    c ^= b;
    for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (c & 1 ? 0xedb88320 : 0);
  }
  return (c ^ 0xffffffff) >>> 0;
}
function png() {
  const chunk = (name: string, body: Buffer) => {
    const length = Buffer.alloc(4);
    length.writeUInt32BE(body.length);
    const data = Buffer.concat([Buffer.from(name), body]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(data));
    return Buffer.concat([length, data, crc]);
  };
  const header = Buffer.alloc(13);
  header.writeUInt32BE(320);
  header.writeUInt32BE(200, 4);
  header[8] = 8;
  header[9] = 2;
  const rows = Buffer.alloc(200 * (320 * 3 + 1), 128);
  for (let y = 0; y < 200; y++) rows[y * (320 * 3 + 1)] = 0;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(rows)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

test("import, reorder, inspect, resolve, and approve training labels", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Evaluate Vehicle", exact: true })
    .click();
  await page.getByRole("button", { name: "General QC", exact: true }).click();
  await page.getByLabel("Stock number", { exact: true }).fill("E2E-100");
  await page.getByLabel("Make", { exact: true }).fill("Ford");
  await page.getByLabel("Model", { exact: true }).fill("Explorer");
  await page.getByLabel("Select photos", { exact: true }).setInputFiles([
    { name: "front.png", mimeType: "image/png", buffer: png() },
    { name: "rear.png", mimeType: "image/png", buffer: png() },
  ]);
  await page
    .getByRole("button", { name: "Move photo 2 earlier", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Evaluate 2 photos", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Reanalyze shoot", exact: true }),
  ).toBeEnabled({ timeout: 20000 });
  await expect(dialog.locator(".photo-navigation")).toContainText("rear.png");
  await dialog
    .getByRole("button", { name: "Add to Training Library", exact: true })
    .click();
  await dialog
    .getByRole("combobox", { name: "Training shot type", exact: true })
    .selectOption("rear");
  await dialog.getByLabel("Approved for training", { exact: true }).check();
  await dialog
    .getByRole("button", { name: "Save labels", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Training labels saved.",
  );
  await dialog
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: /Review Queue/ })
    .click();
  const card = page
    .locator(".review-card")
    .filter({ hasText: "E2E-100" })
    .first();
  await expect(card).toHaveClass(/unviewed/);
  await card.click();
  await expect(dialog).toBeVisible();
  await expect(card).not.toHaveClass(/unviewed/);
  await dialog
    .getByLabel("Reviewer note", { exact: true })
    .fill("Test review: checked the original.");
  await dialog
    .getByRole("button", { name: "Resolve / remove from queue", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Review resolved");
  await dialog
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Vehicle Results", exact: true })
    .click();
  await page.getByRole("button", { name: /Filters/ }).click();
  await page
    .getByRole("combobox", { name: "Previously in review queue", exact: true })
    .selectOption("yes");
  await expect(
    page
      .locator(".vehicle-list:visible .vehicle-card")
      .filter({ hasText: "E2E-100" }),
  ).toHaveCount(1);
  await page.screenshot({
    path: "test-results/desktop-results.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("phone navigation and dealership override save", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("navigation", { name: "Mobile navigation" }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Mobile navigation" })
    .getByRole("button", { name: "More", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Dealership Setup", exact: true })
    .click();
  await page.locator(".dealer-card").first().click();
  const dialog = page.getByRole("dialog");
  const row = dialog
    .locator(".rule-row")
    .filter({ hasText: "Minimum photo count" });
  await row.getByRole("button", { name: "Override", exact: true }).click();
  await dialog.getByLabel("Minimum photo count", { exact: true }).fill("12");
  await dialog
    .getByRole("button", { name: "Save dealership", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  await page.locator(".dealer-card").first().click();
  await expect(
    dialog.getByLabel("Minimum photo count", { exact: true }),
  ).toHaveValue("12");
  await page.screenshot({
    path: "test-results/phone-standards.png",
    fullPage: true,
  });
  const horizontal = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(horizontal).toBe(false);
  await dialog
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Mobile navigation" })
    .getByRole("button", { name: "Evaluate", exact: true })
    .click();
  await expect(page.getByLabel("Stock number", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "test-results/phone-upload.png",
    fullPage: true,
  });
});

test("training defaults, pending removal, bulk paste, shot sync, and trash restore", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  await nav
    .getByRole("button", { name: "Training Library", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Upload training data", exact: true })
    .click();
  const upload = page.getByRole("dialog");
  await upload
    .getByRole("button", { name: "Stage Now / outside photos", exact: true })
    .click();
  await upload
    .getByLabel("Stock number", { exact: true })
    .fill("REVISION-TRAINING");
  await upload.getByLabel("Select photos", { exact: true }).setInputFiles(
    Array.from({ length: 5 }, (_, i) => ({
      name: `training-${i}.png`,
      mimeType: "image/png",
      buffer: png(),
    })),
  );
  await upload
    .getByRole("button", { name: "Remove photo 5", exact: true })
    .click();
  await upload.getByLabel("Select pending photo 4", { exact: true }).check();
  await upload.getByRole("button", { name: /Remove selected/ }).click();
  await expect(
    upload.getByLabel("Shot type for pending photo 1", { exact: true }),
  ).toHaveValue("front_passenger_34");
  await expect(
    upload.getByLabel("Shot type for pending photo 2", { exact: true }),
  ).toHaveValue("front");
  await upload
    .getByRole("button", { name: "Import 3 training photos" })
    .click();
  const detail = page.getByRole("dialog").first();
  await expect(
    detail.getByRole("button", { name: "Reanalyze shoot", exact: true }),
  ).toBeEnabled({ timeout: 20000 });
  await expect(
    detail.getByRole("combobox", { name: "Exposure", exact: true }),
  ).toHaveValue("good");
  await expect(
    detail.getByRole("combobox", { name: "Training shot type", exact: true }),
  ).toHaveValue("front_passenger_34");
  await detail
    .getByRole("combobox", { name: "Exposure", exact: true })
    .selectOption("bad");
  await expect(
    detail.getByLabel("Approved for training", { exact: true }),
  ).toBeChecked();
  await detail
    .getByRole("button", { name: "Copy Settings", exact: true })
    .click();
  await detail
    .getByRole("button", { name: "Paste settings…", exact: true })
    .click();
  const paste = page.getByRole("dialog", {
    name: "Paste settings",
    exact: true,
  });
  await paste.getByRole("button", { name: "Select all", exact: true }).click();
  await paste
    .getByRole("button", { name: "Paste to 3 photos", exact: true })
    .click();
  await expect(paste).not.toBeVisible();
  await detail
    .getByRole("button", { name: "View photo 2", exact: true })
    .click();
  await expect(
    detail.getByRole("combobox", { name: "Exposure", exact: true }),
  ).toHaveValue("bad");
  await expect(
    detail.getByRole("combobox", { name: "Training shot type", exact: true }),
  ).toHaveValue("front");
  await detail
    .getByRole("combobox", { name: "Training shot type", exact: true })
    .selectOption("engine");
  await detail
    .getByRole("button", { name: "Save labels", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Training labels saved.",
  );
  await detail
    .getByRole("combobox", { name: "Shot type (human label)", exact: true })
    .selectOption("rear");
  await expect(
    detail.getByRole("combobox", { name: "Training shot type", exact: true }),
  ).toHaveValue("rear");
  await page.screenshot({
    path: "test-results/training-revisions.png",
    fullPage: true,
  });
  await detail
    .getByRole("button", { name: "Delete photo…", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Delete photo?", exact: true })
    .getByRole("button", { name: "Move to Trash", exact: true })
    .click();
  await expect(
    detail.getByRole("button", { name: "View photo 2", exact: true }),
  ).toHaveCount(0);
  await detail
    .getByRole("button", { name: "Delete vehicle…", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Delete vehicle?", exact: true })
    .getByRole("button", { name: "Move to Trash", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await nav.getByRole("button", { name: "Trash", exact: true }).click();
  const row = page
    .locator(".setting-row")
    .filter({ hasText: "REVISION-TRAINING" })
    .first();
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Restore", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Restored");
  await nav
    .getByRole("button", { name: "Training Library", exact: true })
    .click();
  await expect(
    page
      .locator(".vehicle-card:visible")
      .filter({ hasText: "REVISION-TRAINING" }),
  ).toHaveCount(1);
  expect(errors).toEqual([]);
});

test("Android-sized capture and interrupted staged uploads keep one vehicle", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 412, height: 915 });
  let failedPhoto = false,
    failedReceipt = false,
    batches = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && new URL(r.url()).pathname === "/api/uploads")
      batches++;
  });
  await page.route(/\/api\/uploads\/[^/]+\/photos\/1$/, async (route) => {
    if (!failedPhoto) {
      failedPhoto = true;
      await route.abort();
    } else await route.continue();
  });
  await page.route(/\/api\/uploads\/[^/]+\/complete$/, async (route) => {
    if (!failedReceipt) {
      failedReceipt = true;
      await route.fetch();
      await route.abort();
    } else await route.continue();
  });
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Mobile navigation" })
    .getByRole("button", { name: "Evaluate", exact: true })
    .click();
  await page.getByRole("button", { name: "General QC", exact: true }).click();
  await page.getByLabel("Stock number", { exact: true }).fill("ANDROID-RETRY");
  const camera = page.getByLabel("Take a vehicle photo", { exact: true });
  await expect(camera).toHaveAttribute("capture", "environment");
  await camera.setInputFiles({
    name: "camera.png",
    mimeType: "image/png",
    buffer: png(),
  });
  await page
    .getByLabel("Select photos", { exact: true })
    .setInputFiles({
      name: "gallery.png",
      mimeType: "image/png",
      buffer: png(),
    });
  const submit = page.getByRole("button", {
    name: "Evaluate 2 photos",
    exact: true,
  });
  await submit.click();
  await expect(page.getByRole("alert")).toContainText("Connection interrupted");
  await submit.click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(submit).toBeEnabled();
  await submit.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Reanalyze shoot", exact: true }),
  ).toBeEnabled({ timeout: 20000 });
  const vehicles = await (
    await request.get("/api/shoots?q=ANDROID-RETRY")
  ).json();
  expect(vehicles.total).toBe(1);
  expect(vehicles.items[0].photo_count).toBe(2);
  expect(batches).toBe(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  ).toBe(false);
  await page.screenshot({
    path: "test-results/android-capture-retry.png",
    fullPage: true,
  });
});
