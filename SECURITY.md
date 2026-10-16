# Security policy

The latest stable release and the current 0.1 source line receive security fixes. Prereleases are previews; a stable software release does not certify sensing accuracy. Upgrade using the instructions in [reproducibility](docs/reproducibility.md) and preserve private evidence before changing versions.

Report vulnerabilities privately through [GitHub Security](https://github.com/ha-homelab/sensing-evidence-kit/security/advisories/new) or **alvit.work@gmail.com**. Include the affected version or commit, impact and a minimal synthetic reproducer. Do not post an exploit, a token or real household evidence publicly. The maintainer aims to acknowledge reports within 14 days, reproduce and assess them privately, coordinate disclosure, test the fix and publish upgrade instructions. Critical issues are addressed immediately; other medium-or-higher issues should be fixed within 60 days. Release notes include available advisory identifiers and credit the reporter unless anonymity is requested. If one private channel gets no response, use the other. There is no independent security team or backup maintainer.

Evidence can contain sensitive local observations, location labels, opaque host/boot identifiers and operator notes. Store it privately. The CLI creates owner-only sessions and does not overwrite existing evidence/report files. Use one writer for labels. Hashes provide consistency checks, not authenticity or digital signatures.

Tokens are read from the environment or an explicitly supplied adapter; they are not evidence fields. Use HTTPS for remote Home Assistant access and appropriate account permissions. Custom adapters are trusted Python code. Do not load unreviewed adapters or configuration from an untrusted party.

This toolkit does not validate a detector for emergency, healthcare, security or other safety-critical use.

The [supported profiles](docs/security-profiles.md) distinguish the complete offline workflow from optional live capture and describe the limits of each. An imported adapter is trusted executable code, not an untrusted evidence file.
