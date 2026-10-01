import { expect, test } from "@playwright/test";

test("Semana arranca en 20:00 y muestra la plata real del mes", async ({ page }) => {
  await page.goto("/semana");
  await expect(page.getByText("20:00")).toBeVisible();
  await expect(page.getByText("$500 de $2.400")).toBeVisible();
  await expect(page.getByText("La locura de la semana")).toBeVisible();
});
