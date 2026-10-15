# Security policy

The latest public beta is supported. Use GitHub Security → Report a vulnerability when available for private reporting. If unavailable, open an issue requesting a private contact without exploit details or sensitive evidence. Include the affected version and a synthetic reproducer. There is no guaranteed response deadline during beta.

Evidence can contain sensitive local observations, location labels, opaque host/boot identifiers and operator notes. Store it privately. The CLI creates owner-only sessions and does not overwrite existing evidence/report files. Use one writer for labels. Hashes provide consistency checks, not authenticity or digital signatures.

Tokens are read from the environment or an explicitly supplied adapter; they are not evidence fields. Use HTTPS for remote Home Assistant access and appropriate account permissions. Custom adapters are trusted Python code. Do not load unreviewed adapters or configuration from an untrusted party.

This toolkit does not validate a detector for emergency, healthcare, security or other safety-critical use.
