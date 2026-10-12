import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve("..");
const config = Object.fromEntries(
  fs
    .readFileSync(path.join(root, ".env"), "utf8")
    .split(/\r?\n/)
    .filter((l) => l.includes("="))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
);

async function login(page, role = "user") {
  await page.goto("/login");
  await page
    .getByLabel("Email address")
    .fill(role === "admin" ? "admin@example.com" : "student@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill(
      config[role === "admin" ? "DEMO_ADMIN_PASSWORD" : "DEMO_USER_PASSWORD"],
    );
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/dashboard/);
}

test("landing, authentication, conversion, schema, download, history, logout", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "File Converter System." }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Aayush Sarraf · Aditya Raj · Deepanshu Kumar · Dhruv Agarwal",
    ),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/landing.png",
    fullPage: true,
  });
  await page.goto("/converter");
  await expect(page).toHaveURL(/login/);
  await page.getByLabel("Email address").fill("student@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Wrong-password-123");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("incorrect");
  await login(page);
  await expect(
    page.getByRole("heading", { name: "Recent conversions" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/dashboard.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "File converter", exact: true }).click();
  await page
    .getByLabel("Dataset file")
    .setInputFiles(path.join(root, "samples/students.csv"));
  await page.getByRole("button", { name: "Upload & review schema" }).click();
  await expect(
    page.getByRole("heading", { name: /Review & confirm schema/ }),
  ).toBeVisible();
  await page
    .getByLabel("Attribute 1 name", { exact: true })
    .fill("student_name");
  await page
    .getByLabel("Attribute 1 type", { exact: true })
    .selectOption("string");
  await page.getByRole("button", { name: "Convert to ARFF" }).click();
  await expect(
    page.getByRole("heading", { name: /Your converted file is ready/ }),
  ).toBeVisible();
  await expect(page.locator("pre")).toContainText(
    "@attribute 'student_name' STRING",
  );
  await expect(page.getByRole("status")).toContainText(
    "Verification passed · WEKA",
  );
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download ARFF" }).click();
  expect((await download).suggestedFilename()).toBe("students.arff");
  await page.screenshot({
    path: "../docs/screenshots/converter.png",
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Conversion history", exact: true })
    .click();
  await page.getByLabel("Search file name").fill("students");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(
    page.getByText("students.csv", { exact: true }).first(),
  ).toBeVisible();
  page.once("dialog", (d) => d.accept());
  await page
    .getByRole("button", { name: "Delete students.csv", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/login/);
  expect(errors).toEqual([]);
});

test("recent sign-in names replace the login and registration promotional panel", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  const panel = page.getByRole("region", {
    name: "Recently signed in",
    exact: true,
  });
  for (const mode of ["login", "register"]) {
    await page.goto(`/${mode}`);
    await expect(panel).toBeVisible();
    await expect(
      panel.getByRole("listitem").filter({ hasText: "Mira Desai" }),
    ).toBeVisible();
    expect(await panel.getByRole("listitem").count()).toBeLessThanOrEqual(5);
    await expect(panel).not.toContainText("student@example.com");
    await expect(panel).not.toContainText("127.0.0.1");
    await expect(panel.locator("time, svg")).toHaveCount(0);
    await expect(
      page.getByText("Less formatting.", { exact: false }),
    ).toHaveCount(0);
    await expect(
      page.getByText("More possibility.", { exact: true }),
    ).toHaveCount(0);
    await expect(
      page.getByText("One workspace for preparing your CSV and ARFF datasets."),
    ).toHaveCount(0);
    await expect(
      page.getByText("Secure accounts.", { exact: false }),
    ).toHaveCount(0);
    await page.screenshot({
      path: `../docs/screenshots/${mode}-recent-users.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(panel).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../docs/screenshots/register-recent-users-mobile.png",
    fullPage: true,
  });
  await page.route("**/api/v1/auth/recent-users", (route) =>
    route.fulfill({ json: { names: [] } }),
  );
  await page.goto("/login");
  await expect(panel).toContainText("No recent sign-ins yet");
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeEnabled();
  await page.unroute("**/api/v1/auth/recent-users");
  await page.route("**/api/v1/auth/recent-users", (route) =>
    route.fulfill({ status: 503, json: { detail: "Unavailable" } }),
  );
  await page.goto("/register");
  await expect(panel).toContainText("temporarily unavailable");
  await expect(
    page.getByRole("button", { name: "Create account", exact: true }),
  ).toBeEnabled();
  await page.unroute("**/api/v1/auth/recent-users");
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await expect(panel).toContainText("Mira Desai");
  await page.route("**/api/v1/auth/recent-users", (route) =>
    route.fulfill({
      json: { names: ["<img src=x onerror=alert(1)>", "A".repeat(100)] },
    }),
  );
  await page.goto("/login");
  await expect(panel.getByRole("listitem").first()).toHaveText(
    "<img src=x onerror=alert(1)>",
  );
  await expect(panel.locator("img")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("last login list, previous logins, reload and mobile layout", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/last-login");
  await expect(page).toHaveURL(/login/);
  await login(page);
  await page.getByRole("link", { name: "Last login", exact: true }).click();
  await expect(page).toHaveURL(/last-login/);
  const table = page.getByRole("table", {
    name: "Successful sign-ins",
    exact: true,
  });
  const times = table.locator("tbody time");
  await expect(times.first()).toBeVisible();
  await expect(table).toContainText("Mozilla");
  await expect(
    page.getByText(/Successful sign-ins for student@example.com/),
  ).toBeVisible();
  const firstTime = await times.first().getAttribute("datetime");
  await page.reload();
  await expect(times.first()).toHaveAttribute("datetime", firstTime);
  await page.getByRole("button", { name: "Refresh details" }).click();
  await expect(times.first()).toHaveAttribute("datetime", firstTime);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Recently signed in", exact: true }),
  ).toContainText("Mira Desai");
  await login(page);
  await page.getByRole("link", { name: "Last login", exact: true }).click();
  await expect(times.nth(1)).toHaveAttribute("datetime", firstTime);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page);
  await page.getByRole("link", { name: "Last login", exact: true }).click();
  await expect(times.nth(2)).toHaveAttribute("datetime", firstTime);
  await page.screenshot({
    path: "../docs/screenshots/last-login.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(table).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../docs/screenshots/last-login-mobile.png",
    fullPage: true,
  });
  const latestTime = await times.first().getAttribute("datetime");
  await page.evaluate(() => {
    const tokens = JSON.parse(sessionStorage.getItem("tokens"));
    tokens.access_token = "expired-access-token";
    sessionStorage.setItem("tokens", JSON.stringify(tokens));
  });
  await page.getByRole("button", { name: "Refresh details" }).click();
  await expect(times.first()).toHaveAttribute("datetime", latestTime);
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.route("**/api/v1/auth/login-history", (route) =>
    route.fulfill({ json: { items: [] } }),
  );
  await page.getByRole("button", { name: "Refresh details" }).click();
  await expect(page.getByText(/No login details recorded yet/)).toBeVisible();
  await page.unroute("**/api/v1/auth/login-history");
  await page.route("**/api/v1/auth/login-history", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Login history temporarily unavailable" },
    }),
  );
  await page.getByRole("button", { name: "Refresh details" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Login history temporarily unavailable",
  );
  await page.unroute("**/api/v1/auth/login-history");
  await page.getByRole("button", { name: "Refresh details" }).click();
  await expect(times.first()).toHaveAttribute("datetime", latestTime);
  expect(errors).toEqual([]);
});
test("ARFF to CSV and malformed-file feedback", async ({ page }) => {
  await login(page);
  await page.goto("/converter");
  await page
    .getByLabel("Dataset file")
    .setInputFiles(path.join(root, "samples/invalid.csv"));
  await page.getByRole("button", { name: "Upload & review schema" }).click();
  await expect(page.getByRole("alert")).toContainText("Line 3");
  await page
    .getByLabel("Dataset file")
    .setInputFiles(path.join(root, "samples/weather.arff"));
  await page.getByRole("button", { name: "Upload & review schema" }).click();
  await page.getByRole("button", { name: "Convert to CSV" }).click();
  await expect(page.locator("pre")).toContainText(
    "outlook,temperature,humidity,windy,observed_on",
  );
  await expect(page.getByRole("status")).toContainText(
    "Verification passed · Python CSV reader",
  );
});

test("administrator views and configuration", async ({ page }) => {
  await login(page, "admin");
  await page.getByRole("link", { name: "Administration", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Accounts", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("student@example.com", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(page.getByRole("status")).toContainText("Changes saved");
  await page.screenshot({
    path: "../docs/screenshots/admin.png",
    fullPage: true,
  });
});

test("failed output verification withholds preview and download", async ({
  page,
}) => {
  await login(page);
  await page.goto("/converter");
  await page.getByLabel("Dataset file").setInputFiles({
    name: "overflow.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("number\n1e999\n"),
  });
  await page.getByRole("button", { name: "Upload & review schema" }).click();
  await page.getByRole("button", { name: "Convert to ARFF" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Output verification failed",
  );
  await expect(page.getByRole("button", { name: "Download ARFF" })).toHaveCount(
    0,
  );
  await expect(page.locator("pre")).toHaveCount(0);
  await expect(page.getByText(/Verification passed/)).toHaveCount(0);
});

test("mobile layout and role redirect", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.screenshot({
    path: "../docs/screenshots/landing-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await login(page);
  await page.goto("/admin");
  await expect(page).toHaveURL(/dashboard/);
  await page.goto("/converter");
  await expect(
    page.getByRole("button", { name: "Upload & review schema" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/converter-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Sign out on mobile" }).click();
  await expect(page).toHaveURL(/login/);
});

test("registration, emailed verification, password recovery, and account deletion", async ({
  page,
}) => {
  const email = `browser-${Date.now()}@example.com`;
  const password = `Browser-${Date.now()}Aa`;
  const replacement = `Changed-${Date.now()}Bb`;
  const outbox = path.join(root, ".runtime/outbox");
  function actionLink(purpose) {
    for (const file of fs.readdirSync(outbox)) {
      const text = fs
        .readFileSync(path.join(outbox, file), "utf8")
        .replace(/=\r?\n/g, "")
        .replace(/=3D/g, "=");
      if (!text.includes(`To: ${email}`)) continue;
      const match = text.match(
        new RegExp(`https?://[^\\s<>]+/${purpose}\\?token=([A-Za-z0-9_-]+)`),
      );
      if (match) return `/${purpose}?token=${match[1]}`;
    }
    return "";
  }
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Browser Researcher");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("status")).toContainText("Account created");
  await expect.poll(() => actionLink("verify")).not.toBe("");
  await page.goto(actionLink("verify"));
  await page.getByRole("button", { name: "Verify email" }).click();
  await expect(page.getByRole("status")).toContainText("Email verified");
  await page.goto("/forgot");
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send link" }).click();
  await expect.poll(() => actionLink("reset")).not.toBe("");
  await page.goto(actionLink("reset"));
  await page.getByLabel("Password", { exact: true }).fill(replacement);
  await page.getByLabel("Confirm password").fill(replacement);
  await page.getByRole("button", { name: "Save new password" }).click();
  await expect(page.getByRole("status")).toContainText("Password reset");
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(replacement);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto("/profile");
  const deletion = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Delete account", exact: true }),
  });
  await deletion.getByLabel("Current password").fill(replacement);
  page.once("dialog", (dialog) => dialog.accept());
  await deletion.getByRole("button", { name: "Delete my account" }).click();
  await expect(page).toHaveURL(/login/);
  await expect(page.getByRole("status")).toContainText(
    "Account and conversion history deleted",
  );
});
