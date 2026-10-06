import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("la cuenta hacia atrás: mensualidades necesarias, tienes, y las propuestas de la semana", async ({ page }) => {
  await page.goto("/rumbo");
  const cuenta = page.locator('section[aria-label="Cuenta hacia atrás"]');
  await expect(cuenta.getByText("Necesitas 3 mensualidades de $1.000 para $2.400/mes. Tienes 1.")).toBeVisible();
  await expect(cuenta.getByText("Esta semana: 1 de 2 propuestas.")).toBeVisible();
  await expect(cuenta.getByText(/Cierras 3 de cada 10 propuestas, con tu propio dato \(8\)\./)).toBeVisible();
});

test("tus horas: el reparto de la semana por camino", async ({ page }) => {
  await page.goto("/rumbo");
  const horas = page.locator('section[aria-label="Cuenta hacia atrás"]');
  await expect(horas.getByRole("img", { name: "Clientes de software: 60% de la semana" })).toBeVisible();
  await expect(horas.getByRole("img", { name: "Malik (contenido): 30% de la semana" })).toBeVisible();
  await expect(horas.getByRole("img", { name: "Sin planear: 10% de la semana" })).toBeVisible();
});

test("apuestas: la activa muestra su señal y su progreso; la cerrada, su resultado", async ({ page }) => {
  await page.goto("/rumbo");
  const apuestas = page.locator('section[aria-label="Apuestas"]');
  const activa = apuestas.locator('[aria-label="Mensualidad de mantenimiento"]');
  await expect(activa.getByText("9 de 20 h")).toBeVisible();
  await expect(activa.getByText("sigue")).toBeVisible();

  const cerrada = apuestas.locator('[aria-label="Curso corto de edición"]');
  await expect(cerrada.getByText("pausa")).toHaveCount(2); // la señal y el resultado, ambos dicen "pausa"
});

test("en el teléfono nada se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/rumbo");
  await expect(page.locator('section[aria-label="Apuestas"]')).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
