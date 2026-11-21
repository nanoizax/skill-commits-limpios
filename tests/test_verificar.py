import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SCRIPT = os.path.join(RAIZ, "scripts", "verificar_publicacion.py")
INSTALAR = os.path.join(RAIZ, "scripts", "instalar_hooks.sh")
CEROS = "0" * 40


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.env = {**os.environ, "HOME": self.home, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_TERMINAL_PROMPT": "0"}
        self.env.pop("COMMIT_LIMPIO_TERMINOS", None)
        self.env.pop("COMMIT_LIMPIO_PERMITIR_FORCE", None)
        self.repo = self.nuevo_repo()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- ayudas
    def git(self, *a, repo=None, ok=True, entrada=None):
        r = subprocess.run(["git", "-C", repo or self.repo, *a], capture_output=True, text=True, env=self.env, input=entrada)
        if ok and r.returncode != 0:
            raise AssertionError(f"git {a} falló: {r.stderr}")
        return r

    def nuevo_repo(self, nombre="Ana Pérez", correo="ana@ejemplo.com", local=True):
        d = tempfile.mkdtemp(dir=self.tmp)
        subprocess.run(["git", "-C", d, "init", "-q", "-b", "main"], check=True, env=self.env)
        if local:
            subprocess.run(["git", "-C", d, "config", "--local", "user.name", nombre], check=True, env=self.env)
            subprocess.run(["git", "-C", d, "config", "--local", "user.email", correo], check=True, env=self.env)
        return d

    def escribir(self, ruta, texto, repo=None):
        p = os.path.join(repo or self.repo, ruta)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(texto)

    def preparar(self, ruta, texto, repo=None):
        self.escribir(ruta, texto, repo)
        self.git("add", ruta, repo=repo)

    def commit(self, mensaje, repo=None):
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", mensaje, repo=repo)
        return self.git("rev-parse", "HEAD", repo=repo).stdout.strip()

    def politica(self, **kw):
        os.makedirs(os.path.join(self.repo, ".commit-limpio"), exist_ok=True)
        json.dump(kw, open(os.path.join(self.repo, ".commit-limpio", "politica.json"), "w"))

    def terminos(self, *lineas):
        os.makedirs(os.path.join(self.repo, ".commit-limpio"), exist_ok=True)
        open(os.path.join(self.repo, ".commit-limpio", "terminos.txt"), "w", encoding="utf-8").write("\n".join(lineas))

    def correr(self, *args, entrada=None, repo=None, extra_env=None):
        env = {**self.env, **(extra_env or {})}
        return subprocess.run([sys.executable, SCRIPT, "--repo", repo or self.repo, *args], capture_output=True,
                              text=True, env=env, input=entrada)

    def mensaje(self, texto, **kw):
        f = os.path.join(self.tmp, "MSG")
        open(f, "w", encoding="utf-8").write(texto)
        return self.correr("mensaje", f, **kw)


class Mensajes(Base):
    def test_mensaje_bueno(self):
        r = self.mensaje("Agrega el filtro por fecha al listado de pedidos\n\nPermite acotar por rango de fechas.\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Todo en orden", r.stderr)

    def test_trailer_de_coautoria_bloquea(self):
        r = self.mensaje("Corrige el cálculo del total\n\nCo-Authored-By: Alguien <a@b.c>\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("coautoría", r.stderr)

    def test_coautoria_y_herramienta_se_avisan_juntas(self):
        self.terminos("herramienta-x")
        r = self.mensaje("update\n\nHecho con herramienta-x\nCo-Authored-By: Alguien <a@b.c>\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("coautoría", r.stderr)
        self.assertIn("herramienta-x", r.stderr)

    def test_patron_general_de_autoria_automatica(self):
        r = self.mensaje("Corrige el total\n\nGenerated with una-herramienta\n")
        self.assertEqual(r.returncode, 1)
        r = self.mensaje("Corrige el total, hecho por una IA\n")
        self.assertEqual(r.returncode, 1)

    def test_termino_propio_bloquea(self):
        self.terminos("herramienta-x")
        r = self.mensaje("Corrige el total con herramienta-x\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("herramienta-x", r.stderr)
        self.assertEqual(self.mensaje("Corrige el total\n").returncode, 0)

    def test_termino_propio_como_regex(self):
        self.terminos("re:\\bmi-asistente(-\\w+)?\\b")
        self.assertEqual(self.mensaje("Mejora el login con mi-asistente-2\n").returncode, 1)

    def test_titulo_generico_solo_avisa(self):
        r = self.mensaje("update\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("genérico", r.stderr)

    def test_titulo_largo(self):
        self.assertEqual(self.mensaje("a" * 80 + " bien\n").returncode, 0)  # avisa
        self.assertEqual(self.mensaje("palabra " * 20 + "\n").returncode, 1)  # >100

    def test_prefijo_de_la_politica(self):
        self.politica(prefijo="^TASK #\\d+: ")
        self.assertEqual(self.mensaje("Agrega algo útil\n").returncode, 1)
        self.assertEqual(self.mensaje("TASK #12: Agrega algo útil\n").returncode, 0)

    def test_comentarios_de_git_se_ignoran(self):
        r = self.mensaje("Agrega el filtro por fecha\n# Co-Authored-By: esto es un comentario de git\n")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_mensaje_vacio(self):
        self.assertEqual(self.mensaje("# solo comentarios\n").returncode, 1)

    def test_commit_grande_sin_descripcion_avisa(self):
        self.preparar("datos.txt", "\n".join(f"linea {i}" for i in range(60)))
        r = self.mensaje("Agrega los datos iniciales\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("no tiene descripción", r.stderr)

    def test_solo_aviso_nunca_falla(self):
        f = os.path.join(self.tmp, "M")
        open(f, "w").write("Co-Authored-By: x <x@y.z>\n")
        r = self.correr("--solo-aviso", "mensaje", f)
        self.assertEqual(r.returncode, 0)


class Commit(Base):
    def test_commit_limpio(self):
        self.preparar("app.py", "print('hola')\n")
        r = self.correr("commit")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_nada_preparado(self):
        self.assertEqual(self.correr("commit").returncode, 1)

    def test_archivo_env_bloquea_pero_el_ejemplo_no(self):
        self.preparar(".env", "A=1\n")
        r = self.correr("commit")
        self.assertEqual(r.returncode, 1)
        self.assertIn(".env", r.stderr)
        self.git("reset", "-q")
        self.preparar(".env.example", "A=\n")
        self.assertEqual(self.correr("commit").returncode, 0)

    def test_secretos(self):
        clave = "AKIA" + "ABCDEFGHIJKLMNOP"
        self.preparar("config.py", f"KEY = '{clave}'\n")
        r = self.correr("commit")
        self.assertEqual(r.returncode, 1)
        self.assertIn("AWS", r.stderr)
        self.git("reset", "-q")
        self.preparar("c2.py", "token = '" + "x" * 20 + "'\n")
        self.assertEqual(self.correr("commit").returncode, 1)

    def test_llave_privada(self):
        self.preparar("a.txt", "-----BEGIN " + "RSA PRIVATE KEY-----\nabc\n")
        self.assertEqual(self.correr("commit").returncode, 1)

    def test_marca_de_conflicto(self):
        self.preparar("a.txt", "<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> otra\n")
        self.assertEqual(self.correr("commit").returncode, 1)

    def test_todo_solo_avisa(self):
        self.preparar("a.py", "# TODO: mejorar\n")
        r = self.correr("commit")
        self.assertEqual(r.returncode, 0)
        self.assertIn("TODO", r.stderr)

    def test_texto_con_termino_propio_avisa(self):
        self.terminos("herramienta-x")
        self.preparar("README.md", "Hecho con herramienta-x\n")
        r = self.correr("commit")
        self.assertEqual(r.returncode, 0)
        self.assertIn("herramienta-x", r.stderr)

    def test_identidad_global_avisa(self):
        d = self.nuevo_repo(local=False)
        self.env["GIT_CONFIG_GLOBAL"] = os.path.join(self.tmp, "gitconfig")
        open(self.env["GIT_CONFIG_GLOBAL"], "w").write("[user]\n\tname = Ana Pérez\n\temail = ana@ejemplo.com\n")
        self.preparar("a.py", "x=1\n", repo=d)
        r = self.correr("commit", repo=d)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("global", r.stderr)

    def test_sin_identidad(self):
        d = self.nuevo_repo(local=False)
        self.preparar("a.py", "x=1\n", repo=d)
        self.assertEqual(self.correr("commit", repo=d).returncode, 1)

    def test_nombre_corto_avisa(self):
        d = self.nuevo_repo(nombre="Ana")
        self.preparar("a.py", "x=1\n", repo=d)
        r = self.correr("commit", repo=d)
        self.assertEqual(r.returncode, 0)
        self.assertIn("nombre y apellido", r.stderr)

    def test_autor_que_parece_herramienta(self):
        self.terminos("herramienta-x")
        d = self.nuevo_repo(nombre="herramienta-x bot", correo="bot@ejemplo.com")
        os.makedirs(os.path.join(d, ".commit-limpio"))
        open(os.path.join(d, ".commit-limpio", "terminos.txt"), "w").write("herramienta-x\n")
        self.preparar("a.py", "x=1\n", repo=d)
        self.assertEqual(self.correr("commit", repo=d).returncode, 1)

    def test_autor_exigido_por_la_politica(self):
        self.politica(autor_nombre="Otra Persona")
        self.preparar("a.py", "x=1\n")
        r = self.correr("commit")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Otra Persona", r.stderr)


class Push(Base):
    def linea(self, sha, remoto=CEROS, rama="main"):
        return f"refs/heads/{rama} {sha} refs/heads/{rama} {remoto}\n"

    def test_push_limpio(self):
        self.preparar("a.py", "x=1\n")
        sha = self.commit("Agrega el archivo principal")
        r = self.correr("push", "origin", entrada=self.linea(sha))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_push_con_commit_con_coautoria(self):
        self.preparar("a.py", "x=1\n")
        sha = self.commit("Agrega el archivo\n\nCo-Authored-By: Alguien <a@b.c>")
        r = self.correr("push", "origin", entrada=self.linea(sha))
        self.assertEqual(r.returncode, 1)
        self.assertIn("coautoría", r.stderr)

    def test_push_rama_protegida(self):
        self.politica(ramas_protegidas=["main"])
        self.preparar("a.py", "x=1\n")
        sha = self.commit("Agrega el archivo principal")
        self.assertEqual(self.correr("push", "origin", entrada=self.linea(sha)).returncode, 1)
        self.git("checkout", "-q", "-b", "dev/ana")
        self.assertEqual(self.correr("push", "origin", entrada=self.linea(sha, rama="dev/ana")).returncode, 0)

    def test_push_que_reescribe_historial(self):
        self.preparar("a.py", "x=1\n")
        base = self.commit("Agrega el archivo principal")
        self.git("checkout", "-q", "-b", "otra")
        self.preparar("b.py", "y=1\n")
        otro = self.commit("Agrega otro archivo distinto")
        self.git("checkout", "-q", "main")
        self.preparar("c.py", "z=1\n")
        nuevo = self.commit("Agrega un tercer archivo")
        entrada = self.linea(nuevo, remoto=otro)
        r = self.correr("push", "origin", entrada=entrada)
        self.assertEqual(r.returncode, 1)
        self.assertIn("reescribe", r.stderr)
        r = self.correr("push", "origin", entrada=entrada, extra_env={"COMMIT_LIMPIO_PERMITIR_FORCE": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_push_solo_revisa_lo_nuevo(self):
        self.preparar("a.py", "x=1\n")
        viejo = self.commit("Agrega el archivo\n\nCo-Authored-By: Alguien <a@b.c>")
        self.preparar("b.py", "y=1\n")
        nuevo = self.commit("Agrega otro archivo de prueba")
        r = self.correr("push", "origin", entrada=self.linea(nuevo, remoto=viejo))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_pruebas_del_proyecto_bloquean(self):
        self.politica(comando_pruebas="exit 3")
        self.preparar("a.py", "x=1\n")
        sha = self.commit("Agrega el archivo principal")
        r = self.correr("push", "origin", entrada=self.linea(sha))
        self.assertEqual(r.returncode, 1)
        self.assertIn("pruebas", r.stderr)
        self.politica(comando_pruebas="exit 0")
        self.assertEqual(self.correr("push", "origin", entrada=self.linea(sha)).returncode, 0)

    def test_borrar_una_rama_no_se_revisa(self):
        self.assertEqual(self.correr("push", "origin", entrada=self.linea(CEROS, remoto="a" * 40)).returncode, 0)


class Historial(Base):
    def test_historial_limpio(self):
        self.preparar("a.py", "x=1\n")
        self.commit("Agrega el archivo principal")
        self.assertEqual(self.correr("historial").returncode, 0)

    def test_historial_con_commit_malo(self):
        self.preparar("a.py", "x=1\n")
        self.commit("Agrega el archivo\n\nCo-Authored-By: Alguien <a@b.c>")
        r = self.correr("historial")
        self.assertEqual(r.returncode, 1)

    def test_historial_avisa_de_env_versionado(self):
        self.preparar(".env", "A=1\n")
        self.commit("Agrega la configuración inicial")
        r = self.correr("historial")
        self.assertIn(".env", r.stderr)


class GanchosReales(Base):
    """Integración: con los ganchos instalados, Git de verdad bloquea o deja pasar."""

    def instalar(self):
        r = subprocess.run(["sh", INSTALAR, self.repo], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_commit_malo_bloqueado_y_bueno_permitido(self):
        self.instalar()
        self.preparar("a.py", "x=1\n")
        malo = self.git("commit", "-q", "-m", "Agrega el archivo\n\nCo-Authored-By: Alguien <a@b.c>", ok=False)
        self.assertNotEqual(malo.returncode, 0)
        self.assertEqual(self.git("rev-list", "--count", "--all", ok=False).stdout.strip() or "0", "0")
        bueno = self.git("commit", "-q", "-m", "Agrega el archivo principal de la aplicación", ok=False)
        self.assertEqual(bueno.returncode, 0, bueno.stderr)
        self.assertEqual(self.git("rev-list", "--count", "HEAD").stdout.strip(), "1")

    def test_secreto_bloqueado_por_pre_commit(self):
        self.instalar()
        self.preparar("k.py", "KEY = '" + "AKIA" + "ABCDEFGHIJKLMNOP" + "'\n")
        r = self.git("commit", "-q", "-m", "Agrega la configuración", ok=False)
        self.assertNotEqual(r.returncode, 0)

    def test_desinstalar(self):
        self.instalar()
        subprocess.run(["sh", INSTALAR, "--desinstalar", self.repo], check=True, capture_output=True, env=self.env)
        self.preparar("a.py", "x=1\n")
        r = self.git("commit", "-q", "-m", "update", ok=False)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
