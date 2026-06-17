# CONTRIBUTING

Run the server:

```text
uv run python main.py
```

Hit the server:

```text
curl -X POST 'http://localhost:4000/set?somekey=somevalue'
curl 'http://localhost:4000/get?key=somekey'
```

Run formatter, linter, type checker, tests:

```text
just check
```
