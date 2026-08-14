import pytest
from ev_twin_api.schemas.admin import AdminInviteRequest, AdminUserUpdate
from ev_twin_api.schemas.auth import AppRole
from pydantic import ValidationError


def test_invite_normalizes_email_and_rejects_password_field() -> None:
    invite = AdminInviteRequest.model_validate(
        {
            "email": "  USER@Example.COM ",
            "display_name": "  Factory User  ",
            "role": "DESIGNER",
        }
    )

    assert invite.email == "user@example.com"
    assert invite.display_name == "Factory User"
    assert invite.role == AppRole.DESIGNER

    with pytest.raises(ValidationError):
        AdminInviteRequest.model_validate(
            {
                "email": "user@example.com",
                "display_name": "Factory User",
                "role": "DESIGNER",
                "password": "must-not-be-accepted",
            }
        )


@pytest.mark.parametrize("email", ["invalid", "user@localhost", "user @example.com"])
def test_invite_rejects_invalid_email_shape(email: str) -> None:
    with pytest.raises(ValidationError):
        AdminInviteRequest(email=email, display_name="User", role=AppRole.DESIGNER)


def test_user_update_requires_a_field_and_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AdminUserUpdate()
    with pytest.raises(ValidationError):
        AdminUserUpdate.model_validate({"display_name": "Not mutable"})

    assert AdminUserUpdate(role=AppRole.MONITOR).role == AppRole.MONITOR
