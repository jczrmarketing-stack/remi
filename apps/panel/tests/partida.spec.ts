import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("el punto de partida agrupa por tipo, con origen y dominio", async ({ page }) => {
  await page.goto("/rumbo/partida");
  await expect(page.getByRole("heading", { name: "Punto de partida" })).toBeVisible();
  const recursos = page.locator('section[aria-label="Recursos"]');
  await expect(recursos.getByText("Horas reales por semana")).toBeVisible();
  await expect(recursos.getByText("22 h")).toBeVisible();

  const habilidades = page.locator('section[aria-label="Habilidades"]');
  await expect(habilidades.getByText("Software para clientes")).toBeVisible();
  await expect(habilidades.getByText("cirujano")).toBeVisible();
  await expect(habilidades.getByText("aprendiz")).toBeVisible();

  const cuesta = page.locator('section[aria-label="Lo que cuesta"]');
  await expect(cuesta.getByText("Seguimiento de propuestas")).toBeVisible();
});

test("«Rumbo» vuelve a la pantalla principal", async ({ page }) => {
  await page.goto("/rumbo/partida");
  await page.locator("a.body-muted", { hasText: "Rumbo" }).click();
  await expect(page).toHaveURL(/\/rumbo$/);
});

test("en el teléfono nada se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/rumbo/partida");
  await expect(page.getByRole("heading", { name: "Punto de partida" })).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
