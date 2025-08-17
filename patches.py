import os, re, sys, subprocess, time, json, shutil
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
CFG = yaml.safe_load(open(HERE / "patches.yaml", "r", encoding="utf-8"))
FIXES = yaml.safe_load(open(HERE / "known_fixes.yaml", "r", encoding="utf-8"))
LOG_FILE = Path(CFG["behavior"]["log_file"])
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    msg = msg.strip()
    print(msg, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")

def find_project_root(start: Path) -> Path:
    cur = start
    markers = set(CFG["workspace"]["root_markers"])
    for _ in range(25):
        if any((cur / m).exists() for m in markers):
            return cur
        if cur.parent == cur: break
        cur = cur.parent
    return start

def run(cmd, shell=True, env=None, cwd=None):
    proc = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=cwd, text=True)
    out = []
    for line in proc.stdout:
        print(line, end="")
        out.append(line)
    code = proc.wait()
    return code, "".join(out)

def ensure_python(version: str, venv_path: Path):
    if os.name == "nt":
        py_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
        if not py_exe.exists():
            log(f"Patches: creating Windows venv with Python {version}")
            code, out = run(f'py -{version} -m venv "{venv_path}"')
            if code != 0:
                log(out); raise RuntimeError("venv create failed")
        return str(py_exe), str(pip_exe)
    else:
        py = shutil.which(f"python{version}") or shutil.which("python3") or shutil.which("python")
        py_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
        if not py_exe.exists():
            log(f"Patches: creating Linux venv with {py}")
            code, out = run(f'"{py}" -m venv "{venv_path}"')
            if code != 0:
                log(out); raise RuntimeError("venv create failed")
        return str(py_exe), str(pip_exe)

def pip_install(pip, packages, index_url=None):
    pkgs = " ".join(packages)
    cmd = f'"{pip}" install -U {pkgs}'
    if index_url: cmd += f' --index-url {index_url}'
    log(f"Patches: pip install → {pkgs}")
    return run(cmd)

def apply_actions(actions, project_root, py, pip):
    for act in actions:
        t = act["type"]
        if t == "pip_install":
            code, out = pip_install(pip, act["args"], act.get("index_url"))
            if code != 0: return False, out
        elif t == "ensure_python_version" or t == "create_venv_with":
            py, pip = ensure_python(act["args"][0], project_root / CFG["python"]["venv"])
        elif t == "cd_to_project_root":
            os.chdir(project_root)
            log(f"Patches: cd → {project_root}")
        elif t == "bash_run":
            script = act["script"].replace('"','\\"').replace("\n"," && ")
            if os.name == "nt":
                run(f'wsl.exe bash -lc "{script}"')
            else:
                run(script)
        elif t == "re_run":
            return "RETRY", None
    return True, None

def match_rule(text):
    for rule in FIXES.get("rules", []):
        if re.search(rule["match"], text or "", re.MULTILINE):
            return rule
    return None

def main(target_shell=None, target_cmd=None):
    start = Path.cwd()
    project_root = find_project_root(start)
    os.chdir(project_root)
    log(f"Patches online. Root → {project_root}")

    desired = CFG["python"]["desired"]
    venv = project_root / CFG["python"]["venv"]
    py, pip = ensure_python(desired, venv)
    run(f'"{pip}" install -U pip wheel')

    shell = target_shell or ("powershell" if os.name == "nt" else "bash")
    if target_cmd:
        cmd = target_cmd
    else:
        cmd = CFG["targets"]["powershell"] if shell == "powershell" else CFG["targets"]["bash"]

    retries = CFG["behavior"]["max_retries"]
    for i in range(1, retries+1):
        log(f"Try {i}/{retries}: {cmd}")
        env = os.environ.copy()
        if os.name == "nt":
            env["PATH"] = str((venv / "Scripts")) + os.pathsep + env["PATH"]
            env["PYTHONPATH"] = str(project_root)
        else:
            env["PATH"] = str((venv / "bin")) + os.pathsep + env["PATH"]
        code, out = run(cmd, env=env, cwd=project_root)
        if code == 0:
            log("Success ✅")
            return 0

        log("Failed. Analyzing…")
        rule = match_rule(out)
        if not rule:
            log("No quick-fix rule matched. Stopping for manual review.")
            return code

        log(f"Applying rule: {rule['match']}")
        res, msg = apply_actions(rule["actions"], project_root, py, pip)
        if res == "RETRY":
            continue
        if not res:
            log(f"Fix failed:\n{msg}")
            return 1
        log("Fix applied. Retrying…")
        time.sleep(1)

    log("Exhausted retries. Consider enabling escalation in patches.yaml.")
    return 1

if __name__ == "__main__":
    # Optional CLI: python patches.py [powershell|bash] "custom command"
    sh = sys.argv[1] if len(sys.argv) > 1 else None
    cmd = sys.argv[2] if len(sys.argv) > 2 else None
    sys.exit(main(sh, cmd))
