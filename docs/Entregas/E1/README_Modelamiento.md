# Explicación de Decisiones de Modelamiento Matemático - Entrega 1

En este documento se detallan y justifican las decisiones matemáticas tomadas para el modelo de optimización del proyecto para SENAPRED (Incendios de Valparaíso), alineadas explícitamente con las normativas y pautas de corrección del curso ICS1113. 

Estas decisiones buscan maximizar la eficiencia del solver (Gurobi), evitar variables o parámetros redundantes y asegurar la total factibilidad realista frente al desastre.

## 1. Eliminación del parámetro $P_{ij}$ (Distancia lineal)
**Razón de diseño:** En el modelamiento matemático riguroso, si se define un dato o parámetro (como la *distancia*), este debe ser utilizado obligatoriamente en alguna ecuación (función objetivo o restricciones). Previamente se había listado $P_{ij}$, pero la función objetivo y las restricciones evaluaban estrictamente el tiempo de respuesta ($T_{ijm}$). 
Al eliminar este parámetro "fantasma", el modelo se limpia, se vuelve compacto, se gana total aplicabilidad y se evitan penalizaciones directas según la **Condición 5** del enunciado del curso (uso ineficiente y redundante).

## 2. Naturaleza de la variable de flota $z_{ijm}$ (De Binaria a Entera $\mathbb{Z}^+_0$)
**Razón de diseño:** En la formulación inicial, $z_{ijm} \in \{0, 1\}$ significaba que, como máximo, por cada ruta, solo se podía enviar *un* solo vehículo. 
Dado el volumen de la catástrofe en Valparaíso, una sola ambulancia o camión hacia una zona grave carecería de la capacidad para cumplir la *restricción de satisfacción de demanda*. Esto generaría un modelo lógicamente **infactible**. Al redefinir la variable como entera positiva no negativa ($z_{ijm} \in \mathbb{Z}^+_0$), permitimos al modelo despachar múltiples vehículos del mismo tipo por la misma ruta (por ejemplo, enviar $z=5$ camiones aljibe), habilitando a Gurobi a sumar la capacidad total fluida ($A_m \cdot z_{ijm}$).

## 3. Inclusión de la Restricción de "Disponibilidad de Flota" ($\sum z_{ijm} \leq Q_m$)
**Razón de diseño:** Previamente se había declarado la existencia cuantitativa de vehículos $Q_m$ en los parámetros, pero la ecuación restrictiva estaba ausente. Matemáticamente, omitir esta restricción causaba que el algoritmo de optimización sumiera "flota de vehículos infinita". La añadidura de esta ecuación limita la cantidad de despachos totales según los recursos de transporte reales de la organización (SENAPRED), dándole un fuerte anclaje a la realidad.

## 4. Eficiencia Computacional: Vinculación Lógica de Apertura (Big-M) y Poda de $TMax$
**Razón de diseño:** Previamente se ocupaba la restricción polinómica $T_{ijm} \cdot z_{ijm} \leq TMax \cdot y_i$ para intentar vincular que un camión no salga desde un lugar cerrado, pero cruzando variables con ratios numéricos.
Para escalar a optimización experta se aplicaron dos mejoras:
1. **Pre-procesamiento (Poda Temprana de grafos):** En la instanciación de datos, evitamos darle a Gurobi millones de variables matemáticas imposibles. Las rutas ($x$ e $z$) **solo** se instancian si de base cumplen que $T_{ijm} \leq TMax$. Las que excedan eso, ni siquiera se crean.
2. **Vinculación Big-M:** Para garantizar que $z$ (despachos) solo ocurran si $y_i=1$ (la bodega de acopio abre), se introdujo $\sum z_{ijm} \leq M \cdot y_i$. 
   - Si la bodega no se construye ($y_i = 0$), el lado derecho es $0$ y Gurobi colapsa la variable $z=0$ (obligando al flujo a ser cero).
   - Si la bodega se habilita ($y_i = 1$), se enciende la constante "Big M" (que a nivel real de código puede igualarse al máximo de la flota) dejando que los vehículos operen con normalidad.