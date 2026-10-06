import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("el motor lista las piezas del latido, sin rojo ni alarma", async ({ page }) => {
  await page.goto("/rumbo/motor");
  const latido = page.locator('section[aria-label="Latido"]');
  await expect(latido.getByText("El reloj")).toBeVisible();
  await expect(latido.getByText("Los pronósticos")).toBeVisible();
  await expect(latido.getByText(/callado 3 días/)).toBeVisible();
  // «La cuenta de la semana» lleva 1 día: por debajo del umbral de 2, no se marca callada.
  const filaCuenta = latido.locator(".fila", { hasText: "La cuenta de la semana" });
  await expect(filaCuenta).not.toContainText("callado");
});

test("desde Rumbo, «Ver el motor» lleva al latido", async ({ page }) => {
  await page.goto("/rumbo");
  await page.getByRole("link", { name: "Ver el motor" }).click();
  await expect(page).toHaveURL(/\/rumbo\/motor$/);
  await expect(page.getByRole("heading", { name: "El motor" })).toBeVisible();
});

test("en el teléfono nada se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/rumbo/motor");
  await expect(page.getByRole("heading", { name: "El motor" })).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});

// R5, punto 4: las cuatro pantallas de Rumbo construidas en las Tareas 1-4,
// a 375 px y en escritorio, sin overflow horizontal.
const PANTALLAS_RUMBO = ["/rumbo", "/rumbo/partida", "/rumbo/caminos/camino-1", "/rumbo/motor"];

for (const ruta of PANTALLAS_RUMBO) {
  test(`375 px: ${ruta} no desborda`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(ruta);
    await expect(page.locator("header.header, .tabbar").first()).toBeVisible();
    const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(desborde).toBeLessThanOrEqual(0);
  });

  test(`escritorio: ${ruta} no desborda`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(ruta);
    const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(desborde).toBeLessThanOrEqual(0);
  });
}
