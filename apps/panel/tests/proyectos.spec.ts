import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";
const TELEFONO = { width: 375, height: 812 };

// El núcleo falso guarda estado entre pruebas: cada una arranca con el
// bloque abierto en UpVisuals y sus hitos sin tocar.
test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("la constelación ordena por el líder: la plata primero y más grande", async ({ page }) => {
  await page.goto("/proyectos");
  const constelacion = page.locator('section[aria-label="Constelación de proyectos"]');
  const circulos = constelacion.getByRole("button", { name: /: ver su camino$/ });
  // Upvisuals tiene la entrega con dinero; después, lo tocado hace menos.
  await expect(circulos).toHaveText(["Upvisuals", "BeaM", "Malik", "Omniway"]);

  const anchos = await circulos.evaluateAll((botones) => botones.map((b) => b.getBoundingClientRect().width));
  expect(anchos).toEqual([...anchos].sort((a, b) => b - a));
  expect(anchos[0]).toBeGreaterThan(anchos[3]);
});

test("cada proyecto dice de quién es, cuándo entrega y cuánto camino lleva", async ({ page }) => {
  await page.goto("/proyectos");
  const constelacion = page.locator('section[aria-label="Constelación de proyectos"]');
  // tipo · fecha de la entrega · hitos hechos / total.
  await expect(constelacion.getByText(/^cliente · .+ · 2\/4$/)).toBeVisible();
  await expect(constelacion.getByText("cliente · 3/10")).toBeVisible();
  await expect(constelacion.getByText("propio · 2/7")).toBeVisible();
  // Ley 3: progreso sí, contadores de atraso no.
  await expect(constelacion).not.toContainText(/atras|días sin|pendientes/i);
});

test("el camino del bloque abierto: fase, lo que falta y un solo paso encendido", async ({ page }) => {
  await page.goto("/proyectos");
  const camino = page.locator('section[aria-label="Camino de Upvisuals"]');
  await expect(camino.getByRole("heading", { name: "Upvisuals · Fase 1" })).toBeVisible();
  await expect(camino.getByText("Faltan 2")).toBeVisible();
  await expect(camino.getByText("Contrato firmado")).toBeVisible();
  // El hito futuro sigue visible pero apagado, nunca oculto.
  await expect(camino.getByText("Seguridad crítica")).toBeVisible();
  await expect(camino.locator('li[aria-current="step"]')).toHaveText("Distribución");
  await expect(camino.locator('li[aria-current="step"]')).toHaveCount(1);
});

test("el libro se abre en Obsidian, en la bóveda y el archivo que son", async ({ page }) => {
  await page.goto("/proyectos");
  const camino = page.locator('section[aria-label="Camino de Upvisuals"]');
  await expect(camino.getByRole("link", { name: "Ver el libro en Obsidian" })).toHaveAttribute(
    "href",
    "obsidian://open?vault=remi-mente&file=proyectos%2Fupvisuals",
  );
});

test("con el bloque abierto en ese proyecto, el botón vuelve al bloque", async ({ page }) => {
  await page.goto("/proyectos");
  await page.locator('section[aria-label="Camino de Upvisuals"]').getByRole("button", { name: "Volver al bloque abierto" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('section[aria-label="Lo único de ahora"]')).toBeVisible();
});

test("elegir otro proyecto muestra su camino y la última entrega cobrada", async ({ page }) => {
  await page.goto("/proyectos");
  await page.getByRole("button", { name: "BeaM: ver su camino" }).click();
  const camino = page.locator('section[aria-label="Camino de BeaM"]');
  await expect(camino.getByText("Faltan 7 · última entrega cobrada: $400")).toBeVisible();
  await expect(camino.locator('li[aria-current="step"]')).toHaveText("Contrato");
  await expect(camino.getByRole("button", { name: "Seguir con contrato" })).toBeVisible();
});

test("una cosa a la vez: con otro bloque abierto, Remi lo dice sin abrir nada", async ({ page }) => {
  await page.goto("/proyectos");
  await page.getByRole("button", { name: "Omniway: ver su camino" }).click();
  const camino = page.locator('section[aria-label="Camino de Omniway"]');
  await camino.getByRole("button", { name: "Seguir con biblia corta" }).click();
  await expect(camino.getByText("Hay otro bloque abierto. Ciérralo en Hoy y seguimos con este.")).toBeVisible();
  await expect(page).toHaveURL(/\/proyectos$/);
});

test("sin nada abierto, «Seguir con» abre el bloque de ese hito y lleva a Hoy", async ({ page, request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: false } });
  await page.goto("/proyectos");
  await page.getByRole("button", { name: "Omniway: ver su camino" }).click();
  await page.locator('section[aria-label="Camino de Omniway"]').getByRole("button", { name: "Seguir con biblia corta" }).click();
  const foco = page.locator('section[aria-label="Lo único de ahora"]');
  await expect(foco.getByRole("heading", { name: "Omniway · Biblia corta" })).toBeVisible();
  await expect(foco.getByText("hito 3 de 7")).toBeVisible();
});

test("un libro sin camino no rompe la página ni ofrece seguir", async ({ page }) => {
  await page.goto("/proyectos");
  await page.getByRole("button", { name: "Malik: ver su camino" }).click();
  const camino = page.locator('section[aria-label="Camino de Malik"]');
  await expect(camino.getByText("«Malik» todavía no tiene camino.")).toBeVisible();
  await expect(camino.getByRole("button", { name: /^Seguir con/ })).toHaveCount(0);
  await expect(camino.getByRole("link", { name: "Ver el proyecto" })).toHaveAttribute("href", "/proyectos/malik");
});

test("en el teléfono no hay constelación: una lista de caminos, el de plata arriba", async ({ page }) => {
  await page.setViewportSize(TELEFONO);
  await page.goto("/proyectos");
  await expect(page.getByRole("heading", { name: "Caminos" })).toBeVisible();
  await expect(page.locator('section[aria-label="Constelación de proyectos"]')).toBeHidden();

  const filas = page.getByRole("list", { name: "Caminos" }).getByRole("listitem");
  await expect(filas).toHaveCount(4);
  await expect(filas.nth(0)).toContainText("Upvisuals");
  await expect(filas.nth(0)).toContainText("Ahora: Distribución");
  await expect(filas.nth(0)).toContainText("$1.000");
  await expect(filas.nth(1)).toContainText("faltan 7");
  await expect(filas.nth(2)).toContainText("Sin camino todavía");

  // Nada se sale de la pantalla.
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);

  // Tocar una fila abre el proyecto.
  await filas.nth(0).getByRole("link").click();
  await expect(page).toHaveURL(/\/proyectos\/upvisuals$/);
});
