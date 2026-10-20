# Imágenes de productos

Cada foto se llama igual que el **código de barras** del producto, en PNG:

```
static/img/7501234567890.png   →  producto con barcode "7501234567890"
```

- Si el producto no tiene código de barras o no hay archivo, la app muestra
  sus iniciales sobre un color de su categoría.
- Recomendado: cuadrada, unos 300×300 px y fondo blanco o transparente
  (cada foto pesa ~10 KB; importa en la Raspberry Pi).
- Las imágenes van dentro de la imagen de Docker del frontend: después de
  agregar o cambiar una, hay que reconstruir con
  `docker compose up -d --build frontend`.

## Créditos

Las fotos de los productos del catálogo inicial (`productos_tiendita.json`)
provienen de [Open Food Facts](https://world.openfoodfacts.org) y se usan bajo
licencia [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/deed.es).
Fueron reducidas a 300×300 px con fondo blanco.
