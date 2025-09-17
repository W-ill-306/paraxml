# paraxml.py (stub UBL 2.1 mínimo para pruebas) - UTF-8
# Genera XML de Factura a partir de un JSON sencillo (ver ejemplo en README o arriba).
# ⚠️ Sólo para pruebas internas: no incluye firma digital ni todos los campos DIAN.

from decimal import Decimal, ROUND_HALF_UP
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.dom.minidom as minidom

__version__ = "fel-test-0.1.0"

# Namespaces UBL 2.1
NS = {
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}
import xml.etree.ElementTree as ET
for p, uri in NS.items():
    ET.register_namespace(p if p != "inv" else "", uri)

def get_version():
    return __version__

# ---------- Utilidades ----------
def _money(val, nd=2):
    q = Decimal("0." + "0"*(nd-1) + "1") if nd > 0 else Decimal("1")
    return str(Decimal(val).quantize(q, rounding=ROUND_HALF_UP))

def _txt(parent, tag_ns, text):
    el = SubElement(parent, f"{{{NS[tag_ns.split(':')[0]]}}}{tag_ns.split(':')[1]}")
    el.text = str(text)
    return el

def _elm(parent, tag_ns, **attrs):
    el = SubElement(parent, f"{{{NS[tag_ns.split(':')[0]]}}}{tag_ns.split(':')[1]}")
    for k, v in attrs.items():
        if v is not None:
            el.set(k, str(v))
    return el

# ---------- Generación ----------
def generate(invoice: dict) -> str:
    """
    Recibe un dict con la estructura mínima (ver ejemplo) y devuelve XML UBL 2.1 como str.
    """
    # Totales a partir de líneas
    subtotal = Decimal("0")
    tax_total = Decimal("0")

    for ln in invoice.get("lines", []):
        qty = Decimal(str(ln["qty"]["value"]))
        price = Decimal(str(ln["price"]["amount"]))
        line_base = qty * price
        subtotal += line_base
        percent = Decimal(str(ln.get("tax", {}).get("percent", 0)))
        tax_total += (line_base * (percent / Decimal("100")))

    total = subtotal + tax_total
    currency = invoice.get("currency", "COP")

    # Raíz
    inv = Element(f"{{{NS['inv']}}}Invoice")
    # (Opcional) extensiones UBLExtensions
    _elm(inv, "ext:UBLExtensions")

    # Encabezado mínimo
    _txt(inv, "cbc:CustomizationID", "2.1:CO")  # etiqueta de ejemplo
    _txt(inv, "cbc:ProfileExecutionID", "2")    # 1=pruebas, 2=producción (convención común)
    _txt(inv, "cbc:ID", invoice["id"])
    _txt(inv, "cbc:IssueDate", invoice.get("issueDate"))
    if invoice.get("issueTime"):
        _txt(inv, "cbc:IssueTime", invoice["issueTime"])
    _txt(inv, "cbc:InvoiceTypeCode", invoice.get("invoiceTypeCode", "01"))
    _txt(inv, "cbc:DocumentCurrencyCode", currency)

    # Proveedor (AccountingSupplierParty)
    sup = invoice["supplier"]
    asp = _elm(inv, "cac:AccountingSupplierParty")
    party = _elm(asp, "cac:Party")
    _txt(_elm(party, "cac:PartyName"), "cbc:Name", sup["registrationName"])
    pid = _elm(party, "cac:PartyIdentification")
    _txt(pid, "cbc:ID", sup["companyID"]["value"]).set("schemeID", sup["companyID"]["schemeID"])
    addr = _elm(party, "cac:PostalAddress")
    _txt(addr, "cbc:Department", sup["address"]["department"])
    _txt(addr, "cbc:CityName", sup["address"]["city"])
    _txt(addr, "cbc:CountrySubentity", sup["address"]["department"])
    _txt(_elm(addr, "cac:Country"), "cbc:IdentificationCode", sup["address"]["countryCode"])

    # Cliente (AccountingCustomerParty)
    cus = invoice["customer"]
    acp = _elm(inv, "cac:AccountingCustomerParty")
    party = _elm(acp, "cac:Party")
    _txt(_elm(party, "cac:PartyName"), "cbc:Name", cus["registrationName"])
    pid = _elm(party, "cac:PartyIdentification")
    _txt(pid, "cbc:ID", cus["companyID"]["value"]).set("schemeID", cus["companyID"]["schemeID"])
    addr = _elm(party, "cac:PostalAddress")
    _txt(addr, "cbc:Department", cus["address"]["department"])
    _txt(addr, "cbc:CityName", cus["address"]["city"])
    _txt(addr, "cbc:CountrySubentity", cus["address"]["department"])
    _txt(_elm(addr, "cac:Country"), "cbc:IdentificationCode", cus["address"]["countryCode"])

    # Impuestos globales (TaxTotal)
    if tax_total > 0:
        tx = _elm(inv, "cac:TaxTotal")
        _txt(tx, "cbc:TaxAmount", _money(tax_total))
        tsub = _elm(tx, "cac:TaxSubtotal")
        _txt(tsub, "cbc:TaxableAmount", _money(subtotal))
        _txt(tsub, "cbc:TaxAmount", _money(tax_total))
        sch = _elm(_elm(tsub, "cac:TaxCategory"), "cac:TaxScheme")
        _txt(sch, "cbc:ID", "01")   # IVA (ejemplo)
        _txt(sch, "cbc:Name", "IVA")

    # Totales monetarios (LegalMonetaryTotal)
    lmt = _elm(inv, "cac:LegalMonetaryTotal")
    _txt(lmt, "cbc:LineExtensionAmount", _money(subtotal))
    _txt(lmt, "cbc:TaxExclusiveAmount", _money(subtotal))
    _txt(lmt, "cbc:TaxInclusiveAmount", _money(total))
    _txt(lmt, "cbc:PayableAmount", _money(total))

    # Líneas
    for idx, ln in enumerate(invoice.get("lines", []), start=1):
        line = _elm(inv, "cac:InvoiceLine")
        _txt(line, "cbc:ID", ln.get("id", str(idx)))
        qty = ln["qty"]
        _txt(line, "cbc:InvoicedQuantity", str(qty["value"])).set("unitCode", qty["unitCode"])

        # Base de la línea
        qty_val = Decimal(str(qty["value"]))
        price_amt = Decimal(str(ln["price"]["amount"]))
        base = qty_val * price_amt
        _txt(line, "cbc:LineExtensionAmount", _money(base))

        # Impuesto de la línea
        percent = Decimal(str(ln.get("tax", {}).get("percent", 0)))
        if percent > 0:
            total_line_tax = (base * percent / Decimal("100"))
            t = _elm(line, "cac:TaxTotal")
            _txt(t, "cbc:TaxAmount", _money(total_line_tax))
            ts = _elm(t, "cac:TaxSubtotal")
            _txt(ts, "cbc:TaxableAmount", _money(base))
            _txt(ts, "cbc:TaxAmount", _money(total_line_tax))
            cat = _elm(ts, "cac:TaxCategory")
            _txt(cat, "cbc:Percent", _money(percent, 2))
            sch = _elm(cat, "cac:TaxScheme")
            _txt(sch, "cbc:ID", ln["tax"].get("schemeID", "01"))
            _txt(sch, "cbc:Name", ln["tax"].get("name", "IVA"))

        # Item
        item = _elm(line, "cac:Item")
        _txt(item, "cbc:Description", ln.get("description", "ITEM"))
        _txt(_elm(item, "cac:SellersItemIdentification"), "cbc:ID", ln.get("itemCode", "ITEM"))

        # Precio
        price = _elm(line, "cac:Price")
        _txt(price, "cbc:PriceAmount", _money(price_amt))
        bq = ln["price"].get("baseQty")
        if bq:
            _txt(price, "cbc:BaseQuantity", str(bq["value"])).set("unitCode", bq["unitCode"])

    # Pretty print
    xml_bytes = tostring(inv, encoding="utf-8", method="xml")
    return minidom.parseString(xml_bytes).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

def generate_to_file(invoice: dict, path: str) -> str:
    """Genera el XML y lo escribe en 'path'. Retorna la ruta."""
    xml = generate(invoice)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    return path
