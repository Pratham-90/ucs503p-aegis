/**
 * The 5-minute demo script (brief section 1) as one end-to-end test through the
 * real UI. Every step is screenshotted into report-assets/screenshots/.
 * Requirements exercised: FR-1..FR-8, NFR-SEC-1/2/5, NFR-REL-1, NFR-USE-1.
 */
import { expect, test, type Browser, type BrowserContext, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

const ADMIN = "e2e-admin-token";
const SHOTS = path.resolve(here, "../../report-assets/screenshots");
const RESULTS = path.resolve(here, "../test-results");
const MARKER = "AEGIS-E2E-MARKER-7f3a9c: the deed is in the blue box";
const FILE_MARKER = "AEGIS-E2E-FILE-MARKER-41d2";
const OWNER = { email: "owner.e2e@example.com", password: "correct horse battery" };
const TRUSTEES = ["alice.e2e@example.com", "bob.e2e@example.com", "carol.e2e@example.com"];

const shot = (page: Page, name: string) => page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });

async function demoApi(page: Page, method: "get" | "post", url: string, data?: unknown) {
  const res = await page.request[method](url, { headers: { "X-Demo-Token": ADMIN }, data });
  expect(res.ok(), `${method} ${url}`).toBeTruthy();
  return res.json();
}

async function outbox(page: Page): Promise<{ to: string; kind: string; body: string }[]> {
  return (await demoApi(page, "get", "/api/demo/outbox")).emails;
}

const linkPath = (body: string, marker: string) => {
  const url = body.split(/\s+/).find((w) => w.includes(marker))!;
  return url.replace(/^https?:\/\/[^/]+/, "");
};

async function newContext(browser: Browser): Promise<BrowserContext> {
  return browser.newContext({ acceptDownloads: true, viewport: { width: 1280, height: 860 } });
}

test("demo script: enrol, seal, check in, release, recover 2 of 3", async ({ browser }) => {
  mkdirSync(SHOTS, { recursive: true });
  mkdirSync(RESULTS, { recursive: true });

  // 1. Owner registers (FR-1)
  const ownerCtx = await newContext(browser);
  const owner = await ownerCtx.newPage();
  await owner.goto("/");
  await expect(owner.getByRole("heading", { level: 1 })).toBeVisible();
  await shot(owner, "01-landing");
  await owner.goto("/register");
  await owner.getByLabel("Email").fill(OWNER.email);
  await owner.getByLabel("Password").fill(OWNER.password);
  await shot(owner, "02-register");
  await owner.getByRole("button", { name: "Create account" }).click();
  await owner.getByRole("link", { name: "Create my vault" }).click();

  // 2-3. Trustees, K = 2 of N = 3, demo schedule, with live FR-4 validation
  for (const [i, email] of TRUSTEES.entries()) await owner.getByLabel(`Trustee ${i + 1} email`).fill(email);
  await owner.getByLabel("Threshold K").fill("1");
  await expect(owner.getByText("K must be at least 2")).toBeVisible();
  await owner.getByLabel("Threshold K").fill("3");
  await expect(owner.getByText("K = N: if any single trustee")).toBeVisible();
  await shot(owner, "03-threshold-validation");
  await owner.getByLabel("Threshold K").fill("2");
  await expect(owner.getByTestId("loss-tolerance")).toContainText("1 trustee can be lost");
  await shot(owner, "04-wizard-configure");
  await owner.getByRole("button", { name: "Create vault & invite trustees" }).click();
  await expect(owner.getByTestId("invite-link")).toHaveCount(3);
  await shot(owner, "05-invite-links");
  const inviteLinks = await owner.getByTestId("invite-link").allTextContents();

  // Each trustee enrols in their own browser: keypair generated client-side, key file downloaded (FR-4)
  const trustees: { ctx: BrowserContext; page: Page; keyFile: string }[] = [];
  for (const [i, link] of inviteLinks.entries()) {
    const ctx = await newContext(browser);
    const page = await ctx.newPage();
    await page.goto(link.replace(/^https?:\/\/[^/]+/, ""));
    await expect(page.getByTestId("enrol-button")).toBeVisible();
    if (i === 0) await shot(page, "06-trustee-enrol");
    const download = page.waitForEvent("download");
    await page.getByTestId("enrol-button").click();
    const keyFile = path.join(RESULTS, `trustee-${i + 1}.json`);
    await (await download).saveAs(keyFile);
    await expect(page.getByText("Enrolled.")).toBeVisible();
    if (i === 0) await shot(page, "07-trustee-enrolled");
    expect(JSON.parse(readFileSync(keyFile, "utf8")).private_jwk.d).toBeTruthy();
    trustees.push({ ctx, page, keyFile });
  }

  // 3-4. Secret typed only after enrolment; browser encrypts, splits, wraps; server receives ciphertext only
  await expect(owner.getByRole("button", { name: "Next: write your secret" })).toBeEnabled({ timeout: 15_000 });
  await owner.getByRole("button", { name: "Next: write your secret" }).click();
  await owner.getByLabel("Secret message").fill(MARKER);
  await owner.getByLabel("Attach a file").setInputFiles({ name: "instructions.txt", mimeType: "text/plain", buffer: Buffer.from(FILE_MARKER) });
  await owner.getByRole("button", { name: "Review" }).click();
  await shot(owner, "08-review");
  await owner.getByTestId("seal-button").click();
  await expect(owner.getByText("What the server received")).toBeVisible();
  const page_text = await owner.locator("main").innerText();
  expect(page_text).not.toContain(MARKER); // the request body shown contains ciphertext only
  await shot(owner, "09-server-received");

  // 5. Dashboard: Active with countdown; one-click check-in (FR-6, NFR-USE-1)
  await owner.getByRole("link", { name: "Go to dashboard" }).click();
  await expect(owner.getByTestId("state-badge").first()).toHaveText(/Active/);
  await shot(owner, "10-dashboard-active");
  await owner.getByTestId("checkin-button").click();
  await expect(owner.getByText("Checked in. The timer has been reset.")).toBeVisible();
  await shot(owner, "11-checked-in");

  // 6. Owner goes silent. Fast-forward the demo clock past the deadline: Active -> Warning, prompt email (FR-5)
  await demoApi(owner, "post", "/api/demo/clock/advance", { seconds: 125 });
  const demo = await ownerCtx.newPage();
  await demo.goto("/demo");
  await demo.getByLabel("Demo admin token").fill(ADMIN);
  await demo.getByRole("button", { name: "Open console" }).click();
  await demo.getByTestId("run-tick").click();
  await expect(demo.getByText(/Tick done: 1 transition/)).toBeVisible();
  await expect(demo.getByTestId("outbox")).toContainText("Aegis: please check in");
  await shot(demo, "12-demo-console-warning");

  // The emailed one-click link works exactly once
  const prompt = (await outbox(owner)).find((e) => e.kind === "checkin_prompt")!;
  const checkinPath = linkPath(prompt.body, "/checkin/");
  await owner.goto(checkinPath);
  await expect(owner.getByText("You're checked in.")).toBeVisible();
  await shot(owner, "13-checkin-link");

  // Silence again: past deadline + grace -> Grace -> Released (FR-7, NFR-REL-1)
  await demoApi(owner, "post", "/api/demo/clock/advance", { seconds: 150 });
  await demo.getByTestId("run-tick").click();
  await expect(demo.getByText(/Tick done/)).toBeVisible();
  await owner.goto("/dashboard");
  await expect(owner.getByTestId("state-badge").first()).toHaveText(/Grace/);
  await shot(owner, "14-dashboard-grace");
  await demoApi(owner, "post", "/api/demo/clock/advance", { seconds: 35 });
  await demo.getByTestId("run-tick").click();
  await expect(demo.getByTestId("outbox")).toContainText("has been released");
  await shot(demo, "15-demo-console-released");
  await owner.goto("/dashboard");
  await expect(owner.getByTestId("state-badge").first()).toHaveText(/Released/);
  await shot(owner, "16-dashboard-released");

  // 7. Two trustees decrypt their own shares in their browsers (FR-7, FR-8)
  const emails = await outbox(owner);
  const releaseLink = (email: string) => linkPath(emails.find((e) => e.kind === "release" && e.to === email)!.body, "/trustee?t=");
  const shares: string[] = [];
  for (const i of [0, 2]) {
    // Trustee 3 uses a fresh browser (no IndexedDB copy) and loads the downloaded key file instead.
    const ctx = i === 0 ? trustees[0].ctx : await newContext(browser);
    const page = await ctx.newPage();
    await page.goto(releaseLink(TRUSTEES[i]));
    await expect(page.getByText("This vault was released")).toBeVisible();
    if (i === 2) await page.getByLabel("Private key file").setInputFiles(trustees[2].keyFile);
    await page.getByTestId("decrypt-share").click();
    const share = (await page.locator("pre").first().innerText()).trim();
    expect(share).toMatch(/^aegis-share:v1:\d+:/);
    shares.push(share);
    await shot(page, i === 0 ? "17-trustee-portal-share" : "18-trustee-key-file-share");
  }

  // 8. Recovery Room: one share fails, two succeed (FR-8, NFR-SEC-2)
  const room = await trustees[0].ctx.newPage();
  await room.goto(`/recover?t=${releaseLink(TRUSTEES[0]).split("t=")[1]}`);
  await room.getByLabel("Share 1").fill(shares[0]);
  await room.getByTestId("recover-button").click();
  await expect(room.getByRole("alert")).toContainText("Not enough shares");
  await shot(room, "19-recovery-one-share-fails");
  await room.getByLabel("Share 2").fill(shares[1]);
  await room.getByTestId("recover-button").click();
  await expect(room.getByTestId("recovered-message")).toHaveText(MARKER);
  const fileDownload = room.waitForEvent("download");
  await room.getByRole("button", { name: "Download instructions.txt" }).click();
  const recoveredFile = path.join(RESULTS, "recovered-instructions.txt");
  await (await fileDownload).saveAs(recoveredFile);
  expect(readFileSync(recoveredFile, "utf8")).toBe(FILE_MARKER);
  await shot(room, "20-recovery-success");

  // 9. Demo Console evidence + a phone-sized dashboard
  await demo.reload();
  await shot(demo, "21-demo-console-evidence");
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const phonePage = await phone.newPage();
  await phonePage.goto("/login");
  await phonePage.getByLabel("Email").fill(OWNER.email);
  await phonePage.getByLabel("Password").fill(OWNER.password);
  await phonePage.getByRole("button", { name: "Log in" }).click();
  await expect(phonePage.getByTestId("state-badge").first()).toBeVisible();
  await shot(phonePage, "22-dashboard-mobile");

  // Hand the known secrets to scripts/inspect_server_store.py (it scans e2e.db for them).
  writeFileSync(
    path.join(RESULTS, "e2e-known-secrets.json"),
    JSON.stringify({ marker: MARKER, file_marker: FILE_MARKER, shares }, null, 2),
  );
});
