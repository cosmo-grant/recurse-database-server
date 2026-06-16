from threading import Thread

import requests
from pytest import fixture

from main import GetRequest, Response, Server, SetRequest, Store, handle_request, parse


@fixture
def server():
    server = Server("localhost", 0)
    thread = Thread(target=server.start)
    thread.start()
    yield server
    server.stop()
    thread.join()


def test_store():
    store = Store()
    store.set("k", "v")
    assert store.get("k") == "v"


def test_parse_set_request():
    assert parse(b"POST /set?somekey=somevalue HTTP/1.1\r\n\r\n") == SetRequest("somekey", "somevalue")


def test_parse_get_request():
    assert parse(b"GET /get?key=somekey HTTP/1.1\r\n\r\n") == GetRequest("somekey")


def test_handle_set_request():
    store = Store()
    response = handle_request(SetRequest("somekey", "somevalue"), store)
    assert response == Response(200, "OK", {}, b"")
    assert store == Store({"somekey": "somevalue"})


def test_handle_get_request():
    response = handle_request(GetRequest("somekey"), Store({"somekey": "somevalue"}))
    assert response == Response(200, "OK", {}, b"somevalue")


def test_e2e_get_then_set(server):
    port = server.get_port()
    response = requests.post(f"http://localhost:{port}/set", params={"somekey": "somevalue"})
    assert response.status_code == 200
    response = requests.get(f"http://localhost:{port}/get", params={"key": "somekey"})
    assert response.text == "somevalue"


def test_body_is_ignored(server):
    port = server.get_port()
    response = requests.post(
        f"http://localhost:{port}/set",
        data="somebody",
        params={"key": "somekey", "value": "somevalue"},
    )
    assert response.status_code == 200
