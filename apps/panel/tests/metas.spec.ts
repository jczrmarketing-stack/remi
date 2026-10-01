import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("la meta tiene nombre y horizonte, y nunca un porcentaje solo", async ({ page }) => {
  await page.goto("/metas");
  const meta = page.locator('section[aria-label="Meta: Vivir solo"]');
  await expect(meta.getByText("Meta · 12 meses")).toBeVisible();
  await expect(meta.getByRole("heading", { name: "Vivir solo" })).toBeVisible();
  await expect(meta.getByText("21%")).toBeVisible();
  // Al lado del porcentaje: el número del mes, la brecha y la acción.
  await expect(meta.getByText("necesitas $2.400/mes · este mes vas en $500")).toBeVisible();
  await expect(meta.getByText(/Brecha: \$1\.900\. Cobrar la de Alfonso cierra \$1\.000\./)).toBeVisible();
});

test("la acción de la brecha es un botón: con un bloque abierto, vuelve a él", async ({ page }) => {
  await page.goto("/metas");
  await page.locator('section[aria-label="Meta: Vivir solo"]').getByRole("button", { name: "Volver al bloque abierto" }).click();
  await expect(page.locator('section[aria-label="Lo único de ahora"]')).toBeVisible();
});

test("sin nada abierto, el botón abre el bloque de la entrega que cierra la brecha", async ({ page, request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: false } });
  await page.goto("/metas");
  await page.locator('section[aria-label="Meta: Vivir solo"]').getByRole("button", { name: "Seguir con la de Alfonso" }).click();
  await expect(page.locator('section[aria-label="Lo único de ahora"]').getByRole("heading", { name: "Entrega de Alfonso" })).toBeVisible();
});

test("«Ver clientes» lleva a Proyectos", async ({ page }) => {
  await page.goto("/metas");
  await page.getByRole("link", { name: "Ver clientes" }).click();
  await expect(page).toHaveURL(/\/proyectos$/);
});

test("por línea: lo que trajo cada una y cuál rinde más por hora", async ({ page }) => {
  await page.goto("/metas");
  const lineas = page.locator('section[aria-label="Por línea"]');
  await expect(lineas.getByRole("img", { name: "Software (clientes): $400 de $2.400 de la meta del mes" })).toBeVisible();
  await expect(lineas.getByRole("img", { name: "Malik (contenido): $100 de $2.400 de la meta del mes" })).toBeVisible();
  // 400 en 2 h contra 100 en 2 h.
  await expect(lineas.getByText("Software rinde 4× más por hora. Prioriza clientes.")).toBeVisible();
  // Lo cobrado del mes sigue a la vista, entrega por entrega.
  await expect(lineas.getByText("Beto")).toBeVisible();
  await expect(lineas.getByText("Canal de Malik")).toBeVisible();
});

test("la segunda meta duerme hasta que la primera pase de 50 %", async ({ page }) => {
  await page.goto("/metas");
  const carro = page.locator('section[aria-label="Meta: Carro"]');
  await expect(carro.getByText("Meta · 18 meses")).toBeVisible();
  await expect(carro.getByText("$1.100/mes")).toBeVisible();
  await expect(carro.getByText("Empieza cuando «Vivir solo» pase de 50 %. Hasta entonces, apagada.")).toBeVisible();
  // Apagada: sin anillo ni avance propio.
  await expect(carro.getByRole("img")).toHaveCount(0);
});

test("en el teléfono nada se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/metas");
  await expect(page.getByRole("heading", { name: "Vivir solo" })).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
