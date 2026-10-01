"""Single source of truth for the visual identity, taken from devinder-kaur.vercel.app.
Every chart and document in this project uses these tokens: brief, dashboard, exports."""

COLORS = {
    "navy": "#2F4156",      # text, primary data, "this week"
    "teal": "#567C8D",      # comparison, "previous week", secondary series
    "teal_ink": "#44697A",  # secondary text, labels
    "sky": "#C8D9E6",       # context bars, soft fills, highlights
    "beige": "#F5EFEB",     # page and chart background
    "white": "#FFFFFF",     # cards
    "rule": "#DCD3CC",      # hairlines, gridlines
}
SERIES = [COLORS["navy"], COLORS["teal"], COLORS["sky"], COLORS["teal_ink"], "#8FA9B8", "#1E2B3A"]

FONT_HEADING = "Playfair Display"
FONT_BODY = "PT Serif"
FONT_SCRIPT = "Pinyon Script"
GOOGLE_FONTS_URL = ("https://fonts.googleapis.com/css2?family=Pinyon+Script"
                    "&family=Playfair+Display:wght@400;500;600&family=PT+Serif:wght@400;700&display=swap")
STACK_HEADING = f'"{FONT_HEADING}", Georgia, "Times New Roman", serif'
STACK_BODY = f'"{FONT_BODY}", Georgia, "Times New Roman", serif'
STACK_SCRIPT = f'"{FONT_SCRIPT}", "Brush Script MT", cursive'


def plotly_template():
    """Plotly template matching the portfolio site. Use: fig.update_layout(template=plotly_template())"""
    import plotly.graph_objects as go

    return go.layout.Template(layout=dict(
        font=dict(family=STACK_BODY, color=COLORS["navy"], size=14),
        title=dict(font=dict(family=STACK_HEADING, size=20, color=COLORS["navy"]), x=0, xanchor="left"),
        paper_bgcolor=COLORS["beige"], plot_bgcolor=COLORS["beige"],
        colorway=SERIES,
        xaxis=dict(showgrid=False, linecolor=COLORS["rule"], tickcolor=COLORS["rule"],
                   tickfont=dict(color=COLORS["teal_ink"]), title=dict(font=dict(color=COLORS["teal_ink"]))),
        yaxis=dict(gridcolor=COLORS["rule"], zeroline=False, linecolor=COLORS["rule"],
                   tickfont=dict(color=COLORS["teal_ink"]), title=dict(font=dict(color=COLORS["teal_ink"]))),
        legend=dict(font=dict(color=COLORS["navy"]), bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.18),
        hoverlabel=dict(bgcolor=COLORS["navy"], font=dict(family=STACK_BODY, color=COLORS["white"])),
        margin=dict(l=40, r=20, t=56, b=40),
    ))


def highlight_colors(n: int, index: int) -> list:
    """One idea per figure: the bar that matters in navy, the rest in sky."""
    return [COLORS["navy"] if i == index else COLORS["sky"] for i in range(n)]
