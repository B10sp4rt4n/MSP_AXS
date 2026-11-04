"""Run with python -m labs.contingency.server. Synthetic localhost laboratory only."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import parse_qs, urlsplit

from .journal import Denied, Journal, SCOPES, SimulatedReceiver


def make_server(directory, port=8766):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    journal = Journal(directory / "local.synthetic.sqlite")
    receiver = SimulatedReceiver(directory / "receiver.synthetic.sqlite")
    for scope in SCOPES.values():
        journal.prepare_fixture(scope)
        receiver.prepare_fixture(scope, journal.state(scope)["snapshot"]["visit"])
    session = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log token, pass or request body.

        def reply(self, code, payload, html=False):
            body = payload.encode() if html else json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; "
                             f"script-src 'nonce-{session}'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def same_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def authorized(self):
            origin = self.headers.get("Origin")
            return (self.same_host() and secrets.compare_digest(self.headers.get("X-Lab-Token", ""), session)
                    and (origin is None or origin == f"http://127.0.0.1:{self.server.server_port}"))

        def do_GET(self):
            route = urlsplit(self.path)
            if not self.same_host():
                return self.reply(403, {"error": "Host no autorizado"})
            if route.path == "/":
                html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
                return self.reply(200, html.replace("__LAB_TOKEN__", session), html=True)
            if route.path != "/api/state":
                return self.reply(404, {"error": "Ruta inexistente"})
            if not self.authorized():
                return self.reply(403, {"error": "Sesión local de laboratorio requerida"})
            try:
                scope = SCOPES[parse_qs(route.query).get("condo", [""])[0]]
                return self.reply(200, {**journal.state(scope), "receiver": receiver.state(scope)})
            except KeyError:
                return self.reply(400, {"error": "Solo existen los escenarios ficticios A y B"})

        def do_POST(self):
            if not self.authorized():
                return self.reply(403, {"error": "Sesión local de laboratorio requerida"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192 or self.headers.get("Content-Type") != "application/json":
                    return self.reply(400, {"error": "Se requiere JSON de hasta 8 KiB"})
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Objeto JSON requerido")
                scope = SCOPES[body["condo"]]
                if self.path == "/api/operation":
                    result = journal.record(scope, request_id=body["request_id"], visit=body["visit"],
                                            action=body["action"], credential=body.get("credential", ""))
                elif self.path == "/api/sync":
                    if type(body.get("lose_ack", False)) is not bool:
                        raise ValueError("lose_ack debe ser booleano")
                    result = {"delivered": journal.sync(scope, receiver, lose_ack=body.get("lose_ack", False))}
                elif self.path == "/api/cancel":
                    receiver.cancel_fixture(scope)
                    result = {"cancelled": True}
                else:
                    return self.reply(404, {"error": "Ruta inexistente"})
                return self.reply(200, result)
            except ConnectionError as exc:
                return self.reply(503, {"error": str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                return self.reply(400, {"error": str(exc) if isinstance(exc, Denied) else "Solicitud inválida"})
            except sqlite3.Error:
                return self.reply(503, {"error": "No se pudo confirmar almacenamiento; conserve la solicitud y reintente"})

    return HTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="tmp/axs-contingency-lab")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = make_server(args.data_dir, args.port)
    print(f"Laboratorio ficticio: http://127.0.0.1:{server.server_port} — Ctrl+C para detener", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
