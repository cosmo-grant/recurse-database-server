import socket
from dataclasses import dataclass
from threading import Event


class Store:
    def __init__(self, data: dict[str, str] | None = None):
        self._data = {**data} if data is not None else {}

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Store):
            return False

        return self._data == other._data

    def get(self, key: str) -> str:
        return self._data[key]

    def set(self, key: str, value: str) -> None:
        self._data[key] = value


@dataclass(frozen=True)
class SetRequest:
    key: str
    value: str


@dataclass(frozen=True)
class GetRequest:
    key: str


@dataclass(frozen=True)
class Response:
    status_code: int
    status_message: str
    headers: dict[str, str]
    body: bytes

    def serialize(self) -> bytes:
        self.headers["Content-Length"] = str(len(self.body))  # silently override if provided
        status_line = f"HTTP/1.1 {self.status_code} {self.status_message}\r\n"
        headers_lines = "".join(f"{key}: {value}\r\n" for key, value in self.headers.items())
        return (status_line + headers_lines + "\r\n").encode("utf-8") + self.body


def handle_request(
    request: SetRequest | GetRequest,
    store: Store,
) -> Response:
    assert isinstance(request, (SetRequest, GetRequest))
    if isinstance(request, GetRequest):
        value = store.get(request.key)
        return Response(200, "OK", {}, value.encode("utf-8"))
    else:
        store.set(request.key, request.value)
        return Response(200, "OK", {}, b"")


def parse(raw: bytes) -> SetRequest | GetRequest:
    request_line = raw.split(b"\r\n")[0]
    _, uri, _ = request_line.split()
    path, _, query = uri.partition(b"?")
    key, _, value = query.partition(b"=")
    if path == b"/set":
        return SetRequest(key=key.decode("utf-8"), value=value.decode("utf-8"))
    else:
        return GetRequest(key=value.decode("utf-8"))


class Server:
    def __init__(self, host: str, port: int, store: Store | None = None):
        self._sock = socket.create_server((host, port))
        self._sock.settimeout(0.1)
        self._event = Event()
        self._store = store or Store()

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
                response = handle_request(request, self._store)
                conn.sendall(response.serialize())

        self._sock.close()

    def stop(self):
        self._event.set()

    def get_port(self) -> int:
        """
        Return the port that the server's underlying socket is listening on.

        This is useful if you initialized with port=0, e.g. when testing, to find out which port the kernel picked for you.
        """
        return self._sock.getsockname()[1]


def main():
    server = Server("localhost", 4000)
    try:
        server.start()
    finally:
        server.stop()


if __name__ == "__main__":
    main()
