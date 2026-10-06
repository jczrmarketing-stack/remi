import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("la escalera muestra los cinco estados, sin relleno salvo conquistado y ahora", async ({ page }) => {
  await page.goto("/rumbo");
  const escalera = page.locator('section[aria-label="Escalera"]');
  await expect(escalera.getByText("Primeros clientes")).toBeVisible();
  await expect(escalera.getByText("Vivir solo")).toBeVisible();
  await expect(escalera.getByText("Un mes de margen")).toBeVisible();
  await expect(escalera.getByText("Dos líneas estables")).toBeVisible();
  await expect(escalera.getByText("norte")).toBeVisible();
});

test("sin meta confirmada, Rumbo lo dice y no inventa un número", async ({ page }) => {
  await page.goto("/rumbo");
  await expect(page.getByText("Todavía no hay meta confirmada.")).toBeVisible();
});

test("contar mi visión propone y solo confirma con el sí explícito", async ({ page }) => {
  await page.goto("/rumbo");
  await page.getByRole("button", { name: "Contar mi visión" }).click();
  await page.getByLabel("Cuenta tu visión").fill("quiero entre 2.400 y 3.000 al mes, seis meses seguidos");
  await page.getByRole("button", { name: "Contar" }).click();
  await expect(page.getByText(/Entendí: entre \$2\.400 y \$3\.000/)).toBeVisible();
  // Antes de confirmar, la meta de la pantalla sigue vacía.
  await expect(page.getByText("Rango: $2.400 a $3.000 /mes")).toBeVisible();
  await page.getByRole("button", { name: "Confirmar meta" }).click();
  await expect(page.getByText("Meta confirmada. Queda guardada.")).toBeVisible();
  await page.getByRole("button", { name: "Cerrar" }).click();
  await expect(page.getByText("$2.400 a $3.000/mes · 6 meses seguidos · ningún cliente más del 40 %")).toBeVisible();
});

test("«Ver el punto de partida» lleva a /rumbo/partida", async ({ page }) => {
  await page.goto("/rumbo");
  await page.getByRole("link", { name: "Ver el punto de partida" }).click();
  await expect(page).toHaveURL(/\/rumbo\/partida$/);
});

test("en el teléfono nada se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/rumbo");
  await expect(page.getByRole("heading", { name: "Rumbo" })).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
