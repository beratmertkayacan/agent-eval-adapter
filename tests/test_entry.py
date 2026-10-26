import adapter.__main__ as entry


def test_main_uses_port_from_settings(monkeypatch):
    calls = {}
    monkeypatch.setenv("PORT", "9100")
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, host, port: calls.update(port=port))

    entry.main()

    assert calls == {"port": 9100}
