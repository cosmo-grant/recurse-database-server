from threading import Thread

import requests

from main import GetRequest, Response, Server, SetRequest, handle_request, parse


def test_parse_set_request():
    assert parse(b"POST /set?somekey=somevalue HTTP/1.1\r\n\r\n") == SetRequest("somekey", "somevalue")


def test_parse_get_request():
    assert parse(b"GET /get?key=somekey HTTP/1.1\r\n\r\n") == GetRequest("somekey")


def test_handle_set_request():
    store = {}
    response = handle_request(SetRequest("somekey", "somevalue"), store=store)
    assert response == Response(200, "OK", {}, b"")
    assert store["somekey"] == "somevalue"


def test_handle_get_request():
    store = {"somekey": "somevalue"}
    response = handle_request(GetRequest("somekey"), store=store)
    assert response == Response(200, "OK", {}, b"somevalue")


def test_e2e_get_then_set():
    server = Server()
    thread = Thread(target=server.start)
    thread.start()
    response = requests.post("http://localhost:4000/set", params={"somekey": "somevalue"})
    assert response.status_code == 200
    response = requests.get("http://localhost:4000/get", params={"key": "somekey"})
    assert response.text == "somevalue"
    server.stop()
    thread.join()
