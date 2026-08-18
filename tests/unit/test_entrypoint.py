from juicebox import __main__


def test_main_starts_uvicorn_with_settings(monkeypatch):
    captured = {}

    def fake_run(app, **kwargs):
        captured["app"] = app
        captured["kwargs"] = kwargs

    monkeypatch.setattr(__main__.uvicorn, "run", fake_run)
    __main__.main()

    assert captured["app"] == "juicebox.app:create_app"
    assert captured["kwargs"]["port"] == 8000
    assert captured["kwargs"]["factory"] is True
