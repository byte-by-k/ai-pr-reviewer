from src import cli


def test_publish_flag_skips_confirmation(monkeypatch):
    def unexpected_confirm(*args, **kwargs):
        raise AssertionError("Confirmation must not run with --publish")

    monkeypatch.setattr(cli.click, "confirm", unexpected_confirm)
    assert cli._should_publish(True) is True


def test_default_publish_path_prompts_with_no_default(monkeypatch):
    received = {}

    def confirm(message, default):
        received.update(message=message, default=default)
        return False

    monkeypatch.setattr(cli.click, "confirm", confirm)

    assert cli._should_publish(False) is False
    assert received == {
        "message": "Post the review comments to the pull request?",
        "default": False,
    }
