import socket
from dataclasses import dataclass
from threading import Event

STORE: dict[str, str] = {}


@dataclass(frozen=True)
class Request:
    key: str
    value: str | None = None


def handle_request(
    request: Request,
    store: dict[str, str] = STORE,
) -> str:
    if request.value is None:
        value = store[request.key]
        return f"HTTP/1.1 200 OK\r\nContent-Length: {len(value)}\r\n\r\n{value}"
    else:
        store[request.key] = request.value
        return "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"


def parse(raw: bytes) -> Request:
    request_line = raw.split(b"\r\n")[0]
    _, uri, _ = request_line.split()
    path, _, query = uri.partition(b"?")
    key, _, value = query.partition(b"=")
    if path == b"/set":
        return Request(key=key.decode("utf-8"), value=value.decode("utf-8"))
    else:
        return Request(key=value.decode("utf-8"))


class Server:
    def __init__(self):
        self._sock = socket.create_server(("localhost", 4000))
        self._sock.settimeout(0.1)
        self._event = Event()

    def start(self):
        while not self._event.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                pass
            else:
                raw = b""
                while data := conn.recv(128):
                    raw += data
                    # I assume all requests are body-free, so end of message is end of headers.
                    if raw.endswith(b"\r\n\r\n"):
                        break

                request = parse(raw)
                response = handle_request(request)
                conn.sendall(response.encode("utf-8"))

        self._sock.close()

    def stop(self):
        self._event.set()


def main():
    server = Server()
    try:
        server.start()
    finally:
        server.stop()


if __name__ == "__main__":
    main()
