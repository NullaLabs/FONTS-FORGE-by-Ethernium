"""
Ethernium Sym — GitHub Publish Helper
─────────────────────────────────────
Guides the user step-by-step to initialize Git, make the first commit,
and push their Ethernium project to GitHub.
"""
import sys
import subprocess
from pathlib import Path

def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, encoding="utf-8")
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def main():
    root = Path(__file__).resolve().parent.parent
    
    print("======================================================================")
    print("           ETHERNIUM SYM — GITHUB PUBLISH HELPER")
    print("======================================================================")
    print("Este script te guiará para subir tu tipografía y herramientas a GitHub.")
    print("Asegúrate de haber creado un repositorio vacío en: https://github.com/new\n")

    # 1. Check if git is initialized
    git_dir = root / ".git"
    if not git_dir.is_dir():
        print("[*] Inicializando repositorio Git local...")
        code, out, err = run_cmd("git init", root)
        if code != 0:
            print(f"[!] Error al inicializar Git: {err}")
            sys.exit(1)
        print("  ✓ Repositorio Git inicializado correctamente.")
    else:
        print("[✓] Repositorio Git local ya inicializado.")

    # 2. Check current branch name or force main
    run_cmd("git checkout -b main", root)
    run_cmd("git branch -M main", root)
    
    # 3. Git status overview
    code, out, err = run_cmd("git status --short", root)
    if not out:
        print("\n[✓] No hay cambios sin confirmar en el repositorio.")
    else:
        print(f"\n[*] Detectados archivos listos para añadir (resumen):\n{out[:500]}")
        if len(out) > 500:
            print("  ...y más archivos.")

        confirm = input("\n¿Quieres añadir todos estos archivos y hacer el primer commit? (s/n): ").strip().lower()
        if confirm == 's' or confirm == 'y':
            print("[*] Añadiendo archivos a Git...")
            run_cmd("git add .", root)
            print("[*] Creando commit inicial...")
            commit_msg = "feat: release Ethernium Sym v3.0 - cyber-runic display typeface with interactive preview & ASCII art generators"
            code, out, err = run_cmd(f'git commit -m "{commit_msg}"', root)
            if code != 0:
                print(f"[!] Error al hacer el commit: {err}")
                print("Nota: Si es la primera vez que usas Git, debes configurar tu email y nombre:")
                print("  git config --global user.email \"tu@email.com\"")
                print("  git config --global user.name \"Tu Nombre\"")
            else:
                print("  ✓ Commit inicial creado con éxito.")
        else:
            print("[*] Omitiendo commit por ahora.")

    # 4. Git remote setup
    code, out, err = run_cmd("git remote -v", root)
    current_remote = ""
    if out:
        lines = out.split("\n")
        for line in lines:
            if "origin" in line and "(push)" in line:
                current_remote = line.split()[1]
                break

    if current_remote:
        print(f"\n[✓] Repositorio remoto origin actual: {current_remote}")
    else:
        print("\n[*] No hay ningún repositorio remoto configurado.")
        repo_url = input("Pega la URL de tu repositorio de GitHub (ej: https://github.com/usuario/ethernium-sym.git) o presiona Enter para omitir: ").strip()
        if repo_url:
            code, out, err = run_cmd(f"git remote add origin {repo_url}", root)
            if code != 0:
                # Try setting url instead
                run_cmd(f"git remote set-url origin {repo_url}", root)
            print(f"  ✓ Repositorio remoto origin configurado como: {repo_url}")
            current_remote = repo_url

    # 5. Push instructions
    print("\n======================================================================")
    print("                  INSTRUCCIONES DE PUBLICACIÓN")
    print("======================================================================")
    if current_remote:
        print("Para subir los archivos a GitHub, simplemente ejecuta en tu terminal:")
        print("  git push -u origin main\n")
        
        push_now = input("¿Quieres intentar subir (push) a GitHub ahora mismo? (s/n): ").strip().lower()
        if push_now == 's' or push_now == 'y':
            print("[*] Subiendo a GitHub (ejecutando 'git push -u origin main')...")
            # We run it showing the output so authentication prompt is visible if needed
            subprocess.run("git push -u origin main", shell=True, cwd=root)
    else:
        print("Cuando crees tu repositorio en GitHub, ejecuta estos comandos en esta carpeta:")
        print("  git remote add origin URL_DE_TU_REPOSITORIO")
        print("  git branch -M main")
        print("  git push -u origin main")

    print("\n======================================================================")
    print("¡Listo! Tu código y release packages están preparados para ser compartidos.")
    print("Abre: C:\\Users\\esenc\\OneDrive\\Documentos\\Escritorio\\ETHERNIUM SYM")
    print("======================================================================")

if __name__ == "__main__":
    main()
