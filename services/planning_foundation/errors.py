"""Domain errors raised by the deterministic planning foundation."""


class PlanningError(Exception):
    """Base class for deterministic planning failures."""


class AuthorizationError(PlanningError):
    pass


class NotFoundError(PlanningError):
    pass


class ValidationError(PlanningError):
    pass


class StaleProposalError(PlanningError):
    pass


class ProposalAlreadyDecidedError(PlanningError):
    pass
