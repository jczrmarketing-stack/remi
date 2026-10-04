import { expect, test } from "@playwright/test";

test("Ajustes: la biónica se guarda en localStorage y sobrevive un reload", async ({ page }) => {
  await page.goto("/ajustes");
  await expect(page.getByRole("switch", { name: "Lectura biónica desactivada" })).toBeVisible();

  await page.getByRole("switch", { name: "Lectura biónica desactivada" }).click();
  await expect(page.getByRole("switch", { name: "Lectura biónica activada" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("switch", { name: "Lectura biónica activada" })).toBeVisible();
});

test("cambiar la piel del Reloj queda marcada", async ({ page }) => {
  await page.goto("/ajustes");
  await page.getByRole("button", { name: "Brasa" }).click();
  await expect(page.getByRole("button", { name: "Brasa" })).toHaveAttribute("aria-pressed", "true");
});

// B1: el tope de gasto, con el núcleo real.
test("Ajustes: el tope de gasto se ve y el interruptor cambia", async ({ page }) => {
  await page.goto("/ajustes");
  const interruptor = page.locator('button[role="switch"][aria-label*="Tope de gasto"]');
  await expect(interruptor).toBeVisible();
  const estabaActivado = (await interruptor.getAttribute("aria-checked")) === "true";
  await interruptor.click();
  await expect(interruptor).toHaveAttribute("aria-checked", String(!estabaActivado));
  // Lo deja como estaba, para no afectar otras pruebas que corran después.
  await interruptor.click();
  await expect(interruptor).toHaveAttribute("aria-checked", String(estabaActivado));
});
