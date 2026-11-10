"""Request and response schemas of the identity module.

The response models here ARE the JSON the mobile app receives (frozen API contract, sprint 2
section 7): never rename or retype a field. Request models validate what the app may send.
"""

import re
import uuid
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.identity.enums import AlertCode, AlertSeverity, SkinType, Verdict

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class HealthCondition(StrEnum):
    """Closed list of health conditions the suitability engine understands."""

    ECZEMA = "eczema"
    ROSACEA = "rosacea"
    ACNE_PRONE = "acne_prone"
    PSORIASIS = "psoriasis"


# --------------------------------------------------------------------------- requests


class RegisterRequest(BaseModel):
    """Body of POST /auth/register."""

    email: str = Field(max_length=255, description="Account email, stored trimmed and lowercase.")
    password: str = Field(min_length=8, max_length=128, description="Plain password, 8-128 chars.")
    display_name: str = Field(min_length=1, max_length=100, description="Name shown in the app.")

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        if not _EMAIL_PATTERN.match(value):
            raise ValueError("must look like name@domain.tld")
        return value

    @field_validator("display_name", mode="before")
    @classmethod
    def _strip_display_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class LoginRequest(BaseModel):
    """Body of POST /auth/login."""

    email: str = Field(max_length=255, description="Account email.")
    password: str = Field(max_length=128, description="Plain password.")

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class RefreshRequest(BaseModel):
    """Body of POST /auth/refresh."""

    refresh_token: str = Field(description="Refresh token received at register or login.")


class ProfileUpdateIn(BaseModel):
    """Body of PUT /profile: full replacement of the editable profile fields."""

    model_config = ConfigDict(extra="ignore")

    skin_type: SkinType | None = Field(default=None, description="Declared skin type, or null.")
    is_pregnant_or_nursing: bool = Field(default=False, description="Pregnancy or nursing flag.")
    health_conditions: list[HealthCondition] = Field(
        default_factory=list, description="Declared health conditions (closed list)."
    )
    allergy_ingredient_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Ingredient ids the user declares an allergy to."
    )

    @field_validator("health_conditions")
    @classmethod
    def _dedupe_conditions(cls, value: list[HealthCondition]) -> list[HealthCondition]:
        return list(dict.fromkeys(value))

    @field_validator("allergy_ingredient_ids")
    @classmethod
    def _dedupe_allergies(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        return list(dict.fromkeys(value))


# -------------------------------------------------------------------------- responses


class UserOut(BaseModel):
    """Public view of a user account."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID = Field(description="User id.")
    email: str = Field(description="Account email.")
    display_name: str = Field(description="Name shown in the app.")


class AuthTokensOut(BaseModel):
    """Response of POST /auth/register and POST /auth/login."""

    model_config = ConfigDict(frozen=True)

    access_token: str = Field(description="Short-lived JWT sent as Authorization: Bearer.")
    refresh_token: str = Field(description="Long-lived JWT used only at POST /auth/refresh.")
    token_type: Literal["bearer"] = Field(default="bearer", description="Always 'bearer'.")
    user: UserOut = Field(description="The authenticated user.")


class AccessTokenOut(BaseModel):
    """Response of POST /auth/refresh."""

    model_config = ConfigDict(frozen=True)

    access_token: str = Field(description="New short-lived JWT.")
    token_type: Literal["bearer"] = Field(default="bearer", description="Always 'bearer'.")


class ProfileOut(BaseModel):
    """Response of GET and PUT /profile."""

    model_config = ConfigDict(frozen=True)

    user_id: uuid.UUID = Field(description="Owner of the profile.")
    skin_type: SkinType | None = Field(description="Declared skin type, or null.")
    is_pregnant_or_nursing: bool = Field(description="Pregnancy or nursing flag.")
    health_conditions: list[HealthCondition] = Field(description="Declared health conditions.")
    allergy_ingredient_ids: list[uuid.UUID] = Field(description="Declared allergy ingredient ids.")
    blacklisted_product_ids: list[uuid.UUID] = Field(description="Blacklisted product ids.")


class BlacklistOut(BaseModel):
    """Response of GET /profile/blacklist."""

    model_config = ConfigDict(frozen=True)

    product_ids: list[uuid.UUID] = Field(description="Blacklisted product ids.")
    ingredient_ids: list[uuid.UUID] = Field(description="Blacklisted ingredient ids.")


class RiskAlertOut(BaseModel):
    """One personal risk alert on a product."""

    model_config = ConfigDict(frozen=True)

    code: AlertCode = Field(description="Machine-readable alert type.")
    severity: AlertSeverity = Field(description="'high' or 'medium'.")
    ingredient_name: str = Field(description="INCI name of the triggering ingredient.")
    title: str = Field(description="Short alert title in the response language.")
    detail: str = Field(description="Explanation in the response language.")


class SuitabilityOut(BaseModel):
    """Response of GET /products/{product_id}/suitability."""

    model_config = ConfigDict(frozen=True)

    product_id: uuid.UUID = Field(description="Product the verdict is about.")
    suits_profile: bool = Field(description="True only when the verdict is 'suitable'.")
    verdict: Verdict = Field(description="suitable, caution or avoid.")
    has_risk_alert: bool = Field(description="True when there is an alert or a blacklist match.")
    is_blacklisted: bool = Field(description="True for a blacklisted product or ingredient.")
    alerts: list[RiskAlertOut] = Field(description="Alerts, most severe first.")
