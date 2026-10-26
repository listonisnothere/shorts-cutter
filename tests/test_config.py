import pytest

from shorts_cutter.config import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SHORTS_OPENAI_API_KEY", raising=False)


def test_openai_key_from_shared_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-shared\nSHORTS_TRANSCRIBER=elevenlabs\n")

    settings = Settings(_env_file=env)
    assert settings.openai_api_key == "sk-shared"
    assert settings.TRANSCRIBER == "elevenlabs"


def test_module_key_wins_over_shared_key(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-shared\nSHORTS_OPENAI_API_KEY=sk-shorts\n")

    assert Settings(_env_file=env).openai_api_key == "sk-shorts"


def test_module_key_in_env_file_wins_over_shared_key_in_shell(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-personal")
    env = tmp_path / ".env"
    env.write_text("SHORTS_OPENAI_API_KEY=sk-shorts\n")

    assert Settings(_env_file=env).openai_api_key == "sk-shorts"


def test_no_key_lets_the_client_report_it(tmp_path):
    assert Settings(_env_file=tmp_path / "missing.env").openai_api_key is None
