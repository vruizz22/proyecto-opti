# SENAPRED — Optimización Logística Humanitaria (E4)

> **Para el ayudante:** ejecutar `python main.py` desde la raíz del proyecto. Genera datos (si no existen), resuelve el modelo y escribe los 6 reportes CSV en `results/`. Solo requiere `gurobipy`, `pandas` y `numpy`.

---

# Disaster Risk Management: Inventory Pre-positioning (SENAPRED)

---

## Cómo ejecutar

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

> El ayudante solo necesita `gurobipy`, `pandas` y `numpy`.

### 2. Ejecutar el modelo (para el ayudante)

```bash
python main.py
```

El script es completamente autónomo:

1. Si los CSV en `data/` no existen, los genera con semilla fija 1113 (reproducible). Si ya existen, los reutiliza.
2. Construye el modelo Gurobi con las restricciones R1–R14 (ver `core/model_builder.py`).
3. Resuelve con TimeLimit=1800 s.
4. Imprime resumen en consola.
5. Escribe 6 CSV en `results/`.

**Requisito:** Gurobi con licencia WLS activa (credenciales en `core/config.py`).

### 3. Generar gráficos (opcional, requiere matplotlib)

```bash
python scripts/generate_plots.py
```

Genera 4 PNG en `results/` a partir de los CSV ya producidos.

### 4. Ejecutar tests de integración (opcional)

```bash
pytest test/test_model.py -v
```

Los tests verifican:

- Factibilidad del solver (OPTIMAL o TIME\_LIMIT con incumbente) y GAP < 15 %
- Restricciones R1, R2, R3, R5, R13 satisfechas numéricamente en la solución
- Calidad E4: 12/12 bodegas abiertas, P1 faltante < 500 u, triage P3 > P2 > P1
- Costo de bodegaje > 0 (R9 activo) y los 6 reportes CSV no vacíos

> **Tiempo estimado: ~2 minutos.** El fixture usa `TimeLimit=120 s` (no el límite de producción de 1800 s), suficiente para obtener una solución incumbente válida. Para omitir además los tests que iteran todas las claves dispersas y reducir a <30 s:
> ```bash
> pytest test/test_model.py -v -k "not demand_coverage and not inventory_balance and not vehicle_capacity"
> ```

### 5. Compilar PDF de análisis de resultados

Copia los PNG de `results/` a `docs/Entregas/E4/figures/` y compila:

```bash
cp results/G*.png docs/Entregas/E4/figures/
cd docs/Entregas/E4 && pdflatex analisis_resultados.tex
```

El `.tex` en `docs/Entregas/E4/analisis_resultados.tex` es el documento estático de análisis.
Para subir a Overleaf: incluir el `.tex` y la carpeta `figures/` con los PNG.

---

## Salidas generadas en `results/`

| Archivo | Descripción |
|---------|-------------|
| `01_Reporte_Bodegas_Abiertas.csv` | Bodegas habilitadas y mes de apertura |
| `02_Reporte_Faltante.csv` | Demanda insatisfecha por prioridad |
| `03_Reporte_Inventario.csv` | Stock y compras por bodega/mes |
| `04_Reporte_Presupuesto.csv` | Desglose de gasto por categoría |
| `05_Reporte_Personal.csv` | Dotación y saturación de cuadrillas |
| `06_Reporte_Rutas.csv` | Viajes y fill rate por ruta/vehículo |
| `G1–G4.png` | Gráficos de análisis (generados con `generate_plots.py`) |

---

This repository contains the development of the semester project for the **Optimization (ICS1113)** course at **Pontificia Universidad Católica de Chile (2026-1)**.

The project solves a real-world decision-making problem under the *IPCh (Engineering for Chile)* seal, addressing logistical preparedness for natural disasters using mathematical models solved with the Python + Gurobi interface.

---

## 📖 Problem Description

Chile is highly exposed to natural hazards, such as earthquakes and wildfires. Recalling the tragic 2024 summer season in Valparaíso (which consumed over 11,300 hectares and left thousands affected), the need to shift from reactive logistics to **evidence-based preventive planning** becomes evident.

This project aims to support **SENAPRED** (National Disaster Prevention and Response Service), formulating a strategy with a **1-year planning horizon**.

**Objective:**
Maximize coverage of the vulnerable population and drastically reduce relief delivery times during an emergency by establishing:

1. The strategic location of critical temporary facilities (relief centers).
2. The exact amount of supplies (water, food, tools) to pre-position before an emergency occurs.

---

## 🗂️ Project Architecture

The repository structure is designed following Data Engineering and Operations Research standards, making it easy to read and visually integrate with tools like *Material Icon Theme* in VS Code:

```bash
proyecto-opti/
│
├── core/                  # Core mathematical logic and optimization engine (Gurobi)
│   ├── solver.py          # Class that instantiates and executes the model
│   └── modelo.ilp         # Generated files for infeasibility debugging
│
├── data/                  # Database and model parameters
│
├── scripts/               # Support scripts and data preprocessing
│
├── views/                 # Results visualization and maps
│
├── docs/                  # Technical documents and deliverables (LaTeX)
│   └── Entregas/          # .tex files and PDF reports
│
├── test/                  # Integration tests and small instances (Unit testing)
│
├── requirements.txt       # Python dependencies (gurobipy, pandas, folium, etc.)
├── .gitignore             # Rules to exclude temporary files and environments
└── README.md              # Main project documentation
```

---

## 📐 Mathematical Model

The problem is addressed through a Mixed-Integer Linear Programming (MILP) model. Its main components are summarized below:

### 1. Sets

* $I$: Set of candidate locations to enable temporary relief centers, indexed by $i$.
* $J$: Set of affected zones (demand nodes) during the emergency, indexed by $j$.

### 2. Parameters

* $D_j$: Projected demand in the affected zone $j$.
* $C_i$: Maximum storage capacity of the candidate facility $i$.
* $F_i$: Fixed cost for opening and operational implementation of facility $i$.
* $V$: Unit variable cost to acquire and pre-position a kit in a warehouse.
* $T_{ij}$: Travel time or logistics cost to send relief from $i$ to $j$.
* $B$: Total national budget available for the preparation phase.

### 3. Decision Variables

* $y_i \in \{0,1\}$: 1 if facility $i$ is opened, 0 otherwise.
* $s_i \geq 0$: Amount of pre-positioned inventory at facility $i$.
* $x_{ij} \geq 0$: Amount of inventory dispatched from $i$ to $j$ during an emergency.

### 4. Main Constraints

1. **Demand Satisfaction**: All inventory dispatched from active centers to a zone $j$ must meet its demand $D_j$.
2. **Flow Conservation / Availability**: The total $x_{ij}$ leaving warehouse $i$ cannot exceed the pre-positioned stock $s_i$.
3. **Capacity and Logical Relationship**: The pre-positioned inventory $s_i$ is bounded by $C_i \cdot y_i$. If $y_i = 0$, the inventory must be 0.
4. **Budget**: The sum of fixed operational costs ($F_i \cdot y_i$) and acquisition costs ($V \cdot s_i$) must be $\leq B$.

---

## ⚙️ Technologies Used

* **Language:** [Python 3.10+](https://www.python.org/)
* **Main Libraries:** pandas, numpy, geopandas
* **Optimization Solver:** [Gurobi Optimizer](https://www.gurobi.com/) (via gurobipy)
* **Documentation:** LaTeX

## 📚 Main References

* SENAPRED (2024). *Visor Chile Preparado y Planes de Reducción del Riesgo de Desastres*.
* Ministry of Social Development and Family. (2024). *Reconstruction Plan: February 2024 Fires, Valparaíso Region.*
* CONAF (2024). *Forest Fire Protection Program.*
