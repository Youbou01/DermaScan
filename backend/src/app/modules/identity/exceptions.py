"""Identity errors. The `code` becomes the problem `type` the mobile app switches on:
urn:skincare:problem:<code>."""

from app.core.errors import ConflictError, NotFoundError, UnauthorizedError


class EmailAlreadyRegisteredError(ConflictError):
    code = "email-already-registered"
    title = "Email already registered"


class InvalidCredentialsError(UnauthorizedError):
    code = "invalid-credentials"
    title = "Invalid email or password"


class IngredientNotFoundError(NotFoundError):
    code = "ingredient-not-found"
    title = "Ingredient not found"
