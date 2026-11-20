# Datos del proyecto – Twitch

Este directorio contiene los conjuntos de datos de Twitch utilizados en el proyecto, correspondientes a los años 2018, 2021, 2022 y 2023.

## Estructura

```text
datos_twitch/
├── datos_twitch_2018/
│   └── twitch_gamers.zip
├── datos_twitch_2021/
│   └── twitch_2021.zip
├── datos_twitch_2022/
│   └── twitch_2022.zip
└── datos_twitch_2023/
    └── README.md
```

## Descarga de los datos

Los conjuntos de datos de 2018, 2021 y 2022 están incluidos directamente en este repositorio.

**Datos de 2023**

Debido al tamaño del conjunto de datos (aproximadamente 2,6 GB), se ha alojado externamente en Google Drive.

- [Descargar datos de Twitch 2023](https://drive.google.com/file/d/1_szNRXkv4I2jgzgduggOrSW32P6KODIt/view?usp=sharing)

El archivo descargado se llama twitch_2023.zip.

## Contenido de los archivos

| Año | Archivo comprimido | Archivos resultantes |
| --- | --- | --- |
| 2018 | twitch_gamers.zip | large_twitch_edges.csv, large_twitch_features.csv |
| 2021 | twitch_2021.zip | 2021-12-edges.csv, 2021-12-nodes.csv |
| 2022 | twitch_2022.zip | 2022-01-edges.csv, 2022-01-nodes.csv |
| 2023 | twitch_2023.zip | 100k_a.csv, full_a.csv |

## Descompresión

Es necesario descomprimir los archivos ZIP antes de utilizar los datos.

Para los datos de 2023, primero hay que descargar el ZIP de Google Drive y situarlo en el directorio datos_twitch_2023/.

Notas

- Los datos de 2018, 2021 y 2022 están almacenados directamente en GitHub.

- Los datos de 2023 se distribuyen mediante Google Drive debido a su tamaño.

- Los archivos se mantienen comprimidos en el repositorio para reducir su tamaño.

- Para ejecutar los análisis es necesario disponer de los archivos descomprimidos.
