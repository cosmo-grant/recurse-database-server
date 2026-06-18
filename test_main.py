from contextlib import contextmanager
from pathlib import Path
from threading import Thread
from time import sleep

import requests
from pytest import raises

from main import GetRequest, Response, Server, SetRequest, Store, handle_request, make_response, parse


@contextmanager
def server_in_thread(host, port, filename):
    server = Server(host, port, filename)
    thread = Thread(target=server.start)
    try:
        thread.start()
        while not server.is_listening():
            sleep(0.1)
        yield server
    finally:
        server.stop()
        thread.join()


def test_server_raises_if_you_look_up_port_without_starting_server():
    server = Server("localhost", 0, Path("some_file.json"))
    with raises(RuntimeError):
        _ = server.port


def test_make_response():
    assert make_response(200, "OK") == Response(200, "OK", {"Content-Length": "0"}, b"")


def test_make_response_with_header():
    assert make_response(
        200,
        "OK",
        headers={"Host": "localhost"},
    ) == Response(
        200,
        "OK",
        {"Host": "localhost", "Content-Length": "0"},
        b"",
    )


def test_make_response_with_body():
    assert make_response(200, "OK", body=b"foobar") == Response(200, "OK", {"Content-Length": "6"}, b"foobar")


def test_make_response_with_headers_and_body():
    assert make_response(
        200,
        "OK",
        headers={"Host": "localhost"},
        body=b"foobar",
    ) == Response(
        200,
        "OK",
        {"Host": "localhost", "Content-Length": "6"},
        b"foobar",
    )


def test_serialize():
    assert Response(200, "OK", {"Content-Length": "6"}, b"foobar").serialize() == b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\n\r\nfoobar"


def test_store():
    store = Store()
    store.set("k", "v")
    assert store.get("k") == "v"


def test_parse_set_request():
    assert parse(b"POST /set?somekey=somevalue HTTP/1.1\r\n\r\n") == SetRequest("somekey", "somevalue")


def test_parse_set_request_with_url_encoding():
    assert parse(b"POST /set?some+key=some%3Avalue HTTP/1.1\r\n\r\n") == SetRequest("some key", "some:value")


def test_parse_get_request():
    assert parse(b"GET /get?key=somekey HTTP/1.1\r\n\r\n") == GetRequest("somekey")


def test_parse_get_request_with_url_encoding():
    assert parse(b"GET /get?key=some%20key HTTP/1.1\r\n\r\n") == GetRequest("some key")


def test_handle_set_request():
    store = Store()
    response = handle_request(SetRequest("somekey", "somevalue"), store)
    assert response == make_response(201, "Created")
    assert store == Store({"somekey": "somevalue"})


def test_handle_get_request():
    response = handle_request(GetRequest("somekey"), Store({"somekey": "somevalue"}))
    assert response == make_response(200, "OK", body="somevalue")


def test_handle_get_request_not_found():
    response = handle_request(GetRequest("nosuchkey"), store=Store())
    assert response == make_response(404, "Not Found")


def test_e2e_set_then_get(tmp_path):
    with server_in_thread("localhost", 0, tmp_path / "store.json") as server:
        post_response = requests.post(f"http://localhost:{server.port}/set", params={"somekey": "somevalue"})
        get_response = requests.get(f"http://localhost:{server.port}/get", params={"key": "somekey"})
    assert post_response.status_code == 201
    assert get_response.status_code == 200
    assert get_response.text == "somevalue"


def test_e2e_set_shutdown_restart_get(tmp_path):
    with server_in_thread("localhost", 0, tmp_path / "store.json") as server:
        post_response = requests.post(f"http://localhost:{server.port}/set", params={"somekey": "somevalue"})
    assert post_response.status_code == 201

    with server_in_thread("localhost", 0, tmp_path / "store.json") as server:
        get_response = requests.get(f"http://localhost:{server.port}/get", params={"key": "somekey"})
    assert get_response.status_code == 200
    assert get_response.text == "somevalue"


def test_extra_parameters_and_body_are_ignored(tmp_path):
    with server_in_thread("localhost", 0, tmp_path / "store.json") as server:
        response = requests.post(
            f"http://localhost:{server.port}/set",
            data="somebody",
            params={"somekey": "somevalue", "extrakey": "extravalue"},
        )
    assert response.status_code == 201
