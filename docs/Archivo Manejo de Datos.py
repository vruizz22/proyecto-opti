import pandas as pd
from gurobipy import Model, GRB, quicksum

# Paso 1: Leer los datos de Excel usando pandas

# Creamos una lista con los nombres de las hojas del libro demanda

excel_file = "demanda.xlsx"
comunas = pd.ExcelFile(excel_file).sheet_names

# Creamos un dataframe con los datos de la primera hoja para los otros 2
# conjuntos

ejemplo = pd.read_excel(excel_file, sheet_name=comunas[0])
ejemplo.index += 1

frutas = ejemplo.columns.tolist()
dias = ejemplo.index.tolist()

# print(comunas)
# print(frutas)
# print(dias)

# Instanciamos el diccionario de demanda[i,j,t]

demanda = {}

for j in comunas:
    df = pd.read_excel(excel_file, sheet_name=j)
    df.index += 1  # Para que los índices de las filas empiecen en 1 y no en 0 y calcen con los de la lista dias
    for i in df.columns:
        for t in df.index:
            # La hoja j en la fila t y la columna i
            demanda[i, j, t] = df.loc[t, i]

# Nombre del libro y las hojas a trabajar

excel_file = "costos.xlsx"
prod = "produccion"
alma = "almacenamiento"

# Creamos los diccionarios de costos de producción y almacenamiento

produccion = {}
almacenamiento = {}

# index_col = 0 debido a que tiene nombres en las filas y no queremos que
# se tomen como datos

df = pd.read_excel(excel_file, sheet_name=prod, index_col=0)

for i in df.columns:
    for t in df.index:
        produccion[i, t] = df.loc[t, i]

df = pd.read_excel(excel_file, sheet_name=alma, index_col=0)

for i in df.columns:
    for t in df.index:
        almacenamiento[i, t] = df.loc[t, i]

# Paso 2: Crear el modelo y las variables

m = Model("Capsula")

# Variables enteras no negativas
x = {}
y = {}
z = {}


x = m.addVars(frutas, comunas, dias, vtype=GRB.INTEGER, name="x", lb=0)
y = m.addVars(frutas, dias, vtype=GRB.INTEGER, name="y", lb=0)

# Esta forma es análoga a la anterior, pero permite personalizar el nombre
# de las variables con format
for i in frutas:
    for t in dias:
        z[i, t] = m.addVar(vtype=GRB.INTEGER, name=f"z_{i}_{t}", lb=0)


m.update()

# Paso 3: Agregar las restricciones

# Utilizamos el diccionario ya creado para agregar las restricciones de demanda
m.addConstrs(x[i, j, t] >= demanda[i, j, t]
             for i in frutas for j in comunas for t in dias)

# Esta forma es análoga a la anterior, pero facilita restricciones con
# cambios según el valor del índice

for i in frutas:
    for t in dias:
        if t == 1:
            m.addConstr(z[i, t] == y[i, t] - quicksum(x[i, j, t]
                        for j in comunas))
        else:
            m.addConstr(z[i, t] == z[i, t - 1] + y[i, t] -
                        quicksum(x[i, j, t] for j in comunas))

Q = 10

m.addConstrs(quicksum(z[i, t] for i in frutas) <= Q for t in dias)

m.update()

# Paso 4: Agregar la función objetivo con los diccionarios de costos

m.setObjective(quicksum(produccion[i,
                                   t] * y[i,
                                          t] + almacenamiento[i,
                        t] * z[i,
                               t] for i in frutas for t in dias),
               GRB.MINIMIZE)

# Paso 5: Optimizar y mostrar variables no negativas

m.optimize()
m.printAttr("X")
