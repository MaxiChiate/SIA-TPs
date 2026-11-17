# Slides de TP4 (recuperatorio): referencia para la presentación

`Slides_TP4_G9 (recu).pdf` es la presentación de TP4 del Grupo 9 (38 slides). Quedó muy buena: se usa como modelo de
estructura y estilo para las slides de TP5. Este archivo resume cómo está armada y el contenido de cada slide (texto
sacado con `pdftotext`; los gráficos se describen, no se reproducen).

## Cómo está armada

- **El título es la conclusión, no el tema.** "k = 5 es la grilla más grande que cumple los dos límites de ocupación",
  no "Elección de k". Leyendo solo los títulos se entiende la historia del TP.
- **Una idea por slide.** Un gráfico o una tabla, y como mucho una línea de texto con los números clave debajo del
  título (por ejemplo, "Recuperación exacta con 3, 6 y 9 píxeles invertidos en el set separado: 99,7 %, 84,7 % y 32,3 %").
- **Poco texto.** Las explicaciones van en las notas del orador; en la slide quedan título y figura. Las listas de
  viñetas aparecen solo en slides de hiperparámetros o de conclusiones (3 a 5 viñetas cortas).
- **Separadores de sección** con fondo liso: "Ejercicio 1 / EDA, PCA y Kohonen", "Kohonen", "Regla de Oja",
  "Ejercicio 2 / Red de Hopfield", "Ejercicio QRs".
- **Tablas chicas** (4 a 8 filas) para hiperparámetros, criterios y comparaciones; la fila elegida resaltada.
- **Hiperparámetros en una slide propia** al empezar cada método, con cómo se actualizan (fórmula de η(t) y del radio).
- **Cada gráfico de estudio dice qué es cada punto** (por ejemplo, la media de 10 entrenamientos con distinta seed).
- **Se nombra lo que no funciona** y por qué ("Hebb recupera 0 % de los QR, ni siquiera sin ruido"), y después la
  solución.
- **Cierre por ejercicio** con las limitaciones medidas.
- Números con coma decimal; slides numeradas; portada con los integrantes y su legajo; última slide "Muchas gracias".

## Contenido slide por slide

| # | Título | Contenido |
|---|---|---|
| 1 | TP4 SIA — Grupo 9 | Subtítulo "Aprendizaje no supervisado y memoria asociativa"; integrantes y legajos |
| 2 | Ejercicio 1 | Separador: EDA, PCA y Kohonen |
| 3 | EDA | Estandarización con z-score; umbral \|r\| ≥ 0,8 para variables redundantes; lista de variables triviales |
| 4 | Matriz de correlaciones de las 26 variables restantes | Matriz de correlaciones con valores |
| 5 | Con 17 variables, 7 componentes pasan el 80 % | Tabla de autovalores, % de varianza y % acumulado de PC1 a PC17 |
| 6 | 7 componentes retienen 83,4 % de la varianza | Barras de autovalores y curva de varianza acumulada |
| 7 | PC1 (40,0 %) opone tamaño a guardados y comentarios; PC2 (11,7 %) sigue el patrocinio | Biplot PC1-PC2 coloreado por tema |
| 8 | Podar con \|r\| ≥ 0,80 deja 17 de 26 variables y PC1 baja a 40,0 % | Tabla de sensibilidad al umbral de correlación, fila 0,80 resaltada |
| 9 | Kohonen | Separador |
| 10 | Hiperparámetros del SOM | Viñetas: inicialización con muestras, límites de ocupación, R(0) = 2,5, η(0) = 0,5, 300 épocas |
| 11 | k = 5 es la grilla más grande que cumple los dos límites de ocupación | Tres paneles por k: error topográfico, % de neuronas vacías, creadores por neurona |
| 12 | Con η(0) entre 0,1 y 0,9 el mapa casi no cambia | Distancia a la neurona ganadora y U media contra η(0), con barras de error |
| 13 | Con R(0) entre 1,25 y 5 el mapa casi no cambia | Lo mismo contra R(0) |
| 14 | Las paredes altas de la matriz U separan perfiles por patrocinio, engagement y alcance | Creadores por neurona y matriz U |
| 15 | Fútbol arriba, arte en el centro, perros abajo y maquillaje a la derecha | Mapa coloreado por tema dominante |
| 16 | El mapa ordena a los creadores igual que PC1 y, en menor medida, PC2 | Planos de PC1 y PC2 sobre el mapa |
| 17 | Regla de Oja | Separador |
| 18 | Oja es una neurona lineal con una entrada por variable | Regla w ← w + η·y·(x − y·w), η(t) exponencial; tabla de hiperparámetros (η(0) = 0,001, 500 épocas) |
| 19 | Oja aprendió PC1: su índice y el valor de PC1 ordenan igual a los creadores | Índice de Oja contra PC1; 10 de 10 seeds coinciden |
| 20 | Elegir el máximo del índice no es correcto: cambia con el signo y no mira el tema | Tabla con el máximo según el signo del autovector |
| 21 | Fútbol: conviene profundidad, que queda lejos de los más seguidos | Dispersión PC1-PC2 de la campaña de fútbol |
| 22 | Cada campaña se ordena con su propio criterio, no con followers | Tabla campaña / criterio / top 5 / USD por mil |
| 23 | Solo por followers suele salir más barato por mil, pero ignora tema y objetivo | Tabla de comparación con el ranking por followers |
| 24 | Una campaña nueva no re-entrena nada; variables nuevas obligan a rehacer el modelo | Viñetas de mantenimiento: campaña nueva, creador nuevo, actualización mensual |
| 25 | Ejercicio 2 | Separador: Red de Hopfield |
| 26 | El conjunto GRTV es casi ortogonal (producto escalar máximo 0,04); HMNW llega a 0,84 | Alfabeto de 5×5 con los dos conjuntos marcados |
| 27 | El set separado resiste el ruido; el correlacionado nunca pasa de 25,0 % | Recuperación contra píxeles invertidos, dos curvas |
| 28 | La red puede bajar de energía hasta un estado espurio, que no es ninguna letra | Ejemplo de estado espurio y curva de energía |
| 29 | Capacidad: 3,75 patrones para N = 25 y la estabilidad cae sin un corte | Fracción de letras estables contra cantidad de patrones |
| 30 | Ejercicio QRs | Separador: Red de Hopfield |
| 31 | Los QR son idénticos en 69,8 % de sus píxeles: están muy correlacionados | Los cinco QR de 37×37 |
| 32 | Hebb recupera 0 % de los QR, ni siquiera sin ruido | Atractor común y barras de distancia a cada QR |
| 33 | Pesos que dejan estable cada QR, utilizamos la pseudo-inversa | Fórmula W = Pᵀ(PPᵀ)⁻¹P y qué hace |
| 34 | La pseudo-inversa recupera 100 % de los QR hasta el nivel 0,30 | Recuperación, overlap y costo contra el ruido |
| 35 | Con Hebb la red converge al estado común; con la pseudo-inversa, al QR consultado | Energía por paso para cada QR y nivel de ruido |
| 36 | Hopfield para QR: la correlación rompe Hebb y hay tres limitaciones medidas | Viñetas: correlación, corrimientos, tamaño de la matriz de pesos |
| 37 | Hebb recupera QR si guarda solo la parte variable de 3 QR poco parecidos | Experimento extra: recuperación contra ruido |
| 38 | Muchas gracias | Grupo 9 |
