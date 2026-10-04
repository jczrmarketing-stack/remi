# Licencias de terceros

Código de terceros que entró a este repo, con su aviso de licencia completo
(regla 10 del mega prompt de `docs/PLAN-FINAL.md`: solo MIT/Apache, con aviso).

## Metaculus/forecasting-tools — recalibrador logístico (R4.5)

`nucleo/calibracion.py` adapta la matemática de
`forecasting_tools/calibration_adjustment/logistic_recalibration_adjuster.py`
(https://github.com/Metaculus/forecasting-tools, consultado 2026-10-04): un
ajuste afín en log-odds (estilo Platt) — BIA y CON — vía regresión logística
sin regularizar sobre `(logit(p), resultado)`. Se adaptó para no sumar
`pandas`/`scikit-learn` como dependencias por un ajuste de dos parámetros: acá
el fit es un Newton-Raphson de una regresión logística de una variable,
escrito en `nucleo/calibracion.py`, sin la capa de `DataFrame` ni el soporte
de opción múltiple de la librería original (Remi solo pronostica binario). La
matemática del ajuste (`BIA`/`CON`, `mu(p) = sigmoid((logit(p) - BIA) / CON)`)
es la misma.

Licencia MIT del proyecto original:

```
MIT License

Copyright (c) 2024 CodexVeritas

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
