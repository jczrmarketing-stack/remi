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
