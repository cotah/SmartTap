from functools import lru_cache

import httpx
from supabase import Client, create_client

from app.config import get_settings

_SAFE_METHODS = {"GET", "HEAD"}


class _RetryOnStaleConnectionTransport(httpx.BaseTransport):
    """Retry once when a reused keep-alive connection turns out to be dead.

    Supabase's edge (Cloudflare) drops idle keep-alive connections; when httpx
    reuses one it raises RemoteProtocolError("Server disconnected"). postgrest's
    own send_with_retry only covers HTTP 503/520 responses, so the exception
    would otherwise propagate as a 500. Only safe (read) methods are retried —
    a write could already have been applied before the connection died.
    """

    def __init__(self, inner: httpx.BaseTransport) -> None:
        self._inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return self._inner.handle_request(request)
        except httpx.RemoteProtocolError:
            if request.method not in _SAFE_METHODS:
                raise
            return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()


@lru_cache
def get_supabase_admin() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase admin client not configured")
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    # `.postgrest` is a lazy property; touching it builds the httpx session we
    # then wrap with the stale-connection retry.
    session = client.postgrest.session
    session._transport = _RetryOnStaleConnectionTransport(session._transport)
    return client
