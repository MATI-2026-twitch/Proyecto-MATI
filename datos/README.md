# Red portuguesa filtrada

Datos derivados localmente de `twitch_gamers/`: se seleccionan filas de `large_twitch_features.csv` con `language == PT`, y luego filas de `large_twitch_edges.csv` cuyos dos extremos están en ese conjunto.

- `twitch_PT_nodes.csv`: 2.536 IDs portugueses, incluso si no tienen vecinos portugueses.
- `twitch_PT_edges.csv`: 42.952 amistades PT—PT.

El notebook repite el filtrado y regenera ambos CSV para que el proceso sea reproducible. Dataset original: *Twitch Gamers*, https://arxiv.org/abs/2101.03091.
