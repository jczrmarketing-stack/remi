import { expect, test } from "@playwright/test";

test("Bandeja distingue fría (con botones) de enfriando (sin botones)", async ({ page }) => {
  await page.goto("/bandeja");
  await expect(page.getByText("Automatizar las facturas")).toBeVisible();
  await expect(page.getByText("App de recetas con IA")).toBeVisible();

  const filaFria = page.getByRole("group", { name: "Automatizar las facturas" });
  await expect(filaFria.getByRole("button", { name: "Soltar" })).toBeVisible();

  const filaTibia = page.getByRole("group", { name: "App de recetas con IA" });
  await expect(filaTibia.getByRole("button", { name: "Soltar" })).toHaveCount(0);
});

test("soltar una idea la saca de la Bandeja", async ({ page }) => {
  await page.goto("/bandeja");
  await page.getByRole("button", { name: "Soltar" }).click();
  await expect(page.getByText("Automatizar las facturas")).toHaveCount(0);
});
