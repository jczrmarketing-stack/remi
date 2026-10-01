import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

// El núcleo falso guarda estado entre pruebas: la idea fría vuelve a la
// Bandeja antes y después de cada una.
test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("Bandeja distingue fría (con botones) de enfriando (sin botones)", async ({ page }) => {
  await page.goto("/bandeja");
  await expect(page.getByText("Automatizar las facturas")).toBeVisible();
  await expect(page.getByText("App de recetas con IA")).toBeVisible();

  const filaFria = page.getByRole("group", { name: "Automatizar las facturas" });
  await expect(filaFria.getByRole("button", { name: "Soltar" })).toBeVisible();
  await expect(filaFria.getByRole("button", { name: "Mantener 48 h más" })).toBeVisible();
  await expect(filaFria.getByRole("button", { name: "Hacer tarea" })).toBeVisible();

  // Solo la fila lista tiene botones.
  await expect(page.locator('section[aria-label="Bandeja de ideas"]').getByRole("button")).toHaveCount(3);
});

test("soltar una idea la saca de la Bandeja", async ({ page }) => {
  await page.goto("/bandeja");
  await page.getByRole("button", { name: "Soltar" }).click();
  await expect(page.getByText("Automatizar las facturas")).toHaveCount(0);
});

test("la cabecera dice cuándo es la revisión en frío", async ({ page }) => {
  await page.goto("/bandeja");
  await expect(page.getByText("revisión en frío · viernes 4:30 p · 10 min")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Bandeja · 3 enfriándose · 1 lista");
});

test("cada idea dice de qué tema es, o que está suelta", async ({ page }) => {
  await page.goto("/bandeja");
  const fria = page.getByRole("group", { name: "Automatizar las facturas" });
  await expect(fria.getByText("omniway · 50 h")).toBeVisible();
  await expect(fria.getByText("lista · revisar")).toBeVisible();

  const suelta = page.getByRole("group", { name: "App de recetas con IA" });
  await expect(suelta.getByText("suelta · 10 h")).toBeVisible();
  // Cuánto le falta para poder decidirse, no cuánto lleva «atrasada».
  await expect(suelta.getByText("enfriando · 38 h")).toBeVisible();

  await expect(page.getByRole("group", { name: "Curso de After Effects" }).getByText("aprender · 2 h")).toBeVisible();
});

test("la destacada de la semana va arriba; después la lista y lo que enfría", async ({ page }) => {
  await page.goto("/bandeja");
  const filas = page.locator('section[aria-label="Bandeja de ideas"]').getByRole("group");
  await expect(filas).toHaveCount(4);
  await expect(filas.nth(0)).toContainText("Router de leads que agenda solo");
  await expect(filas.nth(0)).toContainText("organic cash · destacada de la semana");
  await expect(filas.nth(1)).toContainText("Automatizar las facturas");
  await expect(filas.nth(2)).toContainText("App de recetas con IA");
  await expect(filas.nth(3)).toContainText("Curso de After Effects");
  // La destacada todavía enfría: no tiene botones.
  await expect(filas.nth(0).getByRole("button")).toHaveCount(0);
});

test("en el teléfono el estado baja debajo de la idea y nada se sale", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/bandeja");
  const fria = page.getByRole("group", { name: "Automatizar las facturas" });
  await expect(fria.getByText("lista · revisar")).toBeVisible();
  await expect(fria.getByRole("button", { name: "Mantener", exact: true })).toBeVisible();
  await expect(fria.getByRole("button", { name: "Tarea", exact: true })).toBeVisible();
  await expect(page.getByText("revisión en frío · viernes 4:30 p · 10 min")).toBeVisible();

  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
