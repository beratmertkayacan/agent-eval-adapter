from adapter.redaction import REDACTED, redact


def test_default_sensitive_fields_are_redacted():
    data = {
        "apiKey": "sk-123",
        "authorization": "Bearer abc",
        "token": "t-1",
        "password": "p@ss",
        "secret": "s-1",
        "message": "Invoice No: INV-1001",
    }

    assert redact(data) == {
        "apiKey": REDACTED,
        "authorization": REDACTED,
        "token": REDACTED,
        "password": REDACTED,
        "secret": REDACTED,
        "message": "Invoice No: INV-1001",
    }


def test_names_are_matched_without_case_dashes_or_underscores():
    data = {"API_KEY": "1", "Authorization": "2", "access-token": "3", "clientSecret": "4"}

    assert set(redact(data).values()) == {REDACTED}


def test_nested_objects_and_lists_are_redacted():
    data = {"headers": {"Authorization": "Bearer abc"}, "users": [{"name": "a", "password": "x"}]}

    assert redact(data) == {
        "headers": {"Authorization": REDACTED},
        "users": [{"name": "a", "password": REDACTED}],
    }


def test_custom_fields_can_be_added():
    data = {"iban": "TR00 0000", "customerEmail": "a@b.com", "city": "Ankara"}

    assert redact(data, ["iban", "email"]) == {
        "iban": REDACTED,
        "customerEmail": REDACTED,
        "city": "Ankara",
    }


def test_original_data_is_not_changed():
    data = {"token": "t-1"}

    redact(data)

    assert data == {"token": "t-1"}


def test_values_that_are_not_objects_are_kept():
    assert redact("plain text") == "plain text"
    assert redact(None) is None
