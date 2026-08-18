#!/usr/bin/env python3
"""Deterministic tracking-link form validator — no LLM.

Mirrors the production database constraints of the reference tracking system:
slug shape, destination safety, mandatory UTMs, tracked = destination + UTMs.
Exit 0 when the link form is valid (prints TRACKING VALID), exit 1 otherwise.
"""

import argparse
import json
import re
import sys
from urllib.parse import urlparse, parse_qs

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 100
SLUG_MAX = 80
UTM_MAX = 120
DEST_MAX = 2048
TRACKED_MAX = 4096


def erros_link(link):
    """Returns the list of form errors for one link object. Empty = valid."""
    erros = []

    name = link.get("name")
    if not isinstance(name, str) or not (1 <= len(name) <= NAME_MAX):
        erros.append("name: required string, 1-100 chars")

    slug = link.get("slug")
    if not isinstance(slug, str) or not (1 <= len(slug) <= SLUG_MAX) or not SLUG_RE.match(slug):
        erros.append("slug: must match ^[a-z0-9]+(-[a-z0-9]+)*$, 1-80 chars")

    dest = link.get("destination_url")
    if not isinstance(dest, str) or len(dest) > DEST_MAX or not dest.startswith(("http://", "https://")):
        erros.append("destination_url: must start with http(s):// and be <=2048 chars")
    else:
        parsed = urlparse(dest)
        if not parsed.hostname:
            erros.append("destination_url: must have a hostname")
        if parsed.query:
            erros.append("destination_url: must be query-free (tracked URL is destination + utm params)")
        if parsed.username or parsed.password:
            erros.append("destination_url: credentials embedded in URL")
        # case-insensitive: /T/ is the same loop
        if parsed.path.lower().startswith("/t/"):
            erros.append("destination_url: must not point to another tracking link (/t/ loop)")

    tracked = link.get("tracked_destination_url")
    if not isinstance(tracked, str) or len(tracked) > TRACKED_MAX or not tracked.startswith(("http://", "https://")):
        erros.append("tracked_destination_url: must start with http(s):// and be <=4096 chars")
    elif isinstance(dest, str) and dest.startswith("http"):
        if not tracked.startswith(dest + "?"):
            erros.append("tracked_destination_url: must be destination_url + query string")
        else:
            qs = tracked[len(dest) + 1:]
            valores = parse_qs(qs, keep_blank_values=True)
            for chave in ("utm_source", "utm_medium", "utm_campaign"):
                if not valores.get(chave) or not valores[chave][0]:
                    erros.append("tracked_destination_url: missing or empty %s param" % chave)

    for chave in ("utm_source", "utm_medium", "utm_campaign"):
        valor = link.get(chave)
        if not isinstance(valor, str) or not (1 <= len(valor) <= UTM_MAX):
            erros.append("%s: required string, 1-120 chars" % chave)
    for chave in ("utm_content", "utm_term"):
        if chave in link and (not isinstance(link[chave], str) or len(link[chave]) > UTM_MAX):
            erros.append("%s: optional string, <=120 chars when present" % chave)

    if "is_active" in link and not isinstance(link["is_active"], bool):
        erros.append("is_active: boolean when present")
    if "expires_at" in link:
        exp = link["expires_at"]
        if not isinstance(exp, str):
            erros.append("expires_at: ISO timestamp string when present")
        else:
            from datetime import datetime
            try:
                datetime.fromisoformat(exp.replace("Z", "+00:00"))
            except ValueError:
                erros.append("expires_at: ISO timestamp string when present")

    return erros


def _copia_valida():
    return {
        "name": "Campanha de exemplo",
        "slug": "exemplo-campanha",
        "destination_url": "https://exemplo.com.br/lp/demo",
        "tracked_destination_url": "https://exemplo.com.br/lp/demo?utm_source=referral&utm_medium=site&utm_campaign=demo",
        "utm_source": "referral",
        "utm_medium": "site",
        "utm_campaign": "demo",
        "is_active": True,
    }


CASOS_QUEBRADOS = [
    ("slug com underline e maiuscula", {"slug": "Campanha_Exemplo"}),
    ("slug vazio", {"slug": ""}),
    ("destino com credencial", {
        "destination_url": "https://user:pass@exemplo.com.br/x",
        "tracked_destination_url": "https://user:pass@exemplo.com.br/x?utm_source=a&utm_medium=b&utm_campaign=c",
    }),
    ("destino aponta para /t/ (loop)", {
        "destination_url": "https://exemplo.com.br/t/outro-link",
        "tracked_destination_url": "https://exemplo.com.br/t/outro-link?utm_source=a&utm_medium=b&utm_campaign=c",
    }),
    ("utm_medium ausente", {"utm_medium": None}),
    ("utm_source vazio", {"utm_source": ""}),
    ("tracked nao deriva do destino", {
        "tracked_destination_url": "https://outro-dominio.com/?utm_source=a&utm_medium=b&utm_campaign=c",
    }),
    ("name vazio", {"name": ""}),
    ("destino sem hostname", {
        "destination_url": "https:///sem-host",
        "tracked_destination_url": "https:///sem-host?utm_source=a&utm_medium=b&utm_campaign=c",
    }),
    ("loop /T/ maiusculo", {
        "destination_url": "https://exemplo.com.br/T/outro-link",
        "tracked_destination_url": "https://exemplo.com.br/T/outro-link?utm_source=a&utm_medium=b&utm_campaign=c",
    }),
    ("utm_campaign sem valor", {
        "tracked_destination_url": "https://exemplo.com.br/lp/demo?utm_source=referral&utm_medium=site&utm_campaign=",
    }),
    ("expires_at invalido", {"expires_at": "amanha"}),
    ("destino com query", {
        "destination_url": "https://exemplo.com.br/x?ref=1",
        "tracked_destination_url": "https://exemplo.com.br/x?ref=1?utm_source=a&utm_medium=b&utm_campaign=c",
    }),
]


def self_test():
    falhas = []
    for descricao, mutacao in CASOS_QUEBRADOS:
        link = _copia_valida()
        link.update(mutacao)
        if not erros_link(link):
            falhas.append("deveria reprovar: %s" % descricao)
    if erros_link(_copia_valida()):
        falhas.append("deveria aprovar o exemplo valido")
    if falhas:
        print("SELF-TEST FAIL:")
        for f in falhas:
            print("  - " + f)
        return 1
    print("SELF-TEST OK: %d casos quebrados reprovados, caso valido aprovado" % len(CASOS_QUEBRADOS))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="JSON file with the link object")
    parser.add_argument("--self-test", action="store_true", help="run embedded regression cases")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if not args.input:
        parser.error("inform --input <arquivo> ou --self-test")

    with open(args.input, encoding="utf-8") as f:
        dados = json.load(f)
    if not isinstance(dados, dict):
        print("TRACKING INVALID (1):")
        print("  - input must be a JSON object")
        sys.exit(1)
    link = dados.get("link", dados)

    erros = erros_link(link)
    if erros:
        print("TRACKING INVALID (%d):" % len(erros))
        for e in erros:
            print("  - " + e)
        sys.exit(1)
    print("TRACKING VALID")
    sys.exit(0)


if __name__ == "__main__":
    main()
