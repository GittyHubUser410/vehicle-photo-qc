import { test, expect, type Page } from "@playwright/test";
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
  await expect(dialog.locator(".photo-navigation")).toContainText(
    "Ford_Explorer",
  );
  await dialog.getByLabel("Add to Training Library", { exact: true }).check();
  await chooseShot(page, "Training shot type", "Rear");
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
  ).toContainText("Front passenger ¾");
  await expect(
    upload.getByLabel("Shot type for pending photo 2", { exact: true }),
  ).toContainText("Front");
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
    detail.getByRole("button", { name: "Training shot type", exact: true }),
  ).toContainText("Front passenger ¾");
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
    detail.getByRole("button", { name: "Training shot type", exact: true }),
  ).toContainText("Front");
  await chooseShot(page, "Training shot type", "Engine");
  await detail
    .getByRole("button", { name: "Save labels", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Training labels saved.",
  );
  await chooseShot(page, "Shot type (human label)", "Rear");
  await expect(
    detail.getByRole("button", { name: "Training shot type", exact: true }),
  ).toContainText("Rear");
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
  await page.getByLabel("Select photos", { exact: true }).setInputFiles({
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

async function chooseShot(page: Page, title: string, value: string) {
  await page.getByRole("button", { name: title, exact: true }).click();
  const picker = page.getByRole("dialog", {
    name: `Choose ${title.toLowerCase()}`,
    exact: true,
  });
  await picker.getByRole("textbox", { name: "Search shot types" }).fill(value);
  await picker.getByRole("button", { name: value, exact: true }).click();
  await expect(picker).not.toBeVisible();
}

test("portrait viewer, scores, training membership, vehicle editing and full-shoot link", async ({
  page,
  request,
}) => {
  const config = await (await request.get("/api/config")).json();
  const created = await request.post("/api/shoots", {
    multipart: {
      metadata: JSON.stringify({
        mode: "general",
        stock_number: "MOBILE-REVIEW",
        year: 2023,
        make: "Ford",
        model: "Escape",
        shoot_date: "2026-10-04",
        shot_types: ["front", "rear"],
      }),
      files: { name: "camera-hash.png", mimeType: "image/png", buffer: png() },
    },
  });
  // Import a two-photo batch using browser FormData (the request helper accepts one field per name).
  await page.goto("/");
  const sid = await page.evaluate(async (encoded) => {
    const bytes = Uint8Array.from(atob(encoded), (c) => c.charCodeAt(0));
    const data = new FormData();
    data.set(
      "metadata",
      JSON.stringify({
        mode: "general",
        stock_number: "MOBILE-REVIEW",
        year: 2023,
        make: "Ford",
        model: "Escape",
        shoot_date: "2026-10-04",
        shot_types: ["front", "rear"],
      }),
    );
    data.append(
      "files",
      new File([bytes], "camera-hash-1.png", { type: "image/png" }),
    );
    data.append(
      "files",
      new File([bytes], "camera-hash-2.png", { type: "image/png" }),
    );
    const response = await fetch("/api/shoots", { method: "POST", body: data });
    return (await response.json()).id;
  }, png().toString("base64"));
  expect(created.status()).toBe(422); // malformed count is still rejected atomically
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/shoots/${sid}`)).json()).status,
    )
    .toBe("complete");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Photo Library", exact: true })
    .click();
  const card = page
    .locator(".library-card")
    .filter({ hasText: "MOBILE-REVIEW" });
  await expect(card).toBeVisible();
  expect(
    await card.locator("img").evaluate((el) => getComputedStyle(el).objectFit),
  ).toBe("contain");
  await expect(card.locator(".library-overlay")).toContainText("Technical");
  await card.hover();
  await expect(card.locator(".library-hover")).toBeVisible();
  await card.click();
  let dialog = page.getByRole("dialog").first();
  await expect(dialog.locator(".film-score")).toHaveCount(2);
  await expect(dialog.locator(".needs-review")).toHaveCount(2);
  for (const viewport of [
    { width: 360, height: 800 },
    { width: 412, height: 915 },
    { width: 915, height: 412 },
  ]) {
    await page.setViewportSize(viewport);
    const dimensions = await dialog.evaluate((el) => {
      const body = el.querySelector(".modal-body")!,
        image = el.querySelector(".photo-stage img")!;
      return {
        width: el.getBoundingClientRect().width,
        scroll: body.scrollWidth,
        client: body.clientWidth,
        image: image.getBoundingClientRect().width,
        height: image.getBoundingClientRect().height,
      };
    });
    expect(dimensions.width).toBeLessThanOrEqual(viewport.width);
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client + 1);
    expect(dimensions.image).toBeLessThanOrEqual(dimensions.client);
    expect(dimensions.height).toBeLessThanOrEqual(viewport.height * 0.66);
  }
  await page.setViewportSize({ width: 412, height: 915 });
  await dialog
    .getByRole("button", { name: "Next photo on image", exact: true })
    .click();
  await expect(
    dialog.getByRole("heading", { name: "Photo 2", exact: true }),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Previous photo on image", exact: true })
    .click();
  await dialog
    .getByLabel("Use all photos for training", { exact: true })
    .check();
  await expect(
    dialog.getByLabel("Add to Training Library", { exact: true }),
  ).toBeChecked();
  await dialog.getByLabel("Add to Training Library", { exact: true }).uncheck();
  await expect(
    dialog.getByLabel("Use all photos for training", { exact: true }),
  ).toHaveJSProperty("indeterminate", true);
  await dialog
    .getByRole("button", { name: "Next photo on image", exact: true })
    .click();
  await expect(
    dialog.getByLabel("Add to Training Library", { exact: true }),
  ).toBeChecked();
  await chooseShot(page, "Shot type (human label)", "Rear seats");
  await expect(
    dialog.getByRole("button", {
      name: "Shot type (human label)",
      exact: true,
    }),
  ).toContainText("Rear seats");
  await expect(
    page.getByRole("textbox", { name: "Search shot types" }),
  ).toHaveCount(0);
  await dialog
    .getByRole("button", { name: "Edit vehicle", exact: true })
    .click();
  const editor = page.getByRole("dialog", {
    name: "Edit vehicle",
    exact: true,
  });
  await editor.getByLabel("Year", { exact: true }).fill("2024");
  await editor
    .getByLabel("Stock number", { exact: true })
    .fill("MOBILE-EDITED");
  await editor
    .getByRole("button", { name: "Save vehicle", exact: true })
    .click();
  await expect(editor).not.toBeVisible();
  await expect(dialog.locator(".photo-navigation")).toContainText(
    "2024_Ford_Escape",
  );
  await dialog
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Open navigation", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Training Library", exact: true })
    .click();
  await page
    .locator(".vehicle-card:visible")
    .filter({ hasText: "MOBILE-EDITED" })
    .click();
  dialog = page.getByRole("dialog").first();
  await expect(dialog.locator(".photo-filmstrip button")).toHaveCount(1);
  await page.screenshot({
    path: "test-results/portrait-library-detail.png",
    fullPage: true,
  });
  await dialog
    .getByRole("button", {
      name: "View full vehicle in Photo Library →",
      exact: true,
    })
    .click();
  dialog = page.getByRole("dialog").first();
  await expect(dialog.locator(".photo-filmstrip button")).toHaveCount(2);
  // Resolve one photo and verify problem-only browsing omits it.
  const detail = await (await request.get(`/api/shoots/${sid}`)).json();
  const review = detail.reviews.find(
    (r: { photo_id: string }) => r.photo_id === detail.photos[0].id,
  );
  await request.patch(`/api/reviews/${review.id}`, {
    data: { action: "resolve", resolution: "accepted" },
  });
  await dialog
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page
    .locator(".library-card")
    .filter({ hasText: "MOBILE-EDITED" })
    .click();
  await dialog.getByLabel(/Show only photos needing review/).check();
  await expect(dialog.locator(".photo-filmstrip button")).toHaveCount(1);
  await expect(
    dialog.getByRole("heading", { name: "Photo 2", exact: true }),
  ).toBeVisible();
  expect(config.shot_types.length).toBeGreaterThan(40);
});

test("shot catalog rename reorder delete restore and library menu editing", async ({
  page,
  request,
}) => {
  const imported = await request.post("/api/shoots", {
    multipart: {
      metadata: JSON.stringify({
        mode: "general",
        stock_number: "MENU-TEST",
        shoot_date: "2026-10-04",
      }),
      files: { name: "menu.png", mimeType: "image/png", buffer: png() },
    },
  });
  const importedId = (await imported.json()).id;
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/shoots/${importedId}`)).json()).status,
    )
    .toBe("complete");
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Dealership Setup", exact: true })
    .click();
  await page
    .getByLabel("New shot type", { exact: true })
    .fill("Prototype detail");
  await page
    .getByRole("button", { name: "Add shot type", exact: true })
    .click();
  await page.getByText(/Manage categories/).click();
  const row = page
    .locator(".shot-manager-row")
    .filter({ hasText: "Prototype detail" });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "Rename", exact: true }).click();
  await page
    .getByLabel("Shot type name", { exact: true })
    .fill("Prototype badge");
  await page.getByRole("button", { name: "Save name", exact: true }).click();
  const renamed = page
    .locator(".shot-manager-row")
    .filter({ hasText: "Prototype badge" });
  await renamed
    .getByRole("button", { name: "Move Prototype badge up", exact: true })
    .click();
  await expect
    .poll(async () =>
      (await (await request.get("/api/config")).json()).shot_types.at(-2),
    )
    .toBe("prototype_detail");
  await renamed.getByRole("button", { name: "Delete", exact: true }).click();
  await page
    .getByRole("button", { name: "Delete category", exact: true })
    .click();
  await expect
    .poll(async () =>
      (await (await request.get("/api/config")).json()).shot_types.includes(
        "prototype_detail",
      ),
    )
    .toBe(false);
  await page.getByText("Deleted categories", { exact: true }).click();
  await page
    .locator(".shot-manager-row")
    .filter({ hasText: "Prototype badge" })
    .getByRole("button", { name: "Restore", exact: true })
    .click();
  await expect
    .poll(async () =>
      (await (await request.get("/api/config")).json()).shot_types.includes(
        "prototype_detail",
      ),
    )
    .toBe(true);
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Photo Library", exact: true })
    .click();
  const options = page
    .locator(".library-card-wrap")
    .filter({ hasText: "MENU-TEST" });
  await options.locator("summary").click();
  await options
    .getByRole("button", { name: "Edit vehicle", exact: true })
    .click();
  const editor = page.getByRole("dialog", {
    name: "Edit vehicle",
    exact: true,
  });
  await editor.getByLabel("Color", { exact: true }).fill("Silver");
  await editor
    .getByRole("button", { name: "Save vehicle", exact: true })
    .click();
  await expect(editor).not.toBeVisible();
  await page.screenshot({
    path: "test-results/desktop-library.png",
    fullPage: true,
  });
});

test("evidence: defaults, explicit verification, stale coverage and export", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/shoots", {
    multipart: {
      metadata: JSON.stringify({
        mode: "general",
        purpose: "evaluation",
        shoot_date: "2026-10-08",
        stock_number: "EVIDENCE-101",
        shot_types: ["front"],
      }),
      files: { name: "front.png", mimeType: "image/png", buffer: png() },
    },
  });
  expect(created.status()).toBe(201);
  const sid = (await created.json()).id;
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/shoots/${sid}`)).json()).status,
    )
    .toBe("complete");
  const first = await (await request.get(`/api/shoots/${sid}`)).json();
  const pid = first.photos[0].id;
  await request.post(`/api/photos/${pid}/training`);
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Training Library", exact: true })
    .click();
  await page
    .getByRole("button", { name: /EVIDENCE-101/ })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText(/Not exportable: Unverified Label/i),
  ).toBeVisible();
  await expect(
    dialog.getByLabel("Approved for training", { exact: true }),
  ).toBeChecked();
  await expect(dialog.locator(".issue.resolved")).toHaveCount(0);
  await dialog
    .getByRole("button", { name: "Save labels", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Training labels saved");
  expect(
    (await (await request.get(`/api/shoots/${sid}`)).json()).photos[0].training
      .exportable,
  ).toBe(false);
  const fields = dialog.getByRole("group", {
    name: "Fields reviewed for verification",
  });
  for (const name of [
    "Angle",
    "Blur",
    "Crop",
    "Exposure",
    "Saturation",
    "Framing",
    "Overall",
  ]) {
    await fields.getByLabel(new RegExp(`^${name}`)).uncheck();
  }
  await dialog
    .getByRole("button", { name: "Verify selected labels", exact: true })
    .click();
  await expect(
    dialog.getByText("Exportable verified shot label.", { exact: false }),
  ).toBeVisible();
  const verified = await (await request.get(`/api/shoots/${sid}`)).json();
  expect(verified.photos[0].training.label_evidence.shot_type.state).toBe(
    "verified",
  );
  expect(verified.photos[0].training.label_evidence.blur.state).toBe(
    "suggested",
  );
  await dialog
    .getByRole("button", { name: "Confirm operational shot", exact: true })
    .click();
  await dialog
    .getByText("Analysis coverage & history", { exact: true })
    .click();
  await expect(
    dialog.getByText(/Shot evidence changed; reanalyze/),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Reanalyze shoot", exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/shoots/${sid}`)).json()).qc_evidence
          .freshness,
    )
    .toBe("current");
  await expect(dialog.getByText(/QC coverage Incomplete/)).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Reanalyze shoot", exact: true }),
  ).toBeEnabled();
  await dialog.locator(".history").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "test-results/verified-coverage.png",
    fullPage: true,
  });
  await dialog
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Export verified dataset", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Verified dataset snapshot saved",
  );
  const href = await page
    .getByRole("link", { name: "Download manifest", exact: true })
    .getAttribute("href");
  const manifest = await (await request.get(href!)).json();
  expect(manifest.schema_version).toBe(2);
  expect(
    manifest.entries.some((e: { photo_id: string }) => e.photo_id === pid),
  ).toBe(true);
});

test("evidence: verify next preserves position and selected confirmation semantics", async ({
  page,
  request,
}) => {
  const staged = await request.post("/api/uploads", {
    data: {
      count: 2,
      metadata: {
        mode: "general",
        purpose: "training",
        shoot_date: "2026-10-08",
        stock_number: "VERIFY-NEXT",
        shot_types: ["front", "rear"],
      },
    },
  });
  const url = `/api/uploads/${(await staged.json()).id}`;
  for (const i of [0, 1]) {
    expect(
      (
        await request.put(`${url}/photos/${i}`, {
          multipart: {
            file: { name: `${i}.png`, mimeType: "image/png", buffer: png() },
          },
        })
      ).ok(),
    ).toBe(true);
  }
  const completed = await request.post(`${url}/complete`);
  const sid = (await completed.json()).id;
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/shoots/${sid}`)).json()).status,
    )
    .toBe("complete");
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Training Library", exact: true })
    .click();
  await page
    .getByRole("button", { name: /VERIFY-NEXT/ })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByRole("button", { name: "Verify + next", exact: true })
    .click();
  await expect(
    dialog.getByRole("heading", { name: "Photo 2", exact: true }),
  ).toBeVisible();
  const d = await (await request.get(`/api/shoots/${sid}`)).json();
  expect(d.photos[0].training.exportable).toBe(true);
  expect(
    Object.values(d.photos[0].training.label_evidence).every(
      (e: unknown) => (e as { state: string }).state === "verified",
    ),
  ).toBe(true);
  expect(d.photos[1].training.exportable).toBe(false);
  expect(d.photos[1].training.labels.blur).toBe("good");
  await dialog
    .getByRole("button", { name: "Save labels", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Training labels saved");
  const after = await (await request.get(`/api/shoots/${sid}`)).json();
  expect(after.photos[1].training.exportable).toBe(false);
});

test("evidence: legacy and prediction display stay distinct from approval", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/shoots", {
    multipart: {
      metadata: JSON.stringify({
        mode: "general",
        purpose: "training",
        shoot_date: "2026-10-08",
        stock_number: "LEGACY-EVIDENCE",
        shot_types: ["front"],
      }),
      files: { name: "front.png", mimeType: "image/png", buffer: png() },
    },
  });
  const sid = (await created.json()).id;
  await expect
    .poll(
      async () =>
        (await (await request.get(`/api/shoots/${sid}`)).json()).status,
    )
    .toBe("complete");
  const fixture = await (await request.get(`/api/shoots/${sid}`)).json();
  // Read-only UI fixture represents preserved pre-A.1 records and model provenance.
  fixture.photos[0].shot_evidence.state = "legacy_unverified";
  for (const ev of Object.values(fixture.photos[0].training.label_evidence)) {
    (ev as { state: string }).state = "legacy_unverified";
  }
  fixture.photos[0].analysis.predicted_shot = "rear";
  fixture.photos[0].analysis.confidence = 0.9;
  fixture.photos[0].analysis.context.evidence.prediction = {
    state: "predicted",
    model_id: "fixture-model",
  };
  fixture.qc_evidence = {
    ...fixture.qc_evidence,
    evidence_schema_version: 0,
    coverage: "unknown",
    freshness: "historical_unknown",
    checks: [],
  };
  await page.route(`**/api/shoots/${sid}`, (route) =>
    route.fulfill({ json: fixture }),
  );
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name: "Training Library", exact: true })
    .click();
  await page
    .getByRole("button", { name: /LEGACY-EVIDENCE/ })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText("Legacy Unverified", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    dialog.getByText(/Model suggestion: Rear.*90%.*fixture-model/),
  ).toBeVisible();
  await dialog
    .getByText(/Model suggestion: Rear.*90%.*fixture-model/)
    .scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "test-results/prediction-provenance.png",
    fullPage: true,
  });
  await dialog
    .getByText("Analysis coverage & history", { exact: true })
    .click();
  await expect(
    dialog.getByText(/Historical evidence is unknown/),
  ).toBeVisible();
  await expect(
    dialog.getByLabel("Approved for training", { exact: true }),
  ).toBeChecked();
  await page.screenshot({
    path: "test-results/legacy-prediction.png",
    fullPage: true,
  });
});
