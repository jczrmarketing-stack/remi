import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";
const TELEFONO = { width: 375, height: 812 };

// El núcleo falso guarda estado entre pruebas: cada una arranca con el
// bloque abierto, que es el caso de siempre.
test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("Hoy muestra el bloque abierto con datos reales del núcleo falso", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Terminar el flujo de distribución" })).toBeVisible();
  await expect(page.locator('section[aria-label="Lo único de ahora"]').getByText(/upvisuals/i)).toBeVisible();
  // El nudge pendiente del núcleo falso.
  await expect(page.getByText("Hay 1 idea fría. ¿La miramos 2 minutos?")).toBeVisible();
});

test("responder el nudge lo hace desaparecer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Hay 1 idea fría")).toBeVisible();
  await page.getByRole("button", { name: "Listo" }).click();
  await expect(page.getByText("Hay 1 idea fría")).toHaveCount(0);
});

test("la plata de la semana trae la acción que cierra la brecha", async ({ page }) => {
  await page.goto("/");
  const plata = page.locator('section[aria-label="La plata de la semana"]');
  await expect(plata.getByText("faltan $1.900 este mes · cobrar la de Alfonso cierra $1.000")).toBeVisible();
});

test("el bloque dice de qué proyecto es, la fase, la entrega y el hito", async ({ page }) => {
  await page.goto("/");
  const foco = page.locator('section[aria-label="Lo único de ahora"]');
  await expect(foco.getByText(/^Upvisuals · Fase 1 · entrega /)).toBeVisible();
  await expect(foco.getByText(/^Entrega /)).toBeVisible();
  await expect(foco.getByText("$1.000")).toBeVisible();
  // Dos hitos hechos de cuatro: el encendido es el tercero.
  await expect(foco.getByText("hito 3 de 4")).toBeVisible();
  await expect(foco.getByText("la última vez: 1 h 20")).toBeVisible();
});

test("Paso mínimo muestra el paso de la tarea, en la voz de Remi", async ({ page }) => {
  await page.goto("/");
  const foco = page.locator('section[aria-label="Lo único de ahora"]');
  await expect(foco.getByText("Cinco minutos.")).toHaveCount(0);
  await foco.getByRole("button", { name: "Paso mínimo" }).click();
  await expect(foco.getByText("Cinco minutos.")).toBeVisible();
});

test("Además hoy trae la hora de cada cosa y lo que asoma mañana", async ({ page }) => {
  await page.goto("/");
  const ademas = page.locator('section[aria-label="Además hoy"]');
  await expect(ademas.getByText("Enviar factura a Alfonso")).toBeVisible();
  await expect(ademas.getByText("3:00 p")).toBeVisible();
  await expect(ademas.getByText("4:30 p")).toBeVisible();
  await expect(ademas.getByText("Mañana asoma: Llamada con el banco")).toBeVisible();
});

test("Vence junta tareas con fecha y entregas, y el rojo solo es para hoy", async ({ page }) => {
  await page.goto("/");
  const vence = page.locator('section[aria-label="Vence"]');
  const filas = vence.locator(".fila");
  await expect(filas).toHaveCount(3);
  await expect(filas.nth(0)).toContainText("Factura Omniway");
  await expect(filas.nth(0)).toContainText("hoy");
  await expect(filas.nth(1)).toContainText("Entrega Alfonso");
  await expect(filas.nth(1)).toContainText("$1.000");
  await expect(filas.nth(2)).toContainText("Formulario IRS");
  // Ley 3: ni contadores ni días de atraso.
  await expect(vence).not.toContainText(/atras|venci[óo] hace|días sin/i);
});

test("las ideas frías dicen cuándo es la revisión", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("1 idea fría espera la revisión · viernes 4:30 p")).toBeVisible();
});

test("cerrar el bloque celebra una vez y dice cuánto tomó", async ({ page }) => {
  await page.goto("/");
  await page.locator('section[aria-label="Lo único de ahora"]').getByRole("button", { name: "Cerrar hito a mano" }).click();
  const cerrado = page.locator('section[aria-label="Hito cerrado"]');
  await expect(cerrado.getByText("Cerrada. 42 min.")).toBeVisible();
  await expect(cerrado.getByText(/^Eso tomó .+\. Lo anoto para la próxima\.$/)).toBeVisible();
  await expect(cerrado.getByText(/^Upvisuals · Fase 1/)).toBeVisible();
  // La lista de cierre ya sabe a quién avisar: el cliente de la entrega.
  await expect(page.getByLabel("Cliente a avisar")).toHaveValue("Alfonso");
});

test("sin nada abierto, Remi propone por el orden del líder y el botón abre el bloque", async ({ page, request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: false } });
  await page.goto("/");
  const vacio = page.locator('section[aria-label="Nada abierto"]');
  await expect(vacio.getByRole("heading", { name: "Nada abierto." })).toBeVisible();
  // La entrega con dinero va primero.
  await expect(vacio.getByText(/la entrega de Alfonso va primero: vence .+ y trae \$1\.000\./)).toBeVisible();
  await expect(vacio.getByText("hito 3 de 4")).toBeVisible();
  // Lo anotado para hoy sigue ahí, con su hora.
  await expect(page.locator('section[aria-label="Además hoy"]').getByText("3:00 p")).toBeVisible();

  await vacio.getByRole("button", { name: "Empezar con eso" }).click();
  await expect(page.locator('section[aria-label="Lo único de ahora"]')).toBeVisible();
});

// B2/B4 (forma J): la tira «Al día», arriba de todo.
test("Al día trae sus tres líneas y mientras no estabas", async ({ page }) => {
  await page.goto("/");
  const alDia = page.locator('section[aria-label="Al día"]');
  await expect(alDia.getByText("ESTAMOS EN · upvisuals · Distribución")).toBeVisible();
  await expect(alDia.getByText(/^LO ÚLTIMO · Diste un commit/)).toBeVisible();
  await expect(alDia.getByText("SIGUE · Distribución")).toBeVisible();
  await expect(alDia.getByText("Mientras no estabas")).toBeVisible();
  await expect(alDia.getByText("Cobraste a Alfonso (1500)")).toBeVisible();
});

test("Al día en el teléfono no se sale de la pantalla", async ({ page }) => {
  await page.setViewportSize(TELEFONO);
  await page.goto("/");
  const alDia = page.locator('section[aria-label="Al día"]');
  await expect(alDia).toBeVisible();
  await expect(alDia.getByText("Mientras no estabas")).toBeVisible();
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
});
