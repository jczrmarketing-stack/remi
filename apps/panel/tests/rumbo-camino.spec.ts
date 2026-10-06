import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("un camino listo: las seis preguntas, la prueba y las fuentes verificadas", async ({ page }) => {
  await page.goto("/rumbo/caminos/camino-1");
  await expect(page.getByText("listo")).toBeVisible();
  await expect(page.locator('section[aria-label="¿Hay a quién venderle?"]').getByText(/Negocios chicos/)).toBeVisible();
  await expect(page.locator('section[aria-label="¿Quién ya lo hace?"]').getByText(/Freelancers sueltos/)).toBeVisible();
  await expect(page.locator('section[aria-label="¿Qué objetó otro modelo?"]').getByText(/parecer alto/)).toBeVisible();
  await expect(page.locator('section[aria-label="Qué tan probable es"]').getByText("cirujano")).toBeVisible();
  await expect(page.locator('section[aria-label="La prueba que responde la duda"]').getByText(/Ofrecerlo a un cliente actual/)).toBeVisible();
  const fuentes = page.locator('section[aria-label="Fuentes"]');
  await expect(fuentes.getByText(/3 de 10 freelancers/)).toBeVisible();
  await expect(fuentes.getByText("verificada")).toBeVisible();
});

test("un camino investigando: lo dice sin romper la pantalla", async ({ page }) => {
  await page.goto("/rumbo/caminos/camino-2");
  await expect(page.locator(".chip", { hasText: "investigando" })).toBeVisible();
  await expect(page.getByText("Remi lo está investigando. Vuelve en un rato.")).toBeVisible();
});

test("un camino sin análisis pedido todavía: no rompe, ofrece volver", async ({ page }) => {
  await page.goto("/rumbo/caminos/camino-que-no-existe");
  await expect(page.getByText("Todavía no pedí un análisis para este camino.")).toBeVisible();
  await page.getByRole("link", { name: "Volver a Rumbo" }).click();
  await expect(page).toHaveURL(/\/rumbo$/);
});

test("desde Rumbo, el id del camino lleva a su análisis", async ({ page }) => {
  await page.goto("/rumbo");
  await page.getByLabel("Id del camino").fill("camino-1");
  await page.getByRole("button", { name: "Ver análisis" }).click();
  await expect(page).toHaveURL(/\/rumbo\/caminos\/camino-1$/);
  await expect(page.getByRole("heading", { name: "El análisis de un camino" })).toBeVisible();
});

test("en el teléfono nada se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/rumbo/caminos/camino-1");
  await expect(page.getByRole("heading", { name: "El análisis de un camino" })).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
