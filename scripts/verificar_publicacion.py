#!/usr/bin/env python3
"""verificar_publicacion.py: comprueba un commit o un push ANTES de publicarlo.

Modos:
  mensaje <archivo>   revisa el mensaje de un commit (gancho commit-msg)
  commit              revisa lo que está en el área de preparación (gancho pre-commit)
  push [remoto] [url] revisa lo que se va a subir; lee de la entrada estándar las líneas que Git entrega (gancho pre-push)
  historial [RANGO]   revisa mensajes y autores de todo el historial (o de un rango) y el árbol actual

Separa lo que BLOQUEA (errores) de lo que solo se RECOMIENDA (avisos). Solo biblioteca estándar de Python 3.8+.
Política opcional en  <repo>/.commit-limpio/politica.json  y términos propios en  <repo>/.commit-limpio/terminos.txt
(o en ~/.config/commit-limpio/terminos.txt, o en la variable COMMIT_LIMPIO_TERMINOS).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

CEROS = "0" * 40

# Patrones GENERALES sobre autoría automática. Los nombres de herramientas concretas NO van aquí:
# cada persona los pone en su archivo de términos (ver terminos.ejemplo.txt).
GENERALES = [
    r"co-authored-by\s*:",
    r"generated (?:by|with|using)\b",
    r"generado (?:por|con)\b[^.\n]{0,30}\b(?:ia|inteligencia artificial|asistente|bot)\b",
    r"hecho (?:por|con ayuda de)\b[^.\n]{0,30}\b(?:ia|inteligencia artificial|asistente|bot)\b",
    r"(?:escrito|creado|redactado) (?:por|con)\b[^.\n]{0,30}\b(?:ia|inteligencia artificial|asistente)\b",
    r"\bai[- ]generated\b",
    r"with the help of (?:an? )?(?:ai|assistant)\b",
    r"\U0001F916",
]
TRAILER = re.compile(r"^\s*co-authored-by\s*:", re.I | re.M)
GENERICOS = {"update", "updates", "fix", "fixes", "changes", "cambios", "arreglos", "arreglo", "wip", "misc", "varios",
             "test", "tests", "actualizacion", "actualización", "commit", "initial commit", "ajustes", "mejoras", "cosas"}

SECRETOS = [
    (r"AKIA[0-9A-Z]{16}", "clave de acceso de AWS"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", "llave privada"),
    (r"ghp_[A-Za-z0-9]{30,}", "token de GitHub"),
    (r"\bsk-[A-Za-z0-9_-]{20,}", "llave de API"),
    (r"xox[bpa]-[A-Za-z0-9-]{10,}", "token de Slack"),
    (r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]", "credencial escrita en el código"),
]
ARCHIVOS_PROHIBIDOS = re.compile(r"(^|/)(\.env(\..+)?|id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.pfx|.*\.keystore|.*\.jks)$", re.I)
EJEMPLOS_OK = re.compile(r"\.(example|sample|template|ejemplo)$", re.I)


# --------------------------------------------------------------------------- utilidades de Git

def git(repo: str, *args: str, check: bool = False) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def raiz_repo(inicio: str = ".") -> str:
    r = subprocess.run(["git", "-C", inicio, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Esto no es un repositorio de Git.")
    return r.stdout.strip()


# --------------------------------------------------------------------------- política y términos

def cargar_politica(repo: str) -> dict:
    p = os.path.join(repo, ".commit-limpio", "politica.json")
    if os.path.isfile(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except ValueError as e:
            sys.exit(f"politica.json no es un JSON válido: {e}")
    return {}


def cargar_terminos(repo: str) -> list[re.Pattern]:
    """Patrones generales + los términos propios de la persona (nombres de herramientas, etc.)."""
    pats = [re.compile(p, re.I) for p in GENERALES]
    rutas = [os.environ.get("COMMIT_LIMPIO_TERMINOS", ""),
             os.path.join(repo, ".commit-limpio", "terminos.txt"),
             os.path.join(os.path.expanduser("~"), ".config", "commit-limpio", "terminos.txt")]
    for ruta in rutas:
        if ruta and os.path.isfile(ruta):
            for linea in open(ruta, encoding="utf-8"):
                linea = linea.strip()
                if not linea or linea.startswith("#"):
                    continue
                if linea.startswith("re:"):          # expresión regular
                    pats.append(re.compile(linea[3:], re.I))
                else:                                # texto literal
                    pats.append(re.compile(re.escape(linea), re.I))
    return pats


def coincide(texto: str, pats: list[re.Pattern]):
    for p in pats:
        m = p.search(texto)
        if m:
            return m.group(0)
    return None


# --------------------------------------------------------------------------- reglas

def revisar_mensaje(msg: str, pats, pol: dict, cambios: int = 0):
    """Devuelve (errores, avisos) de un mensaje de commit."""
    errores, avisos = [], []
    lineas = [l for l in msg.splitlines() if not l.startswith("#")]
    while lineas and not lineas[-1].strip():
        lineas.pop()
    texto = "\n".join(lineas)
    if not texto.strip():
        return ["El mensaje está vacío: escribe un título que diga qué se hizo."], avisos
    titulo = lineas[0].strip()
    cuerpo = [l for l in lineas[1:] if l.strip()]

    if TRAILER.search(texto):
        errores.append("Lleva una línea de coautoría (Co-Authored-By). Los commits llevan solo el autor humano.")
    # se busca en el resto del texto, sin las líneas de coautoría, para avisar de AMBAS cosas en una sola pasada
    sin_coautoria = "\n".join(l for l in lineas if not re.match(r"\s*co-authored-by\s*:", l, re.I))
    hallado = coincide(sin_coautoria, pats)
    if hallado:
        errores.append(f"El mensaje menciona una herramienta o autoría automática («{hallado.strip()}»). Describe qué se hizo, no quién o con qué.")

    maximo = int(pol.get("max_titulo", 72))
    if len(titulo) > max(maximo, 100):
        errores.append(f"El título mide {len(titulo)} caracteres: es demasiado largo (máximo recomendado {maximo}).")
    elif len(titulo) > maximo:
        avisos.append(f"El título mide {len(titulo)} caracteres; conviene que no pase de {maximo}.")
    if titulo.lower().rstrip(".") in GENERICOS or len(titulo.split()) < 2:
        avisos.append(f"El título «{titulo}» es genérico. Debe decir qué se hizo en esta actividad.")
    if titulo.endswith("."):
        avisos.append("El título no necesita punto final.")
    if len(lineas) > 1 and lineas[1].strip():
        avisos.append("Deja una línea en blanco entre el título y la descripción.")
    if not cuerpo and cambios > 30:
        avisos.append(f"Este commit toca {cambios} líneas y no tiene descripción. Explica qué cambia y por qué.")
    prefijo = pol.get("prefijo")
    if prefijo and not re.match(prefijo, titulo):
        errores.append(f"El título no sigue el formato que exige la política del proyecto ({prefijo}).")
    return errores, avisos


def revisar_identidad(repo: str, pats, pol: dict):
    errores, avisos = [], []
    nombre = git(repo, "config", "user.name").strip()
    correo = git(repo, "config", "user.email").strip()
    nombre_l = git(repo, "config", "--local", "user.name").strip()
    correo_l = git(repo, "config", "--local", "user.email").strip()
    if not nombre or not correo:
        errores.append("No hay identidad configurada (user.name y user.email).")
        return errores, avisos
    if not (nombre_l and correo_l):
        avisos.append("La identidad viene de la configuración global, no de este repositorio. Si el proyecto exige una identidad propia, fíjala con git config (sin --global).")
    if len(nombre.split()) < 2:
        avisos.append(f"El nombre del autor («{nombre}») parece corto. Usa nombre y apellido.")
    h = coincide(nombre + " " + correo, pats)
    if h:
        errores.append(f"La identidad del autor parece una herramienta o un bot («{h.strip()}»). Debe ser una persona.")
    esperado_n, esperado_c = pol.get("autor_nombre"), pol.get("autor_email")
    if esperado_n and nombre != esperado_n:
        errores.append(f"El autor es «{nombre}» y la política del proyecto exige «{esperado_n}».")
    if esperado_c and correo != esperado_c:
        errores.append(f"El correo del autor es «{correo}» y la política del proyecto exige «{esperado_c}».")
    return errores, avisos


def lineas_agregadas(repo: str, *args: str):
    """Itera (archivo, linea) de las líneas añadidas por un diff."""
    salida = git(repo, "diff", "--unified=0", "--no-color", *args)
    archivo = None
    for l in salida.splitlines():
        if l.startswith("+++ b/"):
            archivo = l[6:]
        elif l.startswith("+") and not l.startswith("+++"):
            yield archivo, l[1:]


def revisar_preparado(repo: str, pats, pol: dict):
    errores, avisos = [], []
    estado = git(repo, "diff", "--cached", "--name-status", "--no-color")
    if not estado.strip():
        return ["No hay nada preparado para commitear."], avisos
    for l in estado.splitlines():
        partes = l.split("\t")
        ruta = partes[-1]
        if partes[0][0] in "AM" and ARCHIVOS_PROHIBIDOS.search(ruta) and not EJEMPLOS_OK.search(ruta):
            errores.append(f"Archivo que no debe subirse: {ruta} (credenciales, llaves o variables de entorno).")
        full = os.path.join(repo, ruta)
        if partes[0][0] in "AM" and os.path.isfile(full) and os.path.getsize(full) > 5 * 1024 * 1024:
            avisos.append(f"{ruta} pesa {os.path.getsize(full) // (1024 * 1024)} MB. ¿Debe ir al repositorio?")
    vistos = set()
    for archivo, linea in lineas_agregadas(repo, "--cached"):
        for rx, que in SECRETOS:
            if re.search(rx, linea) and (archivo, que) not in vistos:
                vistos.add((archivo, que))
                errores.append(f"Posible {que} en {archivo}. Quítala y usa una variable de entorno.")
        if re.match(r"^(<<<<<<<|>>>>>>>) ", linea) or linea.strip() == "=======":
            errores.append(f"Marca de conflicto sin resolver en {archivo}.")
        h = coincide(linea, pats)
        if h and (archivo, "t") not in vistos:
            vistos.add((archivo, "t"))
            avisos.append(f"{archivo}: el texto añadido menciona «{h.strip()}». Revisa que no delate una autoría automática.")
        if re.search(r"\b(TODO|FIXME|XXX)\b", linea) and (archivo, "todo") not in vistos:
            vistos.add((archivo, "todo"))
            avisos.append(f"{archivo}: queda un TODO/FIXME.")
    return errores, avisos


def commits_en(repo: str, rango: str):
    return [c for c in git(repo, "rev-list", "--reverse", rango).split() if c]


def revisar_commit_publicado(repo: str, sha: str, pats, pol: dict):
    """Para un commit ya hecho. Aquí la autoría y los términos BLOQUEAN; el estilo solo avisa."""
    errores, avisos = [], []
    autor, correo, msg = git(repo, "log", "-1", "--format=%an%x00%ae%x00%B", sha).split("\x00", 2)
    corto = sha[:8]
    e, a = revisar_mensaje(msg, pats, pol)
    for x in e:
        # el estilo (título largo/formato) no bloquea un commit que ya existe; la autoría y los términos sí
        (errores if ("coautoría" in x or "menciona" in x or "formato que exige" in x) else avisos).append(f"{corto}: {x}")
    avisos += [f"{corto}: {x}" for x in a]
    h = coincide(autor + " " + correo, pats)
    if h:
        errores.append(f"{corto}: el autor parece una herramienta o un bot («{h.strip()}»).")
    if pol.get("autor_email") and correo != pol["autor_email"]:
        errores.append(f"{corto}: el correo del autor es «{correo}» y la política exige «{pol['autor_email']}».")
    return errores, avisos


def revisar_arbol(repo: str, pats):
    avisos = []
    for ruta in git(repo, "ls-files").splitlines():
        if ARCHIVOS_PROHIBIDOS.search(ruta) and not EJEMPLOS_OK.search(ruta):
            avisos.append(f"El repositorio versiona {ruta} (credenciales, llaves o variables de entorno).")
    return [], avisos


# --------------------------------------------------------------------------- informe

def informe(titulo: str, errores: list, avisos: list, como_json: bool = False) -> int:
    if como_json:
        print(json.dumps({"errores": errores, "recomendaciones": avisos}, ensure_ascii=False, indent=2), file=sys.stderr)
    else:
        print(f"\n== {titulo} ==", file=sys.stderr)
        if errores:
            print("ESTO HAY QUE ARREGLAR ANTES DE PUBLICAR:", file=sys.stderr)
            for e in errores:
                print(f"  ✗ {e}", file=sys.stderr)
        if avisos:
            print("RECOMENDACIONES (no bloquean):", file=sys.stderr)
            for a in avisos:
                print(f"  • {a}", file=sys.stderr)
        if not errores and not avisos:
            print("  Todo en orden.", file=sys.stderr)
        elif not errores:
            print("  Se puede publicar; te recomiendo revisar lo anterior. ¿Publicas así o prefieres mejorarlo?", file=sys.stderr)
    return 1 if errores else 0


# --------------------------------------------------------------------------- modos

def modo_mensaje(a) -> int:
    repo = raiz_repo(a.repo)
    pol, pats = cargar_politica(repo), cargar_terminos(repo)
    msg = open(a.archivo, encoding="utf-8", errors="replace").read()
    cambios = sum(1 for _ in lineas_agregadas(repo, "--cached"))
    e, av = revisar_mensaje(msg, pats, pol, cambios)
    return informe("Mensaje del commit", e, av, a.json)


def modo_commit(a) -> int:
    repo = raiz_repo(a.repo)
    pol, pats = cargar_politica(repo), cargar_terminos(repo)
    e1, a1 = revisar_identidad(repo, pats, pol)
    e2, a2 = revisar_preparado(repo, pats, pol)
    return informe("Commit: identidad y contenido preparado", e1 + e2, a1 + a2, a.json)


def modo_push(a) -> int:
    repo = raiz_repo(a.repo)
    pol, pats = cargar_politica(repo), cargar_terminos(repo)
    errores, avisos = [], []
    remoto = a.remoto or "origin"
    for linea in sys.stdin.read().splitlines():
        partes = linea.split()
        if len(partes) < 4:
            continue
        ref_local, sha_local, ref_remota, sha_remoto = partes[:4]
        if sha_local == CEROS:
            continue  # borrado de rama
        rama = ref_remota.replace("refs/heads/", "")
        if rama in pol.get("ramas_protegidas", []):
            errores.append(f"«{rama}» es una rama protegida: no se publica directamente en ella.")
        if sha_remoto != CEROS:
            if subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", sha_remoto, sha_local]).returncode != 0 \
                    and os.environ.get("COMMIT_LIMPIO_PERMITIR_FORCE") != "1":
                errores.append(f"Esto reescribe el historial de «{rama}» (no es un avance simple). Solo con orden expresa del usuario.")
            nuevos = commits_en(repo, f"{sha_remoto}..{sha_local}")
        else:  # rama nueva: solo lo que el remoto aún no tiene
            nuevos = [c for c in git(repo, "rev-list", "--reverse", sha_local, "--not", f"--remotes={remoto}").split() if c]
        for sha in nuevos:
            e, av = revisar_commit_publicado(repo, sha, pats, pol)
            errores += e
            avisos += av
    cmd = pol.get("comando_pruebas")
    if cmd and not errores:
        r = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True)
        if r.returncode != 0:
            errores.append(f"Las pruebas del proyecto fallaron («{cmd}»). Arréglalas antes de publicar.")
    return informe("Push: lo que se va a publicar", errores, avisos, a.json)


def modo_historial(a) -> int:
    repo = raiz_repo(a.repo)
    pol, pats = cargar_politica(repo), cargar_terminos(repo)
    errores, avisos = [], []
    for sha in commits_en(repo, a.rango or "--all"):
        e, av = revisar_commit_publicado(repo, sha, pats, pol)
        errores += e
        avisos += av
    e, av = revisar_arbol(repo, pats)
    errores += e
    avisos += av
    return informe("Historial completo", errores, avisos, a.json)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verifica commits y pushes antes de publicar.")
    ap.add_argument("--repo", default=".", help="ruta del repositorio (por defecto, el actual)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo-aviso", action="store_true", help="nunca devuelve error: solo informa")
    sub = ap.add_subparsers(dest="modo", required=True)
    s = sub.add_parser("mensaje"); s.add_argument("archivo"); s.set_defaults(f=modo_mensaje)
    s = sub.add_parser("commit"); s.set_defaults(f=modo_commit)
    s = sub.add_parser("push"); s.add_argument("remoto", nargs="?"); s.add_argument("url", nargs="?"); s.set_defaults(f=modo_push)
    s = sub.add_parser("historial"); s.add_argument("rango", nargs="?"); s.set_defaults(f=modo_historial)
    a = ap.parse_args(argv)
    codigo = a.f(a)
    return 0 if a.solo_aviso else codigo


if __name__ == "__main__":
    sys.exit(main())
