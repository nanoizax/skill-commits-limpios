#!/bin/sh
# Instala (o quita) los ganchos de esta skill en UN repositorio. No toca la configuración global.
#   sh scripts/instalar_hooks.sh [ruta-del-repositorio]
#   sh scripts/instalar_hooks.sh --desinstalar [ruta-del-repositorio]
# Ojo: core.hooksPath sustituye a .git/hooks en ese repositorio; si ya usabas ganchos propios, combínalos.
set -e
AQUI="$(cd "$(dirname "$0")" && pwd)"
HOOKS="$(cd "$AQUI/../hooks" && pwd)"

if [ "$1" = "--desinstalar" ]; then
  REPO="${2:-.}"
  git -C "$REPO" config --local --unset core.hooksPath || true
  echo "Ganchos quitados de $(git -C "$REPO" rev-parse --show-toplevel)"
  exit 0
fi

REPO="${1:-.}"
RAIZ="$(git -C "$REPO" rev-parse --show-toplevel)"
chmod +x "$HOOKS"/* 2>/dev/null || true
git -C "$REPO" config --local core.hooksPath "$HOOKS"
echo "Ganchos instalados en $RAIZ"
echo "  usan: $HOOKS"
echo "  política y términos propios: $RAIZ/.commit-limpio/  (ver politica.ejemplo.json y terminos.ejemplo.txt)"
