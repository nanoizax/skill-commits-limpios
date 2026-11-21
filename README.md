# skill-commits-limpios

**Cada commit dice qué se hizo y lo firma una persona. Nada de herramientas ni de IA en el historial, y un chequeo antes de publicar.**

Una skill obligatoria para tu herramienta de desarrollo, con un script que verifica de verdad (con 39 pruebas) y ganchos de Git para que la regla se cumpla sola.

---

## Para qué fue creada

Esta skill fue creada **para la comunidad**, con la finalidad de dar mejor respaldo y mejores procesos a la hora de hacer commits y push. Garantiza lo que subes a Git, tanto en la **autoría** (que el autor sea una persona) como en el contenido, y **quita o evita la mención de la IA** (o de la herramienta) en el commit. Además **valida el commit** que estás subiendo para ver si es coherente y te dice qué mejorar.

## ¿Qué es esto?

Tres piezas que trabajan juntas:

1. **`SKILL.md`**: las reglas que tu herramienta sigue en cada commit y push, y cómo te informa.
2. **`scripts/verificar_publicacion.py`**: comprueba el mensaje, el autor, lo que vas a subir y lo que se publica.
3. **`hooks/`**: ganchos de Git (`commit-msg`, `pre-commit`, `pre-push`) que **bloquean** lo que no cumple.

## El problema que resuelve

Cuando trabajas con una herramienta de desarrollo que escribe código, los commits se llenan de ruido que delata el origen o que simplemente están mal hechos:

- mensajes que dicen que lo hizo **una herramienta**, o con líneas de coautoría que nadie pidió;
- títulos como **"update"** o **"cambios"** que no dicen nada;
- autores que son un bot en vez de una persona;
- **claves, archivos `.env` o llaves** que se cuelan en el historial;
- pushes que **reescriben el historial** o van directo a la rama principal.

Corregirlo después es caro: reescribir historial y empujar muchas ramas a la fuerza, con el riesgo que eso trae. Aquí se corta **antes** de que salga.

## Para qué sirve

- Que **todo commit** tenga un título claro y una descripción, firmados por una **persona**.
- **Bloquear** menciones de herramientas, coautorías automáticas, secretos y archivos que no deben subirse.
- **Revisar un repositorio entero antes de hacerlo público**: cada commit, cada autor.
- Exigir el **formato de la empresa** (por ejemplo `TASK #123: …`), el **autor** y las **ramas protegidas**.
- Que tu herramienta te diga, tras publicar: *"Lo hice y está bien, pero te recomendaría revisar esto. ¿Publico así o prefieres mejorarlo?"*

## Cuándo usarla

- **Siempre** que haya un commit, un push, una rama o un pull request.
- Antes de **publicar por primera vez** un repositorio.
- Cuando heredas un historial y quieres saber si es presentable.

## Cuándo **no** usarla

- En repositorios **desechables** o de pruebas donde no importa el historial.
- Si necesitas **reescribir** historial ya publicado: la skill lo bloquea salvo orden expresa; hazlo con una herramienta específica y con todo respaldado.

## Cómo instalarla

1. Descarga este repositorio y copia su contenido en una carpeta llamada `commits-limpios` dentro del directorio de skills de tu herramienta de desarrollo.
2. **Tus términos propios:** copia `terminos.ejemplo.txt` a `~/.config/commit-limpio/terminos.txt` y escribe los nombres de las herramientas que no deben aparecer.
3. **(Opcional) Política del proyecto:** copia `politica.ejemplo.json` a `.commit-limpio/politica.json`.
4. **Ganchos (para que sea mecánico), en cada repositorio donde los quieras:**
   ```bash
   sh scripts/instalar_hooks.sh /ruta/al/repositorio
   ```
   Se instalan **solo en ese repositorio**; no tocan tu configuración global. Para quitarlos: `--desinstalar`.

Cada herramienta guarda sus skills en un sitio distinto; consulta la documentación de la tuya.

## Ejemplo

Un commit con problemas:

```
update

Hecho con herramienta-x
Co-Authored-By: Alguien <a@b.c>
```

El gancho lo **rechaza** y no crea el commit:

```
ESTO HAY QUE ARREGLAR ANTES DE PUBLICAR:
  ✗ Lleva una línea de coautoría (Co-Authored-By). Los commits llevan solo el autor humano.
  ✗ El mensaje menciona una herramienta o autoría automática ("herramienta-x"). Describe qué se hizo, no quién o con qué.
RECOMENDACIONES (no bloquean):
  • El título "update" es genérico. Debe decir qué se hizo en esta actividad.
```

Uno que pasa **con recomendaciones**:

```
RECOMENDACIONES (no bloquean):
  • El título mide 91 caracteres; conviene que no pase de 72.
  • Este commit toca 42 líneas y no tiene descripción. Explica qué cambia y por qué.
  Se puede publicar; te recomiendo revisar lo anterior. ¿Publicas así o prefieres mejorarlo?
```

## Qué incluye

- **Mensaje:** título claro (≤ 72 recomendado), descripción en commits grandes, sin coautoría ni menciones, formato exigido por la política.
- **Autor:** identidad configurada en el repositorio, nombre y apellido, que no sea una herramienta, y opcionalmente exigida.
- **Contenido:** secretos (claves, tokens, llaves privadas, contraseñas en el código), `.env` y llaves, archivos grandes, marcas de conflicto y TODO.
- **Push:** autores y mensajes de **lo nuevo**, rama protegida, reescritura de historial y, si lo configuras, las pruebas del proyecto.
- **Historial completo** antes de publicar un repositorio.

## Límites honestos

- **Los ganchos se pueden saltar** con `--no-verify`. La skill le prohíbe a tu herramienta usarlo, pero una garantía real necesita además protección de ramas en el servidor.
- **No entiende el código**: no sabe si tu cambio es correcto ni si tus pruebas son buenas. Corre las del proyecto, pero no las sustituye.
- La detección de **secretos** es por patrones: atrapa lo común, no todo. Para auditorías serias, usa además una herramienta especializada.
- Los nombres de **tus herramientas** los pones tú en `terminos.txt`: la skill no trae ninguno a propósito.
- El primer uso en un historial grande puede dar muchos avisos; empieza por revisar los errores.

## Skills relacionadas

[`skill-limpieza-de-texto`](https://github.com/nanoizax/skill-limpieza-de-texto) para los textos que acompañan a tus commits, README y publicaciones.

## Licencia y autoría

[MIT](LICENSE) · Hecha por Leandro Manuel Perez Montañana.
Más skills y herramientas gratis en **[soytegno.sonholab.com](https://soytegno.sonholab.com)** · TikTok [@soytegno](https://www.tiktok.com/@soytegno)
