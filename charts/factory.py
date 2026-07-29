"""
Usine à graphiques Plotly — composants réutilisables.
"""
import plotly.express as px
import plotly.graph_objects as go
from data.config import C

# Layout de base appliqué à tous les graphiques
_BASE = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="white",
    font=dict(family="DM Sans, Figtree, sans-serif", color=C["ink"], size=13),
    margin=dict(l=16, r=16, t=52, b=16),
    title=dict(font=dict(size=15, color=C["ink"])),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="center", x=0.5, font=dict(size=12),
    ),
)


def _base(fig: go.Figure, h: int = 380) -> go.Figure:
    """Applique le layout de base à une figure."""
    fig.update_layout(**_BASE, height=h)
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.13)", zeroline=False, tickfont=dict(size=11))
    return fig


def _empty(title: str, h: int = 380) -> go.Figure:
    """Figure vide avec message 'Aucune donnée disponible'."""
    fig = go.Figure()
    fig.add_annotation(
        text="Aucune donnée disponible",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(color=C["muted"], size=14),
    )
    return _base(fig, h)


def chart_bar(df, x: str, y: str, title: str,
              color: str = None, h: int = 380, orientation: str = "v") -> go.Figure:
    """Bar chart vertical ou horizontal avec labels automatiques."""
    color = color or C["blue"]
    if df is None or df.empty:
        return _empty(title, h)
    if orientation == "h":
        fig = px.bar(df, x=x, y=y, orientation="h", title=title,
                     color_discrete_sequence=[color], text_auto=".3s")
        fig.update_layout(yaxis=dict(autorange="reversed"))
    else:
        fig = px.bar(df, x=x, y=y, title=title,
                     color_discrete_sequence=[color], text_auto=".3s")
    fig.update_traces(textposition="outside", textfont_size=10, cliponaxis=False)
    return _base(fig, h)


def chart_grouped_bar(df, x: str, y_n: str, y_n1: str,
                      title: str, annee_n: int, h: int = 380) -> go.Figure:
    """Barres groupées N vs N-1 avec couleurs sémantiques."""
    if df is None or df.empty:
        return _empty(title, h)
    fig = go.Figure([
        go.Bar(
            x=df[x], y=df[y_n1], name=str(annee_n - 1),
            marker_color=C["slate"],
            text=[f"{v/1e3:.1f}k" for v in df[y_n1]],
            textposition="outside", textfont_size=9,
        ),
        go.Bar(
            x=df[x], y=df[y_n], name=str(annee_n),
            marker_color=C["blue"],
            text=[f"{v/1e3:.1f}k" for v in df[y_n]],
            textposition="outside", textfont_size=9,
        ),
    ])
    fig.update_layout(barmode="group", title=title)
    return _base(fig, h)


def chart_line_compare(df, x: str, y_n: str, y_n1: str,
                       title: str, annee_n: int, h: int = 380) -> go.Figure:
    """Courbes N vs N-1 avec fill sous N."""
    if df is None or df.empty:
        return _empty(title, h)
    fig = go.Figure([
        go.Scatter(
            x=df[x], y=df[y_n1], name=str(annee_n - 1),
            mode="lines+markers",
            line=dict(color=C["slate"], width=2, dash="dot"),
            marker=dict(size=5),
        ),
        go.Scatter(
            x=df[x], y=df[y_n], name=str(annee_n),
            mode="lines+markers",
            line=dict(color=C["blue"], width=3),
            marker=dict(size=8, color=C["blue"]),
            fill="tonexty",
            fillcolor="rgba(29,78,216,0.06)",
        ),
    ])
    fig.update_layout(title=title)
    return _base(fig, h)


def chart_variation_bar(df, cat_col: str, var_col: str,
                        title: str, h: int = 380) -> go.Figure:
    """Barres horizontales colorées vert/rouge par signe de la variation."""
    if df is None or df.empty:
        return _empty(title, h)
    df = df.copy().sort_values(var_col)
    colors = [C["green"] if v >= 0 else C["red"] for v in df[var_col]]
    labels = [f"{v:+.1f}%" for v in df[var_col]]
    fig = go.Figure(go.Bar(
        x=df[var_col], y=df[cat_col], orientation="h",
        marker_color=colors,
        text=labels, textposition="outside", textfont_size=10,
    ))
    fig.add_vline(x=0, line_color=C["muted"], line_width=1)
    fig.update_layout(title=title, xaxis_title="Évolution %")
    return _base(fig, h)


def chart_waterfall(df_years, year_col: str, val_col: str,
                    title: str, h: int = 380) -> go.Figure:
    """Waterfall CA par année — montre l'évolution cumulée."""
    if df_years is None or df_years.empty:
        return _empty(title, h)
    df_sorted = df_years.sort_values(year_col)
    years = df_sorted[year_col].astype(str).tolist()
    vals = df_sorted[val_col].tolist()
    if not vals or len(vals) < 1:
        return _empty(title, h)
    deltas = [vals[0]] + [vals[i] - vals[i - 1] for i in range(1, len(vals))]
    measure = ["absolute"] + ["relative"] * (len(deltas) - 1)
    texts = [f"{v/1e3:.0f}k" for v in deltas]
    fig = go.Figure(go.Waterfall(
        orientation="v", x=years, y=deltas, measure=measure,
        connector=dict(line=dict(color=C["muted"], width=1, dash="dot")),
        increasing=dict(marker_color=C["green"]),
        decreasing=dict(marker_color=C["red"]),
        totals=dict(marker_color=C["blue"]),
        textposition="outside", text=texts,
    ))
    fig.update_layout(title=title, showlegend=False)
    return _base(fig, h)


def chart_risk_table(df, annee_n: int, title: str, h: int = 480) -> go.Figure:
    """Tableau condensé risque / opportunité — simplifié pour directeurs."""
    if df is None or df.empty:
        return _empty(title, h)
    df_disp = df.head(20).copy()

    def get_indicateur(statut):
        if "Croissance" in statut or "Nouveau" in statut:
            return "✅"
        elif "Déclin fort" in statut or "Inactif" in statut:
            return "🔴"
        elif "Déclin" in statut:
            return "🟡"
        else:
            return "⚫"

    df_disp["Statut"] = df_disp["Statut"].apply(get_indicateur)
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[
                "<b>Convention</b>",
                "<b>CA " + str(annee_n) + "</b>",
                "<b>CA " + str(annee_n - 1) + "</b>",
                "<b>Évolution</b>", "<b>Statut</b>",
            ],
            fill_color=C["blue"],
            font=dict(color="white", size=12),
            align="left",
            height=35,
        ),
        cells=dict(
            values=[
                df_disp["Nom"].astype(str),
                df_disp["CA N"].apply(lambda x: f"{x:,.0f}"),
                df_disp["CA N-1"].apply(lambda x: f"{x:,.0f}"),
                df_disp["Évolution %"].apply(lambda x: f"{x:+.1f}%"),
                df_disp["Statut"],
            ],
            fill_color=[[C["surface"]] * len(df_disp)],
            font=dict(size=11),
            align="left",
            height=30,
        ),
    )])
    fig.update_layout(title=title, height=h, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def chart_gauge(value: float, ref: float, title: str, h: int = 260) -> go.Figure:
    """Jauge d'atteinte CA N vs N-1."""
    pct = min(max((value / ref * 100) if ref > 0 else 0, 0), 150)
    color = C["green"] if pct >= 100 else (C["amber"] if pct >= 70 else C["red"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        delta=dict(reference=ref, relative=True, valueformat=".1%"),
        title=dict(text=title, font=dict(size=13)),
        gauge=dict(
            axis=dict(range=[0, ref * 1.5], tickformat=",.0f"),
            bar=dict(color=color, thickness=0.28),
            bgcolor="white",
            borderwidth=0,
            steps=[
                dict(range=[0, ref * 0.7], color="rgba(220,38,38,0.06)"),
                dict(range=[ref * 0.7, ref], color="rgba(217,119,6,0.06)"),
                dict(range=[ref, ref * 1.5], color="rgba(5,150,105,0.08)"),
            ],
            threshold=dict(
                line=dict(color=C["muted"], width=2),
                thickness=0.8, value=ref,
            ),
        ),
        number=dict(suffix=" TND", valueformat=",.0f"),
    ))
    fig.update_layout(template="plotly_white", height=h, margin=dict(l=20, r=20, t=40, b=10))
    return fig


def chart_pie(values, names, title: str, h: int = 340) -> go.Figure:
    """Camembert avec palette sémantique."""
    fig = px.pie(
        values=values, names=names, title=title, hole=0.42,
        color_discrete_sequence=[C["blue"], C["green"], C["amber"], C["purple"]],
    )
    fig.update_traces(textinfo="percent+label", textfont_size=12, pull=[0.04] * len(values))
    return _base(fig, h)


def chart_inactive_bar(df, title: str, h: int = 380) -> go.Figure:
    """Barres horizontales d'inactivité, dégradé amber→rouge selon l'ancienneté."""
    if df is None or df.empty:
        return _empty(title, h)
    df = df.copy().head(20)
    colors = df["Jours inactifs"].apply(
        lambda d: C["red"] if d > 90 else (C["amber"] if d > 60 else "#F97316")
    ).tolist()
    fig = go.Figure(go.Bar(
        x=df["Jours inactifs"], y=df["Convention"],
        orientation="h",
        marker_color=colors,
        text=[f"{d}j" for d in df["Jours inactifs"]],
        textposition="outside", textfont_size=10,
    ))
    fig.update_layout(
        title=title,
        yaxis=dict(autorange="reversed"),
        xaxis_title="Jours sans facture",
    )
    return _base(fig, max(300, len(df) * 28))
