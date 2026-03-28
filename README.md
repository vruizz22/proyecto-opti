# 🚨 Gestión del Riesgo de Desastres: Pre-posicionamiento de Inventarios (SENAPRED)

Este repositorio contiene el desarrollo del proyecto semestral para el curso **Optimización (ICS1113)** de la **Pontificia Universidad Católica de Chile (2026-1)**.

El proyecto resuelve un problema real de toma de decisiones bajo el sello *IPCh (Ingeniería Para Chile)*, abordando la preparación logística ante desastres naturales mediante modelos matemáticos resueltos con la interfaz Python + Gurobi.

---

## 📖 Descripción del Problema

Chile es un país altamente expuesto a riesgos naturales, como sismos e incendios forestales. Recordando la trágica temporada estival de 2024 en Valparaíso (donde se consumieron más de 11.300 hectáreas con miles de damnificados), se hace evidente la necesidad de pasar de una logística reactiva a una **planificación preventiva basada en evidencia**.

Este proyecto se posiciona en el horizonte de apoyo a **SENAPRED** (Servicio Nacional de Prevención y Respuesta ante Desastres), formulando una estrategia con **1 año de horizonte de planificación**.

**Objetivo:**
Maximizar la cobertura de la población vulnerable y reducir drásticamente los tiempos de traslado de ayuda en una emergencia estableciendo:

1. La ubicación estratégica de instalaciones críticas temporales (centros de acopio).
2. La cantidad exacta de sumistros (agua, alimentos, herramientas) a pre-posicionar antes de que ocurra la emergencia.

---

## 🗂️ Arquitectura del Proyecto

La estructura del repositorio está diseñada siguiendo el estándar de Ingeniería de Datos e Investigación de Operaciones, lo que facilita su lectura e integración visual con herramientas como *Material Icon Theme* en VS Code:

```bash
proyecto-opti/
│
├── core/                  # Lógica central matemática y motor de optimización (Gurobi)
│   ├── solver.py          # Clase que instancia y ejecuta el modelo
│   └── modelo.ilp         # Archivos generados para depuración de infactibilidad
│
├── data/                  # Base de datos y parámetros del modelo
│
├── scripts/               # Scripts de soporte y preprocesamiento
│
├── views/                 # Visualización de resultados y mapas
│
├── docs/                  # Documentes técnicos y entregas (LaTeX)
│   └── Entregas/          # Archivos .tex y PDFs con reportes
│
├── test/                  # Pruebas de integración e instancias pequeñas (Unit testing)
│
├── requirements.txt       # Dependencias de Python (gurobipy, pandas, folium, etc.)
├── .gitignore             # Reglas para excluir archivos temporales y entornos
└── README.md              # Documentación principal del proyecto
```

---

## 📐 Modelo Matemático

El problema se aborda a través de un modelo de optimización lineal y entero mixto. A continuación se resumen sus componentes principales:

### 1. Conjuntos

* $I$: Conjunto de ubicaciones candidatas para habilitar centros de acopio temporales, indexado por $i$.
* $J$: Conjunto de zonas afectadas (demandantes) durante la emergencia, indexado por $j$.

### 2. Parámetros

* $D_j$: Demanda proyectada en la zona afectada $j$.
* $C_i$: Capacidad máxima de almacenamiento de la instalación candidata $i$.
* $F_i$: Costo fijo por apertura e implementación operativa de la instalación $i$.
* $V$: Costo variable unitario por adquirir y pre-posicionar un kit en bodega.
* $T_{ij}$: Tiempo de viaje o costo logístico de enviar ayuda desde $i$ hasta $j$.
* $B$: Presupuesto estatal total disponible para la fase de preparación.

### 3. Variables de Decisión

* $y_i \in \{0,1\}$: 1 si se habilita la instalación $i$, 0 en caso contrario.
* $s_i \geq 0$: Cantidad de inventario pre-posicionado en la instalación $i$.
* $x_{ij} \geq 0$: Cantidad de inventario despachado desde $i$ hacia $j$ en emergencia.

### 4. Restricciones Principales

1. **Satisfacción de la Demanda**: Todo lo despachado desde los centros activos hacia una zona $j$ debe suplir su demanda $D_j$.
2. **Conservación de Flujo/Disponibilidad**: El total de $x_{ij}$ saliente de la bodega $i$ no puede superar el stock pre-posicionado $s_i$.
3. **Capacidad y Relación Lógica**: El inventario pre-posicionado $s_i$ está limitado por $C_i \cdot y_i$. Si $y_i = 0$, el inventario es 0.
4. **Presupuesto**: La suma de costos fijos operacionales ($F_i \cdot y_i$) y costos de adquisición ($V \cdot s_i$) debe ser $\leq B$.

---

## ⚙️ Tecnologías Utilizadas

* **Lenguaje:** [Python 3.10+](https://www.python.org/)
* **Librerías principales:** pandas,
umpy, geopandas
* **Solver de Optimización:** [Gurobi Optimizer](https://www.gurobi.com/) (vía gurobipy)
* **Documentación:** LaTeX

## 📚 Referencias Principales

* SENAPRED (2024). *Visor Chile Preparado y Planes de Reducción del Riesgo de Desastres*.
* Ministerio de Desarrollo Social y Familia. (2024). *Plan de Reconstrucción: Incendios de febrero de 2024, Región de Valparaíso.*
* CONAF (2024). *Programa de Protección Contra Incendios Forestales.*
