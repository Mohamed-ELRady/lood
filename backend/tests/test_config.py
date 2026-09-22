from app.config import Settings


def test_cors_origins_accept_comma_separated_environment(monkeypatch):
    monkeypatch.setenv("LOOD_CORS_ORIGINS", "https://lood.example,http://localhost:3000")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["https://lood.example", "http://localhost:3000"]
