from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

OUTPUT = "architecture-diagram.pdf"
WIDTH, HEIGHT = landscape(A4)
NAVY = colors.HexColor("#17211B")
GREEN = colors.HexColor("#B8D86B")
PAPER = colors.HexColor("#F4F0E8")
MUTED = colors.HexColor("#687268")
LINE = colors.HexColor("#BFC8B9")
WHITE = colors.white


def box(pdf, x, y, w, h, title, body, fill=WHITE, accent=GREEN):
    pdf.setFillColor(fill)
    pdf.setStrokeColor(LINE)
    pdf.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    pdf.setFillColor(accent)
    pdf.rect(x, y + h - 5, w, 5, fill=1, stroke=0)
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x + 12, y + h - 24, title)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8.5)
    text_y = y + h - 42
    for line in simpleSplit(body, "Helvetica", 8.5, w - 24):
        pdf.drawString(x + 12, text_y, line)
        text_y -= 12


def arrow(pdf, x1, y1, x2, y2, label=None):
    pdf.setStrokeColor(NAVY)
    pdf.setFillColor(NAVY)
    pdf.setLineWidth(1.2)
    pdf.line(x1, y1, x2, y2)
    pdf.line(x2, y2, x2 - 6, y2 + 3)
    pdf.line(x2, y2, x2 - 6, y2 - 3)
    if label:
        pdf.setFont("Helvetica", 7.5)
        pdf.setFillColor(MUTED)
        pdf.drawCentredString((x1 + x2) / 2, y1 + 6, label)


pdf = canvas.Canvas(OUTPUT, pagesize=landscape(A4))
pdf.setTitle("ContextPilot Architecture")
pdf.setFillColor(PAPER)
pdf.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)

pdf.setFillColor(NAVY)
pdf.setFont("Helvetica-Bold", 24)
pdf.drawString(42, HEIGHT - 52, "ContextPilot")
pdf.setFillColor(MUTED)
pdf.setFont("Helvetica", 10)
pdf.drawString(43, HEIGHT - 70, "AI assistant architecture | bounded agent loop, RAG, tools, evaluation, and local deployment")
pdf.setFillColor(GREEN)
pdf.rect(42, HEIGHT - 84, 90, 3, fill=1, stroke=0)

# Main flow
box(pdf, 42, 250, 128, 105, "Browser UI", "Chat and document ingest\nSource citations\nResponsive static frontend", NAVY, GREEN)
pdf.setFillColor(GREEN)
pdf.setFont("Helvetica-Bold", 11)
pdf.drawString(54, 316, "USER")
pdf.setFillColor(WHITE)

box(pdf, 215, 250, 145, 125, "FastAPI API", "Async request handling\nJSON schemas\nRate limiting\nMetrics and health\nResponse cache", WHITE, GREEN)
box(pdf, 410, 265, 150, 125, "AgentRunner", "Single-agent loop\nModel chooses next action\nMax 4 steps\nCompacted context", WHITE, GREEN)
box(pdf, 410, 120, 150, 95, "LLM provider", "OpenAI-compatible API\nStructured JSON decisions\n3 attempts + backoff\nToken usage returned", WHITE, GREEN)
box(pdf, 615, 390, 145, 75, "RAG search", "Capped top results\nSource de-duplication", WHITE, GREEN)
box(pdf, 615, 295, 145, 75, "External tools", "Safe arithmetic\nUTC time\nBounded tool calls", WHITE, GREEN)
box(pdf, 615, 200, 145, 75, "Clarification", "Terminal action when\nrequired details are missing", WHITE, GREEN)
box(pdf, 615, 105, 145, 75, "Fallback", "Controlled degraded answer\nwhen provider is unavailable", WHITE, colors.HexColor("#D7A84C"))
box(pdf, 815, 230, 125, 145, "Serving", "Hosted provider\nor\nlocal vLLM\nOpenAI-compatible endpoint", NAVY, GREEN)
pdf.setFillColor(WHITE)
pdf.setFont("Helvetica-Bold", 11)
pdf.drawCentredString(877, 320, "DEPLOY")

arrow(pdf, 170, 302, 215, 302, "HTTP")
arrow(pdf, 360, 330, 410, 330, "request")
arrow(pdf, 560, 350, 615, 425, "search")
arrow(pdf, 560, 315, 615, 332, "tool")
arrow(pdf, 560, 280, 615, 237, "clarify")
arrow(pdf, 485, 265, 485, 215, "decide")
arrow(pdf, 560, 165, 615, 142, "failure")
arrow(pdf, 760, 425, 815, 340, "provider")
arrow(pdf, 760, 142, 815, 270, "fallback")

# Ingestion path
box(pdf, 215, 105, 145, 72, "Ingestion", "POST /ingest\nTitle + content\nChunk and index", WHITE, GREEN)
box(pdf, 410, 30, 150, 65, "Evaluation", "Task completion\nTool correctness\nTrajectory + tokens", WHITE, GREEN)
arrow(pdf, 170, 255, 215, 141, "document")
arrow(pdf, 360, 141, 615, 425, "store")
arrow(pdf, 485, 265, 485, 95, "trace")

# Footer
pdf.setFillColor(MUTED)
pdf.setFont("Helvetica", 8)
pdf.drawString(42, 12, "Production note: replace the in-memory vector store with pgvector, Qdrant, or Pinecone for persistence and scale.")
pdf.drawRightString(WIDTH - 42, 12, "ContextPilot W16 v1.1")
pdf.save()
print(OUTPUT)
