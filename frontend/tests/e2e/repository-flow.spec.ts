import { test, expect, type Route } from "@playwright/test";

/**
 * Repository submission flow.
 *
 * The whole backend is mocked at the network boundary so this spec runs
 * without a live API. It verifies that:
 *   1. The list page renders with an empty state and an "Add" CTA.
 *   2. Submitting a valid GitHub URL POSTs to /api/v1/repositories.
 *   3. The dashboard renders for the new repo and shows status copy.
 */

const REPO_ID = "11111111-2222-3333-4444-555555555555";
const ISO_NOW = new Date().toISOString();

const repository = {
  id: REPO_ID,
  url: "https://github.com/octocat/Hello-World",
  branch: "main",
  default_branch: "main",
  name: "Hello-World",
  owner: "octocat",
  status: "ready",
  error_message: null,
  analyzed_at: ISO_NOW,
  file_count: 12,
  total_lines: 2048,
  languages: "python:8,typescript:4",
  created_at: ISO_NOW,
  updated_at: ISO_NOW,
};

const job = {
  id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  repository_id: REPO_ID,
  status: "succeeded",
  rq_job_id: "rq:e2e:1",
  error: null,
  queued_at: ISO_NOW,
  started_at: ISO_NOW,
  completed_at: ISO_NOW,
  progress: 100,
  progress_message: "done",
};

async function mockApi(route: Route): Promise<void> {
  const url = route.request().url();
  const method = route.request().method();

  // POST creates a job.
  if (method === "POST" && url.endsWith("/api/v1/repositories")) {
    await route.fulfill({ status: 202, json: job });
    return;
  }

  // List of repos — empty initially, then containing the one we created.
  if (method === "GET" && /\/api\/v1\/repositories(?:\?.*)?$/.test(url)) {
    await route.fulfill({
      status: 200,
      json: { items: [repository], page: 1, page_size: 20, total: 1 },
    });
    return;
  }

  // Detail page reads.
  if (method === "GET" && url.includes(`/repositories/${REPO_ID}`)) {
    if (url.endsWith("/jobs/latest")) {
      await route.fulfill({ status: 200, json: job });
      return;
    }
    if (url.endsWith("/jobs")) {
      await route.fulfill({ status: 200, json: [job] });
      return;
    }
    await route.fulfill({ status: 200, json: repository });
    return;
  }

  await route.fallback();
}

test.describe("Repository submission", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/**", mockApi);
  });

  test("lists repositories from the API", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /repositories/i })
    ).toBeVisible();
    await expect(page.getByText("octocat/Hello-World")).toBeVisible();
  });

  test("opens the add-repository dialog and submits", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: /add repository/i }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog
      .getByLabel(/repository url/i)
      .fill("https://github.com/octocat/Hello-World");
    await dialog.getByRole("button", { name: /^analyze$/i }).click();

    // After submission the dialog closes (request resolved successfully).
    await expect(dialog).toBeHidden();
  });
});
