from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

OUTPUT = Path(__file__).with_name("Photon-Ops-Navigator-Executive-Flyer.pdf")
PAGE = landscape(letter)

INK = HexColor("#06101A")
DEEP = HexColor("#0A1A27")
PANEL = HexColor("#102534")
LINE = HexColor("#294554")
TEXT = HexColor("#EAF4F7")
MUTED = HexColor("#91A8B3")
CYAN = HexColor("#2FC3E8")
CYAN_PALE = HexColor("#A5EAF8")
VIOLET = HexColor("#9D7CFF")
GREEN = HexColor("#58D69B")
AMBER = HexColor("#F2A93B")


def text(c, x, y, value, size, color=TEXT, font="Helvetica", leading=None):
    c.setFillColor(color)
    c.setFont(font, size)
    if leading is None or "\n" not in value:
        c.drawString(x, y, value)
        return y
    cursor = y
    for line in value.splitlines():
        c.drawString(x, cursor, line)
        cursor -= leading
    return cursor


def rounded_panel(c, x, y, width, height, fill=PANEL, stroke=LINE, radius=8):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.7)
    c.roundRect(x, y, width, height, radius, fill=1, stroke=1)


def pill(c, x, y, label, color):
    padding = 11
    width = stringWidth(label, "Helvetica-Bold", 8) + padding * 2
    c.setFillColor(DEEP)
    c.setStrokeColor(color)
    c.roundRect(x, y, width, 22, 11, fill=1, stroke=1)
    text(c, x + padding, y + 7, label, 8, color, "Helvetica-Bold")
    return width


def feature(c, x, y, number, title, body, color):
    c.setStrokeColor(color)
    c.setFillColor(DEEP)
    c.circle(x + 14, y + 52, 14, fill=1, stroke=1)
    text(c, x + 8.2, y + 48, number, 9, color, "Helvetica-Bold")
    text(c, x + 39, y + 58, title, 12, TEXT, "Helvetica-Bold")
    body_lines = wrap(body, 49)
    text(c, x + 39, y + 43, "\n".join(body_lines), 8.5, MUTED, leading=12)


def wrap(value, max_chars):
    words = value.split()
    lines = []
    current = []
    for word in words:
        if len(" ".join(current + [word])) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def architecture_box(c, x, y, width, title, subtitle, color):
    rounded_panel(c, x, y, width, 48, fill=DEEP, stroke=color, radius=6)
    text(c, x + 12, y + 28, title, 9, TEXT, "Helvetica-Bold")
    text(c, x + 12, y + 13, subtitle, 7.5, MUTED)


def draw_flyer():
    c = canvas.Canvas(str(OUTPUT), pagesize=PAGE)
    c.setTitle("Photon-Ops Navigator Executive Flyer")
    c.setAuthor("CamoZeroDay")
    c.setSubject("AI-guided fiber operations and optical intelligence")

    width, height = PAGE
    c.setFillColor(INK)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    c.setStrokeColor(HexColor("#163346"))
    c.setLineWidth(0.35)
    for x in range(0, int(width), 32):
        c.line(x, 0, x, height)
    for y in range(0, int(height), 32):
        c.line(0, y, width, y)

    c.setStrokeColor(VIOLET)
    c.setLineWidth(2.2)
    path = c.beginPath()
    path.moveTo(42, height - 58)
    path.curveTo(116, height - 18, 165, height - 93, 242, height - 51)
    path.curveTo(310, height - 15, 364, height - 84, 428, height - 50)
    c.drawPath(path, stroke=1, fill=0)
    c.setFillColor(CYAN)
    for x, y in [(42, height - 58), (242, height - 51), (428, height - 50)]:
        c.circle(x, y, 4, fill=1, stroke=0)

    text(c, 46, height - 120, "PHOTON-OPS", 11, CYAN_PALE, "Helvetica-Bold")
    text(c, 46, height - 163, "Navigator", 42, TEXT, "Helvetica-Bold")
    text(c, 46, height - 193, "Operate the route. Understand the light.", 17, CYAN_PALE, "Helvetica-Bold")
    text(
        c,
        46,
        height - 221,
        "An AI-guided workspace that turns an operator narrative into a verified circuit,\nreal satellite context, fault location, optical margin, impact, and field dispatch.",
        10,
        MUTED,
        leading=15,
    )

    x_cursor = 46
    for label, color in [
        ("DOCKER DEMO", VIOLET),
        ("EKS PRODUCTION", CYAN),
        ("ENTRA ID", GREEN),
        ("AWS BEDROCK BUILT IN", AMBER),
    ]:
        x_cursor += pill(c, x_cursor, height - 270, label, color) + 8

    rounded_panel(c, 46, 144, 464, 180, fill=HexColor("#0B1C29"))
    feature(c, 62, 231, "01", "Ask, then verify", "Bedrock extracts bounded intent; the network provider verifies the circuit before analysis.", CYAN)
    feature(c, 282, 231, "02", "See the real route", "Overlay ordered plant, assets, and OTDR events on real satellite imagery.", VIOLET)
    feature(c, 62, 153, "03", "Model the light", "Carry route distance into Photon Bench for loss, receive power, and engineering headroom.", AMBER)
    feature(c, 282, 153, "04", "Restore with context", "Calculate downstream impact and build a deterministic, circuit-aware field plan.", GREEN)

    rounded_panel(c, 532, 144, 214, 369, fill=HexColor("#0B1C29"))
    text(c, 554, 482, "EXECUTIVE VALUE", 9, CYAN_PALE, "Helvetica-Bold")
    text(c, 554, 445, "One operational", 24, TEXT, "Helvetica-Bold")
    text(c, 554, 418, "source of truth.", 24, TEXT, "Helvetica-Bold")
    text(c, 554, 383, "Operator intent, provider-verified data,\nsatellite context, and optical assumptions\nstay attached to the same investigation.", 9, MUTED, leading=14)

    values = [
        ("DETERMINISTIC", "Core analysis"),
        ("SINGLE-TENANT", "Entra identity"),
        ("US-EAST-1", "AWS production"),
        ("VERIFIED DATA", "Plant data contract"),
    ]
    y = 326
    for headline, label in values:
        c.setStrokeColor(LINE)
        c.line(554, y + 25, 724, y + 25)
        text(c, 554, y + 4, headline, 10, TEXT, "Helvetica-Bold")
        text(c, 724 - stringWidth(label, "Helvetica", 8), y + 4, label, 8, MUTED)
        y -= 49

    text(c, 46, 116, "PORTABLE BY DESIGN", 8, MUTED, "Helvetica-Bold")
    architecture_box(c, 46, 50, 120, "Microsoft Entra ID", "PKCE + API scope", VIOLET)
    architecture_box(c, 188, 50, 120, "Next.js workspace", "Navigator + satellite + Bench", CYAN)
    architecture_box(c, 330, 50, 120, "FastAPI analysis", "Intent + OTDR + impact", GREEN)
    architecture_box(c, 472, 50, 120, "Provider contract", "PostGIS / VETRO", AMBER)
    architecture_box(c, 614, 50, 132, "Amazon EKS", "RDS + ALB + Helm", CYAN)
    for start in [166, 308, 450, 592]:
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.line(start + 4, 74, start + 17, 74)
        c.line(start + 13, 78, start + 17, 74)
        c.line(start + 13, 70, start + 17, 74)

    text(c, 46, 22, "PHOTON-OPS NAVIGATOR", 7.5, CYAN_PALE, "Helvetica-Bold")
    footer = "Docker demonstration  |  Amazon EKS production  |  Optional AWS Bedrock Mantle"
    text(c, width - 46 - stringWidth(footer, "Helvetica", 7.5), 22, footer, 7.5, MUTED)

    c.save()


if __name__ == "__main__":
    draw_flyer()
    print(OUTPUT)
