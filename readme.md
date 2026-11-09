# Proyecto MATI: Twitch portugués

El análisis guiado está en `Proyecto_Twitch_MATI.ipynb`. Usa los CSV de `twitch_gamers/`, filtra usuarios con `language == PT` y conserva las amistades entre dos usuarios PT. La primera sección guarda la red derivada en `datos/twitch_PT_nodes.csv` y `datos/twitch_PT_edges.csv`.

La carpeta PT contiene 2.536 usuarios. El filtrado de aristas produce 42.952 amistades mutuas entre esos usuarios; 90 usuarios no tienen vecinos PT y se mantienen como vértices aislados. El cuaderno vuelve a calcular y mostrar estas cifras al ejecutarse.

Abre el notebook en SageMath/Jupyter y ejecuta las celdas de arriba abajo. La carpeta `twitch_gamers/` debe permanecer en la raíz.
