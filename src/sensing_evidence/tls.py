# SPDX-License-Identifier: MIT
"""Shared verified TLS contexts for capture transports."""

import ssl


def client_context(*, strict=False, cafile=None):
    """Keep platform trust and optionally require 128-bit transport security.

    OpenSSL security level 3 rejects RSA/DH keys below 3072 bits (including
    marginal keys rounded by level 2), short EC keys and static RSA exchange.
    Preserve a stronger system policy and its existing cipher selection.
    """
    context = ssl.create_default_context(cafile=cafile)
    context.minimum_version = max(context.minimum_version, ssl.TLSVersion.TLSv1_2)
    if strict:
        if ssl.OPENSSL_VERSION_INFO < (3, 0, 0):
            raise RuntimeError("Strict TLS requires OpenSSL 3 or newer")
        if context.security_level < 3:
            suites = ":".join(
                cipher["name"] for cipher in context.get_ciphers() if cipher["protocol"] != "TLSv1.3"
            )
            context.set_ciphers(f"{suites}:@SECLEVEL=3")
    return context
