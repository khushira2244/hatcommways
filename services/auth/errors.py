class AuthError(Exception):
    pass


class DuplicateEmailError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InvalidSessionError(AuthError):
    pass
