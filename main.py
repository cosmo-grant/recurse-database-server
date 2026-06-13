import socket


def main():
    server = socket.create_server(("localhost", 4000))
    conn, _ = server.accept()
    request = b""
    while data := conn.recv(128):
        request += data
        # I assume all requests are body-free, so end of message is end of headers.
        if request.endswith(b"\r\n\r\n"):
            break
    print(request)


if __name__ == "__main__":
    main()
