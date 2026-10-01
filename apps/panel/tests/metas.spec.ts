import { expect, test } from "@playwright/test";

test("Metas muestra la meta mensual real, nunca un porcentaje solo", async ({ page }) => {
  await page.goto("/metas");
  await expect(page.getByText("$2.400/mes")).toBeVisible();
  await expect(page.getByText("21%")).toBeVisible();
  await expect(page.getByText("Brecha:")).toBeVisible();
  await expect(page.getByText("Alfonso").first()).toBeVisible();
});

test("debajo de la brecha hay una acción con número", async ({ page }) => {
  await page.goto("/metas");
  // proximo: Alfonso $1.000, faltan $1.900 -> cierra el monto de la entrega.
  await expect(page.getByText("Cobrar la de Alfonso cierra $1.000.")).toBeVisible();
});

test("ingreso por línea lista las entregas cobradas del mes", async ({ page }) => {
  await page.goto("/metas");
  const ingreso = page.locator('section[aria-label="Ingreso por línea"]');
  await expect(ingreso.getByText("Beto")).toBeVisible();
  await expect(ingreso.getByText("$500")).toBeVisible();
});
