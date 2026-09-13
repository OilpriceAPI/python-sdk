"""A ValidationError must not eat the message its raiser composed (#117).

``ValidationError.__str__`` replaced the message with
``"Validation error for '<field>'"`` whenever ``field`` was set. Every caller
that passes both ``message=`` and ``field=`` -- which is almost all of them --
lost its explanation, and nothing in normal Python printed it: not ``str(e)``,
not the traceback's last line, not ``logging.exception``, not a pytest repr.

The origin guard added in #113 composes four sentences of remediation and is
the worst-hit caller: for a non-string path (``value is None``) even the reason
disappeared.
"""

import pytest

from oilpriceapi._url import resolve_api_url
from oilpriceapi.exceptions import ValidationError

BASE = "https://api.oilpriceapi.com"


def test_composed_message_survives_str_when_field_is_set():
    error = ValidationError(
        "Radius must be between 0 and 50000 meters",
        field="radius",
        value=99999,
    )

    rendered = str(error)
    assert "Radius must be between 0 and 50000 meters" in rendered
    # The field/value detail other callers rely on is still there.
    assert "radius" in rendered
    assert "99999" in rendered


def test_default_message_still_renders_the_historical_field_form():
    """Nothing useful was supplied, so the field/value form is the message."""
    error = ValidationError(field="per_page", value=-1)

    assert str(error) == "Validation error for 'per_page': invalid value '-1'"


def test_default_message_without_value_still_renders_the_field():
    error = ValidationError(field="per_page")

    assert str(error) == "Validation error for 'per_page'"


@pytest.mark.parametrize(
    "path",
    [
        "//fixture.invalid/v1/prices/latest",
        "https://fixture.invalid/v1/prices/latest",
        "/v1/prices\nHost: fixture.invalid",
    ],
)
def test_origin_guard_remediation_is_reachable_through_str(path):
    with pytest.raises(ValidationError) as excinfo:
        resolve_api_url(BASE, path)

    rendered = str(excinfo.value)
    assert "Refusing to send this request" in rendered
    assert "construct a client with that base_url instead" in rendered


def test_origin_guard_reason_survives_for_a_non_string_path():
    """value is None here, so the old form printed only 'Validation error'."""
    with pytest.raises(ValidationError) as excinfo:
        resolve_api_url(BASE, None)

    rendered = str(excinfo.value)
    assert "must be a string" in rendered
    assert "NoneType" in rendered


def test_str_still_does_not_leak_a_credential():
    """The guard echoes the path back; that must remain the only echoed value."""
    with pytest.raises(ValidationError) as excinfo:
        resolve_api_url(BASE, "//fixture.invalid/v1/prices/latest")

    assert "fixture-not-a-real-key" not in str(excinfo.value)
