"""Capturas de pantalla de la app con Chrome/Edge headless vía DevTools Protocol (sin paquetes extra).

Streamlit se renderiza por WebSocket, así que una captura directa sale vacía: este script espera a que
aparezca un texto en la página antes de capturar, y puede escribir en el ``chat_input``.

Uso (con la app corriendo):
    .venv\\Scripts\\python scripts\\capturas.py --url http://localhost:8501/consultar?evento=ev-res-lemans \\
        --esperar "Consultar opiniones" --salida evidencias/capturas/consulta.png
    .venv\\Scripts\\python scripts\\capturas.py --url http://localhost:8501/emitir --escribir "Gran carrera" ...
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "microsoft-edge",
]


def _navegador() -> str:
    for n in NAVEGADORES:
        if Path(n).exists() or shutil.which(n):
            return n
    raise SystemExit("No se encontró Chrome ni Edge.")


class Cdp:
    def __init__(self, ws) -> None:
        self.ws = ws
        self.n = 0

    async def __call__(self, metodo: str, **params):
        self.n += 1
        mid = self.n
        await self.ws.send(json.dumps({"id": mid, "method": metodo, "params": params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})

    async def evaluar(self, js: str):
        r = await self("Runtime.evaluate", expression=js, returnByValue=True, awaitPromise=True)
        return r.get("result", {}).get("value")

    async def esperar_texto(self, texto: str, limite: float = 60) -> bool:
        fin = time.monotonic() + limite
        while time.monotonic() < fin:
            if await self.evaluar(f"document.body && document.body.innerText.includes({json.dumps(texto)})"):
                return True
            await asyncio.sleep(0.5)
        return False


async def _clic(cdp: Cdp, selector_js: str) -> None:
    rect = await cdp.evaluar(f"(() => {{const r = ({selector_js}).getBoundingClientRect();"
                             " return [r.x + r.width / 2, r.y + r.height / 2];}})()")
    for tipo in ("mousePressed", "mouseReleased"):
        await cdp("Input.dispatchMouseEvent", type=tipo, x=rect[0], y=rect[1], button="left", clickCount=1)
    await asyncio.sleep(0.4)


async def capturar(url: str, salida: Path, esperar: list[str], escribir: list[str], ancho: int, alto: int,
                   pausa: float, puerto: int = 9333, login: str | None = None, ir: list[str] | None = None) -> None:
    ir = ir or []
    perfil = tempfile.mkdtemp(prefix="paddock_cdp_")
    proc = subprocess.Popen([_navegador(), "--headless=new", f"--remote-debugging-port={puerto}",
                             f"--user-data-dir={perfil}", "--disable-gpu", "--hide-scrollbars",
                             f"--window-size={ancho},{alto}", "--no-first-run", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/json") as r:  # noqa: S310
                    paginas = [p for p in json.load(r) if p.get("type") == "page"]
                if paginas:
                    ws_url = paginas[0]["webSocketDebuggerUrl"]
                    break
            except OSError:
                pass
            time.sleep(0.2)
        if not ws_url:
            raise SystemExit("No se pudo conectar con el navegador.")
        async with websockets.connect(ws_url, max_size=50_000_000) as ws:
            cdp = Cdp(ws)
            await cdp("Page.enable")
            await cdp("Page.navigate", url=url)
            if login:
                email, clave = login.split(":", 1)
                for _ in range(60):
                    if await cdp.evaluar("!!document.querySelector('input[aria-label=\"Correo\"]')"):
                        break
                    await asyncio.sleep(0.5)
                for etiqueta, valor in (("Correo", email), ("Contraseña", clave)):
                    await cdp.evaluar(f"document.querySelector('input[aria-label=\"{etiqueta}\"]').focus()")
                    await cdp("Input.insertText", text=valor)
                await cdp.evaluar("[...document.querySelectorAll('[data-testid=\"stFormSubmitButton\"] button')][0].click()")
                await cdp.esperar_texto("Cerrar sesión")
            for destino in ir:
                for _ in range(20):  # espera a que el menú tenga el enlace
                    if await cdp.evaluar(f"!!document.querySelector('a[href$=\"/{destino}\"]')"):
                        break
                    await asyncio.sleep(0.5)
                await cdp.evaluar(f"document.querySelector('a[href$=\"/{destino}\"]').click()")
                await asyncio.sleep(3)
            for t in esperar:
                if not await cdp.esperar_texto(t):
                    print(f"Aviso: no apareció «{t}»")
            for texto in escribir:
                for _ in range(40):  # espera a que exista el cuadro de chat
                    if await cdp.evaluar("!!document.querySelector('textarea')"):
                        break
                    await asyncio.sleep(0.5)
                rect = await cdp.evaluar(
                    "(() => {const r = document.querySelector('textarea')"
                    ".getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2];})()")
                for tipo in ("mousePressed", "mouseReleased"):
                    await cdp("Input.dispatchMouseEvent", type=tipo, x=rect[0], y=rect[1], button="left", clickCount=1)
                await asyncio.sleep(0.3)
                await cdp("Input.insertText", text=texto)
                await asyncio.sleep(0.3)
                for tipo in ("keyDown", "keyUp"):
                    await cdp("Input.dispatchKeyEvent", type=tipo, key="Enter", code="Enter",
                              windowsVirtualKeyCode=13, nativeVirtualKeyCode=13)
                await asyncio.sleep(1)
                # Espera a que termine el análisis (desaparece el spinner)
                fin = time.monotonic() + 240
                while time.monotonic() < fin and await cdp.evaluar(
                        "document.body.innerText.includes('Analizando con')"):
                    await asyncio.sleep(1)
                await asyncio.sleep(1.5)
            await asyncio.sleep(pausa)
            alto_doc = await cdp.evaluar("Math.max(document.body.scrollHeight, "
                                         "document.querySelector('[data-testid=\"stMain\"]')?.scrollHeight || 0)")
            if alto_doc and alto_doc > alto:
                await cdp("Emulation.setDeviceMetricsOverride", width=ancho, height=min(int(alto_doc), 4000),
                          deviceScaleFactor=1, mobile=False)
                await asyncio.sleep(1)
            img = await cdp("Page.captureScreenshot", format="png", captureBeyondViewport=True)
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(base64.b64decode(img["data"]))
            print(f"Captura: {salida}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(perfil, ignore_errors=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True)
    p.add_argument("--salida", required=True, type=Path)
    p.add_argument("--esperar", action="append", default=[])
    p.add_argument("--escribir", action="append", default=[])
    p.add_argument("--ancho", type=int, default=1440)
    p.add_argument("--alto", type=int, default=1000)
    p.add_argument("--pausa", type=float, default=2.0)
    p.add_argument("--login", default=None, help="correo:contraseña (en la página /cuenta)")
    p.add_argument("--ir", action="append", default=[], help="url_path de la página a la que navegar tras el login")
    a = p.parse_args()
    asyncio.run(capturar(a.url, a.salida, a.esperar or ["Paddock Global"], a.escribir, a.ancho, a.alto, a.pausa,
                         login=a.login, ir=a.ir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
