from typing import Protocol


class BrokerConnector(Protocol):
    """Interface future broker integrations should implement."""

    def list_accounts(self) -> list[dict[str, object]]:
        raise NotImplementedError


class BrokerIntegrationUnavailable(RuntimeError):
    """Raised when broker functionality is requested before integrations exist."""


def get_broker_connector() -> BrokerConnector:
    raise BrokerIntegrationUnavailable("Broker integrations are not implemented yet.")
