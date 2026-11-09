# Datos derivados

- `twitch_PT_nodes.csv` y `twitch_PT_edges.csv`: red inducida por usuarios con `language = PT`.
- `comparativa_idiomas.csv`: resumen del grafo inducido para cada idioma.
- `afinidad_idioma.csv`: fracción de aristas del mismo idioma, valor esperado por mezcla aleatoria y assortatividad categórica.

Los archivos de comparación se regeneran desde `twitch_gamers/large_twitch_features.csv` y `large_twitch_edges.csv` al ejecutar el notebook.
