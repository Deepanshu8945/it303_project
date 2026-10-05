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
        new RegExp(`http://localhost:5173/${purpose}\\?token=([A-Za-z0-9_-]+)`),
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
  const deletion = page
    .locator("section")
    .filter({
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
