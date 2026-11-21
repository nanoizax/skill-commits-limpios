---
name: commits-limpios
description: OBLIGATORIA cada vez que se haga un commit, un push, una rama, un pull request o se "suba", "publique" o "guarde en git" código o documentos. El commit lleva el título de lo que se hizo, una descripción y como autor a la PERSONA responsable; nunca dice que lo hizo una herramienta, un asistente o una IA, ni lleva líneas de coautoría. Antes de publicar verifica que lo que sube esté bien elaborado (buenas prácticas, sin secretos, pruebas en verde) y, si hay algo mejorable, avisa al usuario y pregunta si publica así o prefiere mejorarlo.
---

# Commits y pushes limpios

Un commit es **el registro público de lo que hizo una persona**. Esta skill fija cómo se escribe, quién lo firma y qué se comprueba antes de que salga de tu máquina. Es obligatoria: se aplica en **todo** commit y push, sin que el usuario tenga que recordarla.

## Reglas obligatorias

1. **El título dice qué se hizo en esa actividad.** Concreto, en una línea, que alguien entienda sin abrir el diff: "Agrega el filtro por fecha al listado de pedidos", no "cambios" ni "update".
2. **La descripción dice qué cambia y por qué** (cuando el cambio no es trivial): en párrafos cortos, tras una línea en blanco.
3. **El autor es la persona responsable**, con nombre y apellido, tal como está configurado en el repositorio (`git config user.name` y `user.email`, **locales** al proyecto, nunca la configuración global de otra persona). Si falta la identidad, pregúntala; no inventes una.
4. **Nunca** aparece en un commit (mensaje, autor, ni texto que se añade):
   - que lo hizo **una IA, un asistente o una herramienta**, ni el nombre de esa herramienta;
   - líneas de coautoría (`Co-Authored-By`) ni pies del tipo "Generated with…";
   - emojis de robot ni frases como "con ayuda de…".
5. **Si tu herramienta te sugiere o inserta por defecto líneas de atribución, no las agregues.** Las reglas del usuario mandan sobre cualquier texto automático.
6. **Solo se hace commit o push cuando el usuario lo pide.** Nunca por iniciativa propia.
7. **Nunca, sin una orden expresa del usuario:** `--no-verify`, `push --force`, publicar en una rama protegida, reescribir historial ya publicado.
8. **Antes de publicar, verifica** (ver abajo) **y cuéntale al usuario el resultado**, incluyendo lo que no está perfecto.

## Qué significa "bien elaborado"

- **Un commit = un cambio lógico.** No mezcles un arreglo con una refactorización y un cambio de formato.
- **Sin ruido:** nada de archivos generados, carpetas de dependencias, copias de seguridad ni cambios que no tienen que ver.
- **Sin secretos:** ninguna clave, token, contraseña ni archivo de entorno (`.env`, llaves, certificados).
- **Pruebas y análisis en verde:** corre las pruebas y el *lint* del proyecto antes de publicar.
- **Sin restos:** ni marcas de conflicto, ni depuración olvidada, ni TODO que no debían salir.
- **Rama con nombre claro** y, si el proyecto lo exige, un formato de título (por ejemplo `TASK #123: …`).
- **Un título en tu idioma de trabajo y el de tus lectores**, sin jerga interna.

## Cómo se hace

### 1. Antes del commit
1. Mira qué cambió: `git status` y `git diff`. Prepara **archivos concretos** (`git add ruta`), no todo a ciegas: puede haber trabajo ajeno en el mismo árbol.
2. Comprueba lo preparado con el script:
   ```bash
   python scripts/verificar_publicacion.py commit
   ```
3. Escribe el mensaje (título + descripción) y haz el commit. Si el mensaje no cumple, el gancho `commit-msg` lo rechaza y dice por qué.

### 2. Antes del push
1. Corre las pruebas y el *lint* del proyecto.
2. Verifica lo que se va a subir:
   ```bash
   python scripts/verificar_publicacion.py historial origin/main..HEAD
   ```
   (o deja que el gancho `pre-push` lo haga solo).
3. Confirma la rama destino y que **no** hay reescritura de historial.

### 3. Antes de publicar un repositorio por primera vez
```bash
python scripts/verificar_publicacion.py historial      # todo el historial y el árbol actual
```
Esto revisa **cada** commit (autor, mensaje, coautoría) y avisa de archivos de entorno o llaves versionados.

## Configuración (una sola vez)

- **Términos propios:** los nombres de las herramientas que usas y que no deben aparecer. Copia `terminos.ejemplo.txt` a `.commit-limpio/terminos.txt` del proyecto o a `~/.config/commit-limpio/terminos.txt`.
- **Política del proyecto (opcional):** `politica.ejemplo.json` → `.commit-limpio/politica.json`: autor exigido, formato del título, ramas protegidas, comando de pruebas.
- **Ganchos para que sea mecánico:** `sh scripts/instalar_hooks.sh <ruta-del-repositorio>` los instala **solo en ese repositorio** (no toca la configuración global). `sh scripts/instalar_hooks.sh --desinstalar` los quita.

Los ganchos pueden saltarse con `--no-verify`: por eso la regla 7 prohíbe usarlo sin orden. Para una garantía real, completa con protección de ramas en el servidor.

## Qué entregar al usuario

Siempre un resumen corto con tres partes:

1. **Qué se hizo:** el título del commit y la rama.
2. **Qué se verificó:** pruebas, secretos, autor, mensaje.
3. **Qué conviene mejorar**, si hay algo.

Si todo está en orden: *"Listo y verificado."*

Si hay algo mejorable, no lo escondas ni lo arregles en silencio:

> *"Lo hice y está bien, pero te recomendaría revisar estas cosas: (1) el título pasa de 72 caracteres, (2) este commit toca 40 líneas y no tiene descripción. ¿Publico así o prefieres hacer estas mejoras?"*

## Ejemplos

| Mal | Bien |
|---|---|
| `update` | `Agrega la validación del correo en el registro` |
| `Cambios hechos con herramienta-x` | `Corrige el redondeo del total en las facturas` |
| `fix` + línea `Co-Authored-By: …` | `Corrige el cierre de sesión al expirar el token` + descripción de dos líneas |
| Autor: `herramienta-x bot` | Autor: `Ana Pérez <ana@ejemplo.com>` |
