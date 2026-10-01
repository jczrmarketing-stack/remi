import { expect, test } from "@playwright/test";

const NUCLEO_FALSO = "http://localhost:4498";
const P_FASE_2 = "¿Cuándo está lista la Fase 2 de Upvisuals?";

test.beforeEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});
test.afterEach(async ({ request }) => {
  await request.post(`${NUCLEO_FALSO}/__escenario`, { data: { bloque: true } });
});

test("donde falta el dato está la pregunta de Remi: una sola, con su campo", async ({ page }, testInfo) => {
  await page.goto("/proyectos/upvisuals");
  const tarjeta = page.locator('section[aria-label="Remi pregunta"]');
  await expect(tarjeta.getByText(P_FASE_2)).toBeVisible();
  // La etiqueta del campo es la pregunta misma; el ejemplo es solo una pista.
  await expect(tarjeta.getByRole("textbox", { name: P_FASE_2 })).toHaveAttribute("placeholder", "Ej.: la demo corre con datos reales");
  await expect(tarjeta.getByRole("button", { name: "Responder" })).toBeVisible();
  await expect(tarjeta.getByRole("button", { name: "Después" })).toBeVisible();
  // Una a la vez: la segunda pregunta del libro no está a la vista.
  await expect(page.getByText("¿En qué carpeta está el código de Upvisuals?")).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("pregunta-escritorio.png") });
});

test("al contestarla, Remi lo confirma y el dato aparece en la pantalla", async ({ page }, testInfo) => {
  await page.goto("/proyectos/upvisuals");
  const fases = page.locator('section[aria-label="Fases de la propuesta"]');
  await expect(fases.getByText("Falta en el libro.")).toHaveCount(1);

  const tarjeta = page.locator('section[aria-label="Remi pregunta"]');
  await tarjeta.getByRole("textbox", { name: P_FASE_2 }).fill("Genera una imagen desde el panel");
  await tarjeta.getByRole("button", { name: "Responder" }).click();

  const anotado = page.locator('section[aria-label="Remi anotó la respuesta"]');
  await expect(anotado.getByText("Anotado. Quedó en el libro de Upvisuals.")).toBeVisible();
  await expect(fases.getByText("Genera una imagen desde el panel")).toBeVisible();
  await expect(fases.getByText("Falta en el libro.")).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath("pregunta-anotada.png") });

  // La siguiente espera a que se la pidan.
  await anotado.getByRole("button", { name: "Tengo otra pregunta" }).click();
  await expect(page.locator('section[aria-label="Remi pregunta"]').getByText("¿En qué carpeta está el código de Upvisuals?")).toBeVisible();
});

test("Enter también responde", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  const campo = page.getByRole("textbox", { name: P_FASE_2 });
  await campo.fill("La demo de imágenes corre sola");
  await campo.press("Enter");
  await expect(page.locator('section[aria-label="Remi anotó la respuesta"]')).toBeVisible();
});

test("«Después» calla la pregunta, sin contador, y no vuelve en la visita siguiente", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  await page.locator('section[aria-label="Remi pregunta"]').getByRole("button", { name: "Después" }).click();
  await expect(page.locator('section[aria-label="Remi pregunta"]')).toHaveCount(0);
  await expect(page.getByText(/pregunta(s)? pendiente|sin responder/i)).toHaveCount(0);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Fase 1 de 3" })).toBeVisible();
  await expect(page.getByText(P_FASE_2)).toHaveCount(0);
});

test("si Remi no entiende, vuelve a preguntar y no guarda nada", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  const tarjeta = page.locator('section[aria-label="Remi pregunta"]');
  await tarjeta.getByRole("textbox").fill("x");
  await tarjeta.getByRole("button", { name: "Responder" }).click();
  await expect(tarjeta.getByText("No te entendí. Dímelo en una frase corta.")).toBeVisible();
  await expect(tarjeta.getByRole("textbox")).toBeVisible();
  await expect(page.locator('section[aria-label="Fases de la propuesta"]').getByText("Falta en el libro.")).toHaveCount(1);
});

test("«Responder» sin texto no manda nada: lleva al campo", async ({ page }) => {
  await page.goto("/proyectos/upvisuals");
  const tarjeta = page.locator('section[aria-label="Remi pregunta"]');
  await tarjeta.getByRole("button", { name: "Responder" }).click();
  await expect(tarjeta.getByRole("textbox")).toBeFocused();
  await expect(tarjeta.getByText(P_FASE_2)).toBeVisible();
});

test("contestar el tipo de un libro lo deja dicho en su pantalla", async ({ page }) => {
  await page.goto("/proyectos/malik");
  await expect(page.getByText("Proyecto", { exact: true })).toBeVisible();
  const tarjeta = page.locator('section[aria-label="Remi pregunta"]');
  await tarjeta.getByRole("textbox", { name: "¿Malik es de un cliente o es tuyo?" }).fill("es mío");
  await tarjeta.getByRole("button", { name: "Responder" }).click();
  await expect(page.getByText("Anotado: Malik es propio.")).toBeVisible();
  await expect(page.getByText("Proyecto propio", { exact: true })).toBeVisible();
});

test("un libro al que no le falta nada no muestra ninguna pregunta", async ({ page }) => {
  await page.goto("/proyectos/beam");
  await expect(page.getByRole("heading", { name: "Paso 4 de 10" })).toBeVisible();
  await expect(page.locator('section[aria-label="Remi pregunta"]')).toHaveCount(0);
});

test("en el teléfono: el campo arriba, los dos botones debajo, nada se sale", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/proyectos/upvisuals");
  const tarjeta = page.locator('section[aria-label="Remi pregunta"]');
  const campo = (await tarjeta.getByRole("textbox").boundingBox())!;
  const responder = (await tarjeta.getByRole("button", { name: "Responder" }).boundingBox())!;
  const despues = (await tarjeta.getByRole("button", { name: "Después" }).boundingBox())!;
  expect(responder.y).toBeGreaterThan(campo.y + campo.height - 1);
  expect(Math.abs(responder.y - despues.y)).toBeLessThan(2);
  expect(responder.height).toBeGreaterThanOrEqual(44);
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(desborde).toBeLessThanOrEqual(0);
  await page.screenshot({ path: testInfo.outputPath("pregunta-telefono.png") });
});
