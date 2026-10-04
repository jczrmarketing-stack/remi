import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";
const TELEFONO = { width: 375, height: 812 };

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("un proyecto de cliente: la fase en la que va, su monto y lo cobrado", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  await expect(page.getByText("Cliente · Alfonso")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "Upvisuals" })).toBeVisible();
  // Sigue siendo la vista «Proyectos».
  await expect(page.getByRole("navigation", { name: "Vistas" }).first().getByRole("link", { name: "Proyectos" })).toHaveAttribute("aria-current", "page");

  const fase = page.locator('section[aria-label="Fase actual y plata"]');
  await expect(fase.getByRole("heading", { name: "Fase 1 de 3" })).toBeVisible();
  await expect(fase.getByText("Distribución de contenido + seguridad crítica")).toBeVisible();
  await expect(fase.getByText("$5.000", { exact: true })).toBeVisible();
  await expect(fase.getByText("pagando")).toBeVisible();
  await expect(fase.getByText("cobrado $1.500 de $5.000")).toBeVisible();
  await expect(fase.getByRole("img", { name: "Cobrado de Fase 1: $1.500 de $5.000" })).toBeVisible();
  await expect(fase.getByText(/^próxima entrega: .+ · \$1\.000$/)).toBeVisible();
});

test("el camino: el hito encendido, qué significa y qué hace Remi en ese paso", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  const camino = page.locator('section[aria-label="Camino de Upvisuals"]');
  await expect(camino.getByText("Camino · SOP de cliente")).toBeVisible();
  await expect(camino.getByText("hito 3 de 4")).toBeVisible();
  await expect(camino.getByRole("heading", { name: "Distribución" })).toBeVisible();
  await expect(camino.getByText("El flujo de distribución corre con datos reales.")).toBeVisible();
  await expect(camino.getByText("Remi en este paso")).toBeVisible();
  await expect(camino.getByText("Escribe los encargos y lleva el camino.")).toBeVisible();
});

test("las fases de la propuesta, con su «listo cuando» o lo que falta", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  const fases = page.locator('section[aria-label="Fases de la propuesta"]');
  await expect(fases.getByText("con alcance: $8.700")).toBeVisible();
  await expect(fases.getByText("La demo de distribución corre con datos reales.")).toBeVisible();
  // La Fase 2 no tiene «listo cuando» en el libro: se dice, no se inventa.
  await expect(fases.getByText("Falta en el libro.")).toHaveCount(1);
  await expect(fases.getByText("sin monto")).toBeVisible();
  await expect(fases.getByText("Multi-cliente para agencias")).toBeVisible();
});

test("qué falta y el Estado del libro, en sus tres partes", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  const falta = page.locator('section[aria-label="Qué falta"]');
  await expect(falta.getByText("Qué falta · el que sigue")).toBeVisible();
  await expect(falta.getByText("04")).toBeVisible();
  await expect(falta.getByText("Seguridad crítica")).toBeVisible();
  await expect(falta.getByText("Accesos y llaves revisados antes de entregar.")).toBeVisible();

  const estado = page.locator('section[aria-label="Estado"]');
  await expect(estado.getByText("armando el contrato.")).toBeVisible();
  await expect(estado.getByText("cuotas con cinco días de tolerancia.")).toBeVisible();
  await expect(estado.getByText("mandar la propuesta.")).toBeVisible();
  await expect(estado.getByText(/^del libro · \d+ [a-z]{3}$/)).toBeVisible();
});

test("cerrar el hito lo anota en el libro, y se puede deshacer", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  const camino = page.locator('section[aria-label="Camino de Upvisuals"]');
  await camino.getByRole("button", { name: "Cerrar hito" }).click();
  await expect(camino.getByText("hito 4 de 4")).toBeVisible();
  await expect(camino.getByRole("heading", { name: "Seguridad crítica" })).toBeVisible();
  await expect(camino.getByText("Cerrado: Distribución. Quedó anotado en el libro.")).toBeVisible();

  await camino.getByRole("button", { name: "Deshacer" }).click();
  await expect(camino.getByText("hito 3 de 4")).toBeVisible();
  await expect(camino.getByRole("heading", { name: "Distribución" })).toBeVisible();
  await expect(camino.getByRole("button", { name: "Deshacer" })).toHaveCount(0);
});

// Forma K (B3.4): un hito que se cerró solo, con evidencia del servidor —
// sigue ahí aunque se recargue, a diferencia del «Cerrado:» de arriba.
test("un hito cerrado solo dice cómo, y deshacer lo vuelve a abrir", async ({ page, request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true, cerradoSolo: true } });
  await page.goto("/proyectos/upvisuals");
  const camino = page.locator('section[aria-label="Camino de Upvisuals"]');
  await expect(camino.getByText("Lo cerré por un encargo con pruebas en verde: contrato firmado.")).toBeVisible();

  await camino.getByRole("button", { name: "Deshacer" }).click();
  await expect(camino.getByText(/^Lo cerré por/)).toHaveCount(0);
});

test("en el teléfono, el hito cerrado solo también se ve y se deshace", async ({ page, request }) => {
  await page.setViewportSize(TELEFONO);
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true, cerradoSolo: true } });
  await page.goto("/proyectos/upvisuals");
  const camino = page.locator('section[aria-label="Camino de Upvisuals"]');
  await expect(camino.getByText(/^Lo cerré por/)).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);

  await camino.getByRole("button", { name: "Deshacer" }).click();
  await expect(camino.getByText(/^Lo cerré por/)).toHaveCount(0);
});

test("«Seguir con» abre el bloque del hito y lleva a Hoy", async ({ page, request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: false } });
  await page.goto("/proyectos/upvisuals");
  await page.locator('section[aria-label="Camino de Upvisuals"]').getByRole("button", { name: "Seguir con distribución" }).click();
  await expect(page.locator('section[aria-label="Lo único de ahora"]').getByRole("heading", { name: "Upvisuals · Distribución" })).toBeVisible();
});

test("un cliente sin fases todavía: el paso del camino y los tres que siguen", async ({ page }) => {
  await page.goto("/proyectos/beam");
  await expect(page.getByText("Cliente · Beto")).toBeVisible();
  await expect(page.locator('section[aria-label="Dónde va"]').getByRole("heading", { name: "Paso 4 de 10" })).toBeVisible();
  await expect(page.locator('section[aria-label="Fases de la propuesta"]')).toHaveCount(0);

  const falta = page.locator('section[aria-label="Qué falta"]');
  await expect(falta.getByText("Qué falta · los tres que siguen")).toBeVisible();
  await expect(falta.getByText("05")).toBeVisible();
  await expect(falta.getByText("Pago antes de arrancar")).toBeVisible();
  await expect(falta.getByText("Después: producción, entrega y capacitación, mensualidad.")).toBeVisible();
  // Hay otro bloque abierto (UpVisuals): seguir con este no abre nada.
  await page.locator('section[aria-label="Camino de BeaM"]').getByRole("button", { name: "Seguir con contrato" }).click();
  await expect(page.getByText("Hay otro bloque abierto. Ciérralo en Hoy y seguimos con este.")).toBeVisible();
});

test("un proyecto propio sin Estado lo dice sin drama", async ({ page }) => {
  await page.goto("/proyectos/omniway");
  await expect(page.getByText("Proyecto propio")).toBeVisible();
  await expect(page.locator('section[aria-label="Camino de Omniway"]').getByText("Camino · SOP propio")).toBeVisible();
  await expect(page.locator('section[aria-label="Estado"]').getByText("Este libro todavía no tiene Estado.")).toBeVisible();
});

test("un tema que no existe no rompe: ofrece volver", async ({ page }) => {
  await page.goto("/proyectos/no-existe");
  await expect(page.getByText("No tengo un libro con ese nombre.")).toBeVisible();
  await page.getByRole("link", { name: "Volver a Proyectos" }).click();
  await expect(page).toHaveURL(/\/proyectos$/);
});

test("en el teléfono: tramos en vez del camino largo, y «qué falta» antes que las fases", async ({ page }) => {
  await page.setViewportSize(TELEFONO);
  await page.goto("/proyectos/upvisuals");
  const camino = page.locator('section[aria-label="Camino de Upvisuals"]');
  await expect(camino.getByRole("img", { name: "2 de 4 hitos recorridos; el tercero está encendido." })).toBeVisible();
  await expect(camino.getByText("Recorrido: contrato firmado, anticipo recibido.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Ver el libro en Obsidian" })).toBeHidden();

  const yFalta = (await page.locator('section[aria-label="Qué falta"]').boundingBox())!.y;
  const yFases = (await page.locator('section[aria-label="Fases de la propuesta"]').boundingBox())!.y;
  expect(yFalta).toBeLessThan(yFases);

  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
