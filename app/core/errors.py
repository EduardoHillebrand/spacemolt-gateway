"""Gateway-level exceptions."""


class PreconditionError(Exception):
    """Raised when a skill cannot run due to an unmet precondition.

    The message must explain *what* is missing so the LLM can act on it.

    Example:
        raise PreconditionError("missing mining laser")
    """
