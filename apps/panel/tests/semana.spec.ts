import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("Semana arranca en 20:00, en la primera pregunta", async ({ page }) => {
  await page.goto("/semana");
  const revision = page.locator('section[aria-label="Revisión semanal"]');
  await expect(revision.getByText("20:00")).toBeVisible();
  await expect(revision.locator('li[aria-current="step"]')).toContainText("La plata del mes");
  await expect(revision.getByRole("heading", { name: "La locura de la semana" })).toBeVisible();
});

test("la plata llega contestada: por línea, la brecha y lo que la cierra", async ({ page }) => {
  await page.goto("/semana");
  await expect(
    page.getByText("Software $400 · Malik $100 · brecha $1.900. ¿Qué la cierra esta semana? Cobrar la de Alfonso cierra $1.000."),
  ).toBeVisible();
});

test("lo cerrado y lo aplazado traen sus nombres, y lo aplazado no lleva contador", async ({ page }) => {
  await page.goto("/semana");
  await expect(page.getByText("Contrato de UpVisuals y Biblia corta de Omniway. Se celebra una vez y se pasa.")).toBeVisible();
  const aplazado = page.getByText("Formulario IRS y Llamada con el banco. Sin contador: se reprograman y ya.");
  await expect(aplazado).toBeVisible();
  await expect(page.locator('section[aria-label="Revisión semanal"]')).not.toContainText(/\d+ (aplazad|pendiente|atrasad)/i);
});

test("las ideas frías se nombran y se deciden en la Bandeja", async ({ page }) => {
  await page.goto("/semana");
  await expect(page.getByText(/Una lista para revisar: Automatizar las facturas\. Soltar, mantener o hacer tarea\./)).toBeVisible();
  await page.getByRole("link", { name: "Abrir la Bandeja" }).click();
  await expect(page).toHaveURL(/\/bandeja$/);
});

test("la locura es una sola: lo que Remi propone por el orden del líder", async ({ page }) => {
  await page.goto("/semana");
  await expect(page.getByText(/Una sola\. Remi propone: Entrega de Alfonso\./)).toBeVisible();
  await expect(page.getByText(/La idea destacada: Router de leads que agenda solo\./)).toBeVisible();
});

test("destacar otra idea reemplaza a la anterior: una sola por semana", async ({ page }) => {
  await page.goto("/semana");
  const ideas = page.getByRole("list", { name: "Destacar una idea" });
  await expect(ideas.getByRole("button", { name: "Destacada" })).toHaveCount(1);
  await ideas.getByRole("listitem").filter({ hasText: "Automatizar las facturas" }).getByRole("button", { name: "Destacar" }).click();
  await expect(page.getByText(/La idea destacada: Automatizar las facturas\./)).toBeVisible();
  await expect(ideas.getByRole("button", { name: "Destacada" })).toHaveCount(1);
  // Y en la Bandeja es la que va arriba.
  await page.goto("/bandeja");
  await expect(page.locator('section[aria-label="Bandeja de ideas"]').getByRole("group").first()).toContainText("Automatizar las facturas");
});

test("«Siguiente paso» recorre las cinco preguntas y pone a andar el reloj", async ({ page }) => {
  await page.goto("/semana");
  const revision = page.locator('section[aria-label="Revisión semanal"]');
  await revision.getByRole("button", { name: "Siguiente paso" }).click();
  await expect(revision.locator('li[aria-current="step"]')).toContainText("Lo cerrado");
  await expect(revision.getByRole("button", { name: /^Pausar el reloj/ })).toBeVisible();
  for (let i = 0; i < 3; i++) await revision.getByRole("button", { name: "Siguiente paso" }).click();
  await expect(revision.locator('li[aria-current="step"]')).toContainText("La locura de la semana");
  // En la última ya no hay «siguiente»: queda cerrar.
  await expect(revision.getByRole("button", { name: "Siguiente paso" })).toHaveCount(0);
  await revision.getByRole("link", { name: "Guardar y cerrar" }).click();
  await expect(page).toHaveURL(/\/$/);
});

test("en el teléfono nada se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/semana");
  await expect(page.getByRole("heading", { name: "La plata del mes" })).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
