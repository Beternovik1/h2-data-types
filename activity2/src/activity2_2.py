import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import ListedColormap
import matplotlib.patches as mpatches

def analisis_final_categorias(ruta_colonias, ruta_hospitales, output_map="../plots/mapa_categorias_final.png"):
    print("--- 1. Carga y Proceso (Igual que antes) ---")
    gdf_colonias = gpd.read_file(ruta_colonias).to_crs(epsg=32614)
    gdf_hosp = gpd.read_file(ruta_hospitales).to_crs(epsg=32614)
    
    # Spatial Join
    columna_clave = 'UT' # Asumimos que esta es la buena
    join_espacial = gpd.sjoin(gdf_hosp, gdf_colonias, how="inner", predicate="within")
    conteo = join_espacial.groupby(columna_clave).size().reset_index(name='num_hospitales')
    gdf_final = gdf_colonias.merge(conteo, on=columna_clave, how='left')
    gdf_final['num_hospitales'] = gdf_final['num_hospitales'].fillna(0)

    # ============================================================
    # 2. CREACIÓN DE CATEGORÍAS (EL SECRETO) 🤫
    # ============================================================
    print("--- Creando Categorías de Negocio ---")
    
    def clasificar(n):
        if n == 0:
            return "0: Sin Cobertura"
        elif n == 1:
            return "1: Un Centro"
        else:
            return "2+: Múltiples Centros"
    
    gdf_final['categoria'] = gdf_final['num_hospitales'].apply(clasificar)
    
    # Ordenamos las categorías para que la leyenda salga bonita (0, 1, 2)
    gdf_final = gdf_final.sort_values('num_hospitales')

    # ============================================================
    # 3. VISUALIZACIÓN CATEGÓRICA
    # ============================================================
    gdf_web = gdf_final.to_crs(epsg=3857)
    
    fig, ax = plt.subplots(figsize=(15, 15))

    # DEFINIMOS COLORES MANUALES (Diccionario de colores)
    # Gris transparente para los vacíos, Azul para 1, Rojo para 2+
    colores = {
        "0: Sin Cobertura": "#bdc3c7",      # Gris (Silver)
        "1: Un Centro": "#f39c12",          # Naranja
        "2+: Múltiples Centros": "#c0392b"  # Rojo Oscuro
    }
    
    # Plot Categorico
    gdf_web.plot(column='categoria',
                 categorical=True,      # <--- ESTO ES CLAVE
                 k=3,
                 cmap=ListedColormap([colores["0: Sin Cobertura"], 
                                      colores["1: Un Centro"], 
                                      colores["2+: Múltiples Centros"]]),
                 linewidth=0.2,
                 edgecolor='white',     # Borde blanco para separar colonias
                 ax=ax,
                 alpha=0.7,
                 legend=True,
                 legend_kwds={'loc': 'lower right', 'title': 'Nivel de Cobertura'})

    # Mapa Base
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

    plt.title("Clasificación de Cobertura Hospitalaria por Colonia", fontsize=22, fontweight='bold')
    plt.axis('off')
    
    plt.savefig(output_map, dpi=300, bbox_inches='tight')
    print(f"Mapa categórico guardado en: {output_map}")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    ruta_shp_iecm = "../data/colonias_iecm_2022/colonias_iecm2022_.shp"
    ruta_shp_hosp = "../data/centros_salud_cdmx/Centros_de_salud.shp"
    
    try:
        analisis_final_categorias(ruta_shp_iecm, ruta_shp_hosp)
    except Exception as e:
        print(f"Error: {e}")