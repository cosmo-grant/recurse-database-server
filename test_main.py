from main import Request, handle_request, parse


def test_parse_set_request():
    assert parse(b"GET /set?somekey=somevalue HTTP/1.1\r\n\r\n") == Request("somekey", "somevalue")


def test_parse_get_request():
    assert parse(b"GET /get?key=somekey HTTP/1.1\r\n\r\n") == Request("somekey", None)


def test_handle_set_request():
    store = {}
    response = handle_request(Request("somekey", "somevalue"), store=store)
    assert response == "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
    assert store["somekey"] == "somevalue"


def test_handle_get_request():
    store = {"somekey": "somevalue"}
    response = handle_request(Request("somekey", None), store=store)
    assert response == "HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\nsomevalue"
