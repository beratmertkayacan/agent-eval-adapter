from adapter.config import DEFAULT_PORT, DEFAULT_TARGET_URL, load_settings


def test_settings_read_environment_variables(monkeypatch):
    monkeypatch.setenv("TARGET_AGENT_BASE_URL", "http://agent.local:9000")
    monkeypatch.setenv("PORT", "9100")

    settings = load_settings()

    assert settings.target_agent_base_url == "http://agent.local:9000"
    assert settings.port == 9100


def test_settings_use_defaults_when_values_are_missing(monkeypatch):
    monkeypatch.delenv("TARGET_AGENT_BASE_URL", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    settings = load_settings()

    assert settings.target_agent_base_url == DEFAULT_TARGET_URL
    assert settings.port == DEFAULT_PORT
