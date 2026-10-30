# Filtro de la verdad (bóveda + Rumbo)

**Problema (Juan Camilo, 30-oct):** quien publica una cifra muchas veces gana con ella. Un influencer que vende un curso dice «el 80 % de los negocios pierde clientes por no tener IA» y el número no sale de ningún estudio. Si la bóveda guarda eso como dato y Rumbo decide con eso, decidimos con mentiras.

**Principio:** ningún modelo «sabe» la verdad. Una cifra vale lo que vale su evidencia independiente. El filtro no responde «verdadero» o «falso»; responde **quién lo dice, qué gana diciéndolo, de dónde sale el número y si la realidad medida lo confirma**.

## Las 4 capas

### A · Quién lo dice y qué gana (conflicto de interés)
Por cada nota: ¿el autor vende algo relacionado (curso, mentoría, agencia, software, afiliado)? ¿Hay código de descuento, «link en mi bio», patrocinio? ¿La cifra favorece justo lo que vende?
Salida: `interes: alto | medio | bajo | desconocido` + la evidencia textual. Se hace local (reglas + Ollama), sin tokens.

### B · Qué tipo de afirmación es
Separar cada afirmación en: **cifra** (con número, unidad, lugar y fecha) · **anécdota** («yo facturé 10k») · **promesa** («vas a ganar») · **opinión**.
Solo las cifras pasan a la capa C. Las anécdotas quedan marcadas como «no verificable», no como falsas.

### C · Rastrear la cifra hasta la fuente primaria
1. ¿La nota cita fuente? Si no cita: `sin fuente`.
2. Buscar la fuente original y **traer la cita textual de la página**. Si no se encuentra la página real, no cuenta: los modelos inventan estudios.
3. Comparar: ¿la fuente dice lo mismo, en el mismo país, año y población? Marcar `respaldada | distorsionada (dice X, la fuente dice Y) | sin rastro | contradicha`.
4. Detectar **cifras circulares**: veinte artículos que se citan entre sí y ninguno llega al dato original.

**Jerarquía de fuentes** (de más a menos confiable):
- **T1:** datos oficiales primarios (BLS, Census, DANE, bancos centrales), reportes regulatorios (10-K de la SEC), estudios revisados por pares, y **nuestro propio trabajo de campo**.
- **T2:** firmas de investigación que publican su metodología y muestra, y medios que enlazan el dato original.
- **T3:** reportes de empresas que venden la solución, contenido patrocinado y agregadores que no citan el origen.
- **T4:** influencers, posts y videos sin fuente.

Cuesta búsquedas web, así que se hace solo para cifras de notas de oro y para las que Rumbo vaya a usar en una decisión (escalera de tokens: primero lo gratis).

### D · Trabajo de campo: medir la realidad en vez de creer reportes
Bots que observan señales públicas y dejan **hechos de campo** (T1, con fecha y método). Ejemplos para su negocio:
- **Demanda y precios reales:** cuántos servicios y pedidos hay en Fiverr/Upwork para «WhatsApp chatbot» o «automatización», precio mediano y rango, y reseñas recientes como señal de ventas.
- **Competencia:** cuántas agencias hay por nicho y ciudad (Google Maps) y qué precios publican.
- **Quién paga anuncios:** Meta Ad Library. Un anuncio activo por meses suele significar que es rentable.
- **Tendencia:** Google Trends del nicho.
- **Presupuesto:** ofertas de empleo del rol (si contratan, hay dinero).

Reglas: solo datos públicos; respetar términos de uso y límites; nunca cuentas falsas ni mensajes a personas haciéndose pasar por cliente.

## Cómo mejora sola
- Cada cifra tiene **confianza** que sube con fuentes independientes y con trabajo de campo, y baja con contradicciones.
- Cada **fuente (persona o sitio) tiene reputación**: si sus cifras resultan infladas, sus próximas afirmaciones arrancan con menos confianza.
- Los datos **envejecen** (ley de ceguera temporal): una cifra de mercado de hace 3 años pesa menos y se marca para re-medir.
- **Rumbo solo decide con cifras respaldadas** o de campo, y muestra la confianza de cada número.

## Fases
> **30-oct-2026, Juan Camilo:** Fase 1 hecha, sin puntaje de credibilidad: `estatus` (evidencia | hipotesis) como compuerta de fuente. Las fases 2 a 4 no van todavía: el trabajo de campo va antes que rastrear cifras de reels (`docs/revision/2026-10-30-sintesis.md`).

1. **Local, sin tokens** (va dentro de la acción 1 de Ollama): capas A y B por nota, más «¿cita fuente?». Campos en el frontmatter.
2. **Fuente primaria:** capa C para cifras de oro, tabla de reputación de fuentes (SQLite) y cifras circulares.
3. **Campo:** 2-3 bots semanales (precios y demanda en Fiverr/Upwork, Ad Library, Maps) que dejan hechos de campo en la bóveda.
4. **Rumbo:** consume solo evidencia ponderada y muestra la confianza.

## Cómo medimos que sirve
- Muestra de 20 cifras de reels: % con fuente primaria encontrada, % distorsionadas y error medio contra la fuente.
- Ninguna cifra marcada «respaldada» sin URL y cita textual verificables (auditoría por muestreo).
