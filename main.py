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

    def get(self, key: str) -> str | None:
        return self._data.get(key)

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
        status_line = f"HTTP/1.1 {self.status_code} {self.status_message}\r\n"
        headers_lines = "".join(f"{key}: {value}\r\n" for key, value in self.headers.items())
        return (status_line + headers_lines + "\r\n").encode("utf-8") + self.body


def make_response(
    status_code: int,
    status_message: str,
    headers: dict[str, str] | None = None,
    body: str | bytes = b"",
) -> Response:
    """
    Construct an HTTP/1.1 response from the given ingredients.

    The ingredients should have all the endpoint-specific details.
    This function manages the general HTTP details (e.g content-length header) and type conversions on top.
    """
    headers = headers or {}

    if isinstance(body, str):
        body = body.encode("utf-8")

    # For HTTP/1.1, "Content-Length" (or "Transfer-Encoding: chunked") is required.
    headers["Content-Length"] = str(len(body))

    return Response(status_code, status_message, headers, body)


def handle_request(
    request: SetRequest | GetRequest,
    store: Store,
) -> Response:
    assert isinstance(request, (SetRequest, GetRequest))
    if isinstance(request, GetRequest):
        value = store.get(request.key)
        response = make_response(404, "Not Found") if value is None else make_response(200, "OK", body=value)
        return response
    else:
        store.set(request.key, request.value)
        return make_response(201, "Created")


def parse(raw: bytes) -> SetRequest | GetRequest:
    # I expect either GET /get?key=somekey or POST /set?somekey=somevalue.
    # Behaviour is undefined for any other requests.
    decoded = raw.decode("utf-8")
    request_line = decoded.split("\r\n")[0]
    _, uri, _ = request_line.split()
    path, _, query = uri.partition("?")
    key, _, value = query.partition("=")  # TODO: cope with url encoding
    if path == "/set":
        return SetRequest(key=key, value=value)
    else:
        return GetRequest(key=value)  # sic!


class Server:
    def __init__(self, host: str, port: int):
        self._sock = socket.create_server((host, port))
        self._sock.settimeout(0.1)
        self._event = Event()
        self._store = Store()

    def start(self):
        # The event checking and accept timeout is to allow tests to exit the loop.
        # A bit wasteful though.
        while not self._event.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                pass
            else:
                raw = b""
                while data := conn.recv(128):
                    raw += data
                    # I take end of headers as end of message, ignoring anything that comes later.
                    if b"\r\n\r\n" in raw:
                        break

                request = parse(raw)
                response = handle_request(request, self._store)
                conn.sendall(response.serialize())

        # Should I shutdown first? I'm not sure of best practice.
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
