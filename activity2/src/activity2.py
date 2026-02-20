import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.ops import unary_union
import folium
import matplotlib.patches as mpatches 
import contextily as ctx 

def cargar_datos(ruta_hospitales="../data/centros_salud_cdmx/Centros_de_salud.shp", ruta_unidades="../data/unidades_habitacionales_cdmx/Unidades_Habitacionales.shp"):
    """
    Carga los shapefiles. GeoPandas busca automáticamente los archivos
    auxiliares (.dbf, .shx) en la misma carpeta que se encuentra el shp.
    """
    print("cargando archivos...")
    try:
        # Leemos el archivo .shp
        gdf_hosp = gpd.read_file(ruta_hospitales)
        gdf_uni = gpd.read_file(ruta_unidades)
        print(f"Hospitales cargados: {len(gdf_hosp)}")
        print(f"Unidades Habitacionales cargadas: {len(gdf_uni)}")
        return gdf_hosp, gdf_uni
    except FileNotFoundError:
        print("Error !. Archivos no entontrados ...")
        return None


def gestionar_proyecciones(gdf_points, gdf_polys):
    """
    Convierte de Coordenadas Geográficas (Lat/Lon) a UTM Zona 14N (Metros)
    EPSG:32614 es el estándar para el centro de México.
    """
    print("reproyectando a EPSG:32614 (Metros)...")

    # reproyectamos ambos a metros para poder calcular el buffer de 1km
    gdf_points_utm = gdf_points.to_crs(epsg=32614)
    gdf_polys_utm = gdf_polys.to_crs(epsg=32614)
    
    return gdf_points_utm, gdf_polys_utm

def analisis_cobertura(gdf_hosp_utm, gdf_uni_utm, radio_km=1):
    """
    Genera buffers y determina qué unidades habitacionales tocan esos buffers de radio de 1km.
    """
    print(f"generando buffers de {radio_km} km...")
    
    # crear buffer(radio en metros)
    radio_metros = radio_km * 1000
    gdf_hosp_utm['geometry'] = gdf_hosp_utm.geometry.buffer(radio_metros)
    
    # unificar los buffers para crear una sola "Mancha de Cobertura"
    # Esto evita contar doble si una colonia está cerca de dos hospitales
    zona_cobertura = unary_union(gdf_hosp_utm.geometry)
    
    # identificar intersecciones (Spatial Join o Intersects)
    # Creamos una columna para marcar si está cubierta
    # Usamos 'intersects': si la unidad toca el buffer, cuenta como cubierta.
    gdf_uni_utm['cubierta'] = gdf_uni_utm.geometry.intersects(zona_cobertura)
    
    return gdf_uni_utm

def visualizar_resultados(gdf_uni_procesada, gdf_hospitales_original, filename='../plots/head_map.png'):
    """
    Genera el mapa de calor: Verde (Cubierto) vs Rojo (Desatendido)
    """
    fig, ax = plt.subplots(figsize=(15, 15))
    
    # ploteamos las NO cubiertas en rojo
    no_cubiertas = gdf_uni_procesada[gdf_uni_procesada['cubierta'] == False]
    no_cubiertas.plot(ax=ax, color='#ff4d4d', alpha=0.6, label='Desatendidas')
    
    # ploteamos las CUBIERTAS en Verde
    cubiertas = gdf_uni_procesada[gdf_uni_procesada['cubierta'] == True]
    cubiertas.plot(ax=ax, color='#2ecc71', alpha=0.6, label='Con Cobertura')
    
    # ploteamos los Hospitales con Puntos negros
    plt.title("Análisis de Cobertura Hospitalaria (Radio 1km) - CDMX", fontsize=20)
    plt.axis('off')
    
    # KPI
    total = len(gdf_uni_procesada)
    num_cubiertas = len(cubiertas)
    porcentaje = (num_cubiertas / total) * 100
    
    print(f"\nResultados Finales:")
    print(f"Total Unidades: {total}")
    print(f"Unidades Cubiertas: {num_cubiertas}")
    print(f"KPI Cobertura: {porcentaje:.2f}%")
    
    # plt.legend()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Figura guardada con exito ! en {filename}")
    plt.close()



def visualizar_final_pro(gdf_uni_procesada, gdf_hospitales_original, radio_km=1, filename='../plots/mapa_final_contexto.png'):
    print("generando visualizacion con contexto geografico...")
    fig, ax = plt.subplots(figsize=(20, 20))
    # para que el mapa de fondo coincida, los datos deben estar en 3857
    # unidades habitacionales (reproyectar a 3857)
    uni_web = gdf_uni_procesada.to_crs(epsg=3857)
    # hospitales (reproyectar a 3857)
    hosp_web = gdf_hospitales_original.to_crs(epsg=3857)
    # Buffers calculamos en UTM para precision y luego reproyectamos
    # Primero pasamos a UTM para medir 1000m reales
    hosp_utm = gdf_hospitales_original.to_crs(epsg=32614) 
    buffers_utm = hosp_utm.geometry.buffer(radio_km * 1000)
    # Ahora pasamos esos círculos a Web Mercator para el mapa
    buffers_web = buffers_utm.to_crs(epsg=3857)

    # CAPAS DEL MAPA (Orden importa: Abajo -> Arriba)
    # Capa A: Buffers Azules (Fondo de datos)
    buffers_web.plot(ax=ax, facecolor='#3498db', edgecolor='#2980b9', alpha=0.15, linewidth=1, zorder=1)

    # Capa B: Unidades Habitacionales (verde o rojo)
    # Desatendidas
    uni_web[uni_web['cubierta'] == False].plot(ax=ax, color='#e74c3c', alpha=0.6, zorder=2)
    # Cubiertas
    uni_web[uni_web['cubierta'] == True].plot(ax=ax, color='#2ecc71', alpha=0.6, zorder=3)
    
    # Capa C: puntos de hospitales
    hosp_web.plot(ax=ax, color='black', markersize=15, marker='+', zorder=4, alpha=0.8)

    # Aquí agregamos el mapa de calles sutil al fondo.
    # source=ctx.providers.CartoDB.Positron es el estilo limpio (gris).
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=12) # Zoom 12 es bueno para CDMX

    plt.title(f"Análisis de Cobertura Hospitalaria CDMX - Radio {radio_km}km", fontsize=24, fontweight='bold')
    plt.axis('off') # Quitamos los ejes de coordenadas que ensucian
    
    # Leyenda Manual
    patch_rojo = mpatches.Patch(color='#e74c3c', alpha=0.6, label='Zonas Desatendidas')
    patch_verde = mpatches.Patch(color='#2ecc71', alpha=0.6, label='Zonas Cubiertas')
    patch_azul = mpatches.Patch(color='#3498db', alpha=0.3, label=f'Radio de Acción ({radio_km}km)')
    marker_hosp = plt.Line2D([0], [0], marker='+', color='w', markeredgecolor='black', markersize=10, label='Centro de Salud')

    plt.legend(handles=[patch_verde, patch_rojo, patch_azul, marker_hosp], 
               loc='lower left', fontsize=15, frameon=True, facecolor='white', framealpha=0.9)

    # KPI Box
    total = len(gdf_uni_procesada)
    pct = (len(uni_web[uni_web['cubierta'] == True]) / total) * 100
    texto_kpi = f"Cobertura Total:\n{pct:.2f}%"
    plt.text(0.98, 0.02, texto_kpi, transform=ax.transAxes, fontsize=22, fontweight='bold',
             color='#2c3e50', ha='right', va='bottom', 
             bbox=dict(facecolor='white', alpha=0.9, boxstyle='round,pad=0.5', edgecolor='#bdc3c7'))

    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Figura PRO guardada con éxito en {filename}")
    plt.close()


if __name__ == "__main__":

    try:
        hospitales, unidades = cargar_datos()
        hosp_utm, uni_utm = gestionar_proyecciones(hospitales, unidades)
        unidades_analizadas = analisis_cobertura(hosp_utm.copy(), uni_utm, radio_km=1)
        visualizar_resultados(unidades_analizadas, hospitales)
        visualizar_final_pro(unidades_analizadas, hospitales)
    except Exception as e:
        print(f"Error en la ejecución: {e}")
