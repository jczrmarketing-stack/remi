import { expect, test } from "@playwright/test";

// Sin NEXT_PUBLIC_URL_NUCLEO: el cliente pega a "/nucleo" (mismo origen) y
// next.config.mjs lo reenvía al núcleo falso. Esto es lo que hace posible
// abrir el panel desde el teléfono — ver playwright.config.ts (proyecto
// "rewrite", puerto aparte, build aparte).
test("Hoy carga sin NEXT_PUBLIC_URL_NUCLEO, pasando por /nucleo", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Terminar el flujo de distribución" })).toBeVisible();
  await expect(page.getByText("upvisuals")).toBeVisible();
});
