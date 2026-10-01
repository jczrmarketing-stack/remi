import { expect, test } from "@playwright/test";

test("Hoy muestra el bloque abierto con datos reales del núcleo falso", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Terminar el flujo de distribución" })).toBeVisible();
  await expect(page.getByText("upvisuals")).toBeVisible();
  // El nudge pendiente del núcleo falso.
  await expect(page.getByText("Hay 1 idea fría. ¿La miramos 2 minutos?")).toBeVisible();
});

test("responder el nudge lo hace desaparecer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Hay 1 idea fría")).toBeVisible();
  await page.getByRole("button", { name: "Listo" }).click();
  await expect(page.getByText("Hay 1 idea fría")).toHaveCount(0);
});
