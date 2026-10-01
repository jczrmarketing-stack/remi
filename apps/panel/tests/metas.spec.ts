import { expect, test } from "@playwright/test";

test("Metas muestra la meta mensual real, nunca un porcentaje solo", async ({ page }) => {
  await page.goto("/metas");
  await expect(page.getByText("$2.400/mes")).toBeVisible();
  await expect(page.getByText("21%")).toBeVisible();
  await expect(page.getByText("Brecha:")).toBeVisible();
  await expect(page.getByText("Alfonso").first()).toBeVisible();
});
