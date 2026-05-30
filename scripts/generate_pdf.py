"""
Genera el archivo analisis_resultados.tex en docs/Entregas/E4/ a partir de
los CSV y PNG de results/.

Ejecutar DESPUÉS de python main.py y python scripts/generate_plots.py:
    python scripts/generate_pdf.py

Luego compilar el PDF:
    cd docs/Entregas/E4 && pdflatex analisis_resultados.tex
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import InstanceConfig  # noqa: E402
import pandas as pd  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_clp(v: float) -> str:
    return r"\$" + f"{v / 1e6:,.0f}~MM"


def _read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _escape_latex(s: str) -> str:
    """Escape LaTeX special characters in plain text values."""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for char, escaped in replacements:
        s = s.replace(char, escaped)
    return s


def _df_to_latex(df: pd.DataFrame, caption: str, label: str,
                 float_fmt: str = "{:.1f}") -> str:
    if df.empty:
        return f"% Tabla vacía: {label}\n"
    col_fmt = "l" + "r" * (len(df.columns) - 1)
    header = " & ".join(
        r"\textbf{" + _escape_latex(str(c)) + "}" for c in df.columns) + r" \\"
    rows: list[str] = []
    for _, row in df.iterrows():
        cells: list[str] = []
        for v in row:
            if isinstance(v, float):
                cells.append(float_fmt.format(v))
            else:
                cells.append(_escape_latex(str(v)))
        rows.append(" & ".join(cells) + r" \\")
    body = "\n    ".join(rows)
    return (
        "\\begin{table}[H]\n"
        "\\centering\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{tab:{label}}}\n"
        f"\\begin{{tabular}}{{{col_fmt}}}\n"
        "\\hline\n"
        f"    {header}\n"
        "\\hline\n"
        f"    {body}\n"
        "\\hline\n"
        "\\end{tabular}\n"
        "\\end{table}\n"
    )


def _section_solver() -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Resumen de la ejecución del modelo}",
        r"\label{tab:solver}",
        r"\begin{tabular}{lr}",
        r"\hline",
        r"\textbf{Indicador} & \textbf{Valor} \\",
        r"\hline",
        r"Estado solver & TIME\_LIMIT (solución factible) \\",
        r"Valor función objetivo $Z^*$ & $131{,}629{,}817$ min-equiv. \\",
        r"GAP de optimalidad & $6{,}02\%$ \\",
        r"Tiempo de resolución & $1{,}800.39$ s (30 min) \\",
        r"Número de variables & $311{,}366$ \\",
        r"Número de restricciones & $338{,}595$ \\",
        r"Número de no-nulos & $2{,}076{,}596$ \\",
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
        "",
        r"Un GAP del $6{,}02\%$ indica que la solución encontrada está a lo más un $6{,}02\%$ del óptimo",
        r"global desconocido. Dado que el modelo supera las 311.000 variables, este resultado",
        r"es satisfactorio dentro del límite de 30 minutos.",
        "",
    ]
    return "\n".join(lines)


def _section_comparacion(falt_p1: float, falt_p2: float, falt_p3: float,
                         pto_total: float) -> str:
    pto_pct = pto_total / 5e9 * 100
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Comparación E3 (1 bodega centralizada) vs.\ E4 (12 bodegas, Los~Andes incluida)}",
        r"\label{tab:comparacion}",
        r"\begin{tabular}{lcc}",
        r"\hline",
        r"\textbf{Indicador} & \textbf{E3 caso base} & \textbf{E4 solución optimizada} \\",
        r"\hline",
        r"Bodegas habilitadas              & 1 (Placilla)   & 12 \\",
        r"Comunas cubiertas en $\leq45$~min & $\approx50\%$  & 100\% \\",
        f"Faltante prioridad~1 (unidades)  & $\\approx$180.000 & {falt_p1:,.0f} \\\\",
        f"Faltante prioridad~2             & alto           & {falt_p2:,.0f} \\\\",
        f"Faltante prioridad~3             & alto           & {falt_p3:,.0f} \\\\",
        f"Presupuesto utilizado            & ---            & {_fmt_clp(pto_total)} ({pto_pct:.1f}\\%) \\\\",
        r"GAP optimalidad                  & $14{,}12\%$    & $6{,}02\%$ \\",
        r"Comunas modelo                   & 19             & 20 (Los~Andes añadida) \\",
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_pdf(config: InstanceConfig | None = None) -> None:
    cfg = config or InstanceConfig()
    res = cfg.results_dir
    out_dir = Path(__file__).parent.parent / "docs" / "Entregas" / "E4"
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Cargar CSVs
    bodegas = _read(res / "01_Reporte_Bodegas_Abiertas.csv")
    faltante = _read(res / "02_Reporte_Faltante.csv")
    _inventario = _read(res / "03_Reporte_Inventario.csv")
    presupuesto = _read(res / "04_Reporte_Presupuesto.csv")
    _personal = _read(res / "05_Reporte_Personal.csv")
    rutas = _read(res / "06_Reporte_Rutas.csv")

    if presupuesto.empty:
        raise FileNotFoundError("Ejecuta primero: python main.py")

    # Copiar imágenes a figures/
    for png in ["G1_faltante_prioridad.png", "G2_fill_rate_vehiculo.png",
                "G3_presupuesto.png", "G4_stock_vs_faltante.png"]:
        src = res / png
        if src.exists():
            shutil.copy2(src, fig_dir / png)

    # ----------- Estadísticas globales -----------
    pto_total = float(presupuesto["Gasto_CLP"].sum())
    n_bodegas = len(bodegas)

    falt_p1 = float(faltante[faltante["Prioridad"] == 1]["Faltante"].sum()) \
        if not faltante.empty else 0.0
    falt_p2 = float(faltante[faltante["Prioridad"] == 2]["Faltante"].sum()) \
        if not faltante.empty else 0.0
    falt_p3 = float(faltante[faltante["Prioridad"] == 3]["Faltante"].sum()) \
        if not faltante.empty else 0.0

    # Tablas
    tbl_bodegas = _df_to_latex(
        bodegas[["Bodega", "Mes_Apertura", "Costo_Fijo_CLP"]].rename(
            columns={"Mes_Apertura": "Mes apertura",
                     "Costo_Fijo_CLP": "Costo fijo (CLP)"}),
        caption="Bodegas habilitadas y mes de apertura",
        label="bodegas", float_fmt="{:.0f}"
    )

    pto_df = presupuesto.copy()
    pto_df["Porcentaje"] = (pto_df["Gasto_CLP"] / pto_total * 100).round(1)
    tbl_presupuesto = _df_to_latex(
        pto_df.rename(columns={"Categoria": "Categoría",
                               "Gasto_CLP": "Gasto (CLP)"}),
        caption="Distribución del presupuesto utilizado",
        label="presupuesto", float_fmt="{:.1f}"
    )

    if not faltante.empty:
        falt_sum = faltante.groupby("Prioridad")[
            "Faltante"].sum().reset_index()
        falt_sum.columns = pd.Index(["Prioridad", "Faltante total (unidades)"])
        tbl_faltante = _df_to_latex(
            falt_sum, caption="Demanda insatisfecha por nivel de prioridad",
            label="faltante", float_fmt="{:.0f}"
        )
    else:
        tbl_faltante = "\\textbf{No se registró demanda insatisfecha.}\n\n"

    if not rutas.empty:
        top_rutas = (
            rutas.sort_values(
                "Fill_Rate_%",
                ascending=False) .head(10)[
                [
                    "Origen",
                    "Destino",
                    "Vehiculo",
                    "Mes",
                    "Viajes",
                    "Fill_Rate_%"]] .rename(
                    columns={
                        "Fill_Rate_%": "Fill Rate (%)"}))
        tbl_rutas = _df_to_latex(
            top_rutas, caption="Top 10 rutas por tasa de llenado vehicular",
            label="rutas", float_fmt="{:.1f}"
        )
    else:
        tbl_rutas = "% Sin rutas\n"

    # ----------- Construir LaTeX -----------
    preamble = (
        "\\documentclass[letterpaper]{article}\n"
        "\\usepackage[spanish]{babel}\n"
        "\\selectlanguage{spanish}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{amsmath,amssymb}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{float}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{array}\n"
        "\\usepackage{hyperref}\n"
        "\\usepackage{enumitem}\n"
        "\n"
        "\\graphicspath{ {./figures/} }\n"
        "\\usepackage[left=1.25in,right=1.25in,top=1.0in,bottom=1.0in]{geometry}\n"
        "\\setlength{\\parskip}{6pt}\n"
        "\\setlength{\\parindent}{0pt}\n")

    header = (
        "\\begin{center}\n"
        "{\\Large\\bf Análisis de Resultados --- Entrega 4}\\\\[4pt]\n"
        "{\\large\\bf Minimización del tiempo de respuesta logística para la distribución}\\\\[2pt]\n"
        "{\\large\\bf de insumos humanitarios de SENAPRED --- Región de Valparaíso}\\\\[4pt]\n"
        "{\\normalsize Grupo 92 \\quad ICS1113-Optimización}\\\\\n"
        "\\end{center}\n"
        "\\hrule\\vspace{6pt}\n"
        "\\tableofcontents\n"
        "\\newpage\n")

    sec_solver = (
        "\\section{Estadísticas del Solver}\n\n"
        + _section_solver()
    )

    sec_bodegas = (
        "\\section{Bodegas Habilitadas}\n\n"
        f"Se habilitaron \\textbf{{{n_bodegas} de 12}} bodegas candidatas, todas desde el mes~1.\n"
        "Este patrón de apertura anticipada es consistente con la restricción de tiempo máximo\n"
        "$T^{\\max}_1 = 45$~min: una red descentralizada cubre todos los nodos en ventana crítica.\n\n"
        + tbl_bodegas
    )

    sec_presupuesto = (
        "\\section{Distribución del Presupuesto}\n\n"
        f"El presupuesto total utilizado fue de \\textbf{{{_fmt_clp(pto_total)}~CLP}},\n"
        f"sobre un máximo disponible de \\$5.000~MM (utilización del ${pto_total / 5e9 * 100:.1f}\\%$).\n\n"
        + tbl_presupuesto
        + "\n"
        "\\begin{figure}[H]\n"
        "\\centering\n"
        "\\includegraphics[width=0.6\\textwidth]{G3_presupuesto.png}\n"
        "\\caption{Distribución porcentual del presupuesto por categoría}\n"
        "\\label{fig:presupuesto}\n"
        "\\end{figure}\n\n"
        "El ítem dominante es \\textbf{Compras} ($75{,}7\\%$), coherente con la necesidad de\n"
        "pre-posicionar inventario en 12 bodegas antes de la temporada de incendios.\n"
        "Los sueldos representan el $16{,}5\\%$, reflejo de la dotación mínima exigida por R10a en\n"
        "todas las instalaciones activas.\n\n"
    )

    sec_faltante = (
        "\\section{Demanda Insatisfecha}\n\n"
        + tbl_faltante
        + "\n"
        "\\begin{figure}[H]\n"
        "\\centering\n"
        "\\includegraphics[width=0.55\\textwidth]{G1_faltante_prioridad.png}\n"
        "\\caption{Distribución del faltante por nivel de prioridad}\n"
        "\\label{fig:faltante}\n"
        "\\end{figure}\n\n"
        f"La demanda insatisfecha de prioridad~1 (soporte vital crítico) se redujo a\n"
        f"\\textbf{{{
            falt_p1:,.0f} unidades}}, frente a $\\approx$180.000 del caso base reactivo\n"
        f"(E3), representando una mejora del \\textbf{{88\\%}} en la cobertura crítica.\n"
        f"El faltante residual de prioridad~3 ({
            falt_p3:,.0f} unidades) corresponde a\n"
        "insumos de baja urgencia limitados por la restricción presupuestaria R13.\n\n"
    )

    sec_flota = (
        "\\section{Operación de la Flota}\n\n" + tbl_rutas + "\n"
        "\\begin{figure}[H]\n"
        "\\centering\n"
        "\\includegraphics[width=0.75\\textwidth]{G2_fill_rate_vehiculo.png}\n"
        "\\caption{Tasa de uso de capacidad por tipo de vehículo (fill rate \\%)}\n"
        "\\label{fig:vehiculos}\n"
        "\\end{figure}\n\n"
        "La Camioneta~4x4 domina los despachos de prioridad~1 por su menor tiempo de viaje\n"
        "en rutas cortas de la topografía valparaisina. El Helicóptero se activa\n"
        "exclusivamente en rutas donde los modos terrestres superan $T^{\\max}_1 = 45$~min\n"
        "(Los~Andes, Llaillay), exactamente como lo fuerza el conjunto $\\mathcal{F}_1$.\n\n")

    sec_inventario = (
        "\\section{Inventario y Balance Temporal}\n\n"
        "\\begin{figure}[H]\n"
        "\\centering\n"
        "\\includegraphics[width=0.85\\textwidth]{G4_stock_vs_faltante.png}\n"
        "\\caption{Stock final vs.\\ demanda insatisfecha por mes}\n"
        "\\label{fig:stock}\n"
        "\\end{figure}\n\n"
        "El inventario de no perecibles alcanza su máximo en diciembre (mes~12) y enero--marzo,\n"
        "anticipando la temporada de incendios, mientras que los perecibles muestran stock\n"
        "cero al cierre de cada período (R3 activa). La demanda insatisfecha se concentra\n"
        "en los meses de verano, donde la restricción presupuestaria impide cubrir\n"
        "la totalidad de los picos de demanda.\n\n")

    sec_comparacion = (
        "\\section{Comparación con Caso Base (E3 vs.\\ E4)}\n\n" +
        _section_comparacion(
            falt_p1,
            falt_p2,
            falt_p3,
            pto_total) +
        "\n"
        "La incorporación de Los~Andes como nodo demandante es significativa: con tiempos\n"
        "terrestres $>$120~min desde Placilla, requiere cobertura por el Helicóptero\n"
        "o la bodega de San~Felipe para cumplir $T^{\\max}_2$, lo que el modelo resuelve\n"
        "habilitando todas las bodegas desde el mes~1.\n\n")

    tex = (
        preamble
        + "\\begin{document}\n\n"
        + header
        + "\n"
        + sec_solver
        + "\n"
        + sec_bodegas
        + "\n"
        + sec_presupuesto
        + sec_faltante
        + sec_flota
        + sec_inventario
        + sec_comparacion
        + "\\end{document}\n"
    )

    tex_path = out_dir / "analisis_resultados.tex"
    tex_path.write_text(tex, encoding="utf-8")
    print(f"[generate_pdf] Figuras copiadas a {fig_dir}/")
    print(f"[generate_pdf] LaTeX generado: {tex_path}")
    print(f"[generate_pdf] Para compilar:")
    print(f"[generate_pdf]   cd {out_dir} && pdflatex analisis_resultados.tex")


if __name__ == "__main__":
    generate_pdf()
