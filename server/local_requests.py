from __future__ import annotations

import ipaddress

from fastapi import HTTPException, Request


def check_local_request(request: Request) -> None:
    host = request.client.host if request.client else ""
    try:
        is_local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_local = False
    if not is_local:
        raise HTTPException(status_code=403, detail="Movie library settings are local-only")