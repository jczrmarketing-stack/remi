import { expect, test } from "@playwright/test";

test("Proyectos muestra la constelación con los 2 libros", async ({ page }) => {
  await page.goto("/proyectos");
  const constelacion = page.locator('section[aria-label="Constelación de proyectos"]');
  await expect(constelacion.getByText("Upvisuals")).toBeVisible();
  await expect(constelacion.getByText("Distribución de contenido para el artista.")).toBeVisible();
  await expect(constelacion.getByText("mandar la propuesta.")).toBeVisible();
  await expect(constelacion.getByText("Malik")).toBeVisible();
  await expect(constelacion.getByText("sin Estado todavía")).toBeVisible();
  // El del bloque abierto (upvisuals) va primero y marcado.
  await expect(constelacion.getByText("Abierto ahora")).toBeVisible();
});

test("Proyectos muestra el camino del bloque abierto", async ({ page }) => {
  await page.goto("/proyectos");
  const camino = page.locator('section[aria-label^="Camino de"]');
  await expect(camino.getByText("Contrato firmado")).toBeVisible();
  await expect(camino.getByText("Distribución", { exact: true })).toBeVisible();
  // El hito futuro (aún no llegó ahí) sigue visible pero apagado, nunca oculto.
  await expect(camino.getByText("Seguridad crítica")).toBeVisible();
});

test("tocar un libro sin ## Camino no rompe la página", async ({ page }) => {
  await page.goto("/proyectos");
  await page.getByText("Malik").click();
  await expect(page.getByText("«Malik» todavía no tiene ## Camino.")).toBeVisible();
});
