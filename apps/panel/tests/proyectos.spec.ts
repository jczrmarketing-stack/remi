import { expect, test } from "@playwright/test";

test("Proyectos muestra el camino del bloque abierto", async ({ page }) => {
  await page.goto("/proyectos");
  const camino = page.locator('section[aria-label^="Camino de"]');
  await expect(camino.getByText("Contrato firmado")).toBeVisible();
  await expect(camino.getByText("Distribución", { exact: true })).toBeVisible();
  // El hito futuro (aún no llegó ahí) sigue visible pero apagado, nunca oculto.
  await expect(camino.getByText("Seguridad crítica")).toBeVisible();
});

test("buscar un tema sin libro no rompe la página", async ({ page }) => {
  await page.goto("/proyectos");
  await page.getByPlaceholder("tema del libro, p. ej. upvisuals").fill("no-existe");
  await page.getByRole("button", { name: "Ver camino" }).click();
  await expect(page.getByText("Ese tema no tiene un libro con ## Camino.")).toBeVisible();
});
