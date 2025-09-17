# paraxml.py (stub de prueba) - UTF-8
__version__ = "test-0.0.1"

def get_version():
    return __version__

def generate(rips_json: dict) -> str:
    """Recibe el JSON final de RIPSON y devuelve un XML mínimo.
    Sustituye esta función por la implementación real cuando esté lista.
    """
    from xml.sax.saxutils import escape
    try:
        cnt = len(rips_json.get("usuarios", [])) if isinstance(rips_json, dict) else 0
    except Exception:
        cnt = 0
    return "\n".join([
        "<RIPS>",
        "  <Version>" + escape(__version__) + "</Version>",
        f"  <Usuarios count=\"{cnt}\" />",
        "</RIPS>",
    ])
