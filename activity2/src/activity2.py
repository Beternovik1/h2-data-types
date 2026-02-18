import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.ops import unary_union
import folium
import matplotlib.patches as mpatches # <--- NECESARIO para la leyenda personalizada
import contextily as ctx # <--- IMPORTANTE: Nueva librería
# ==========================================
# 1. CONFIGURACIÓN Y CARGA DE DATOS
# ==========================================
def cargar_datos(ruta_hospitales="../data/centros_salud_cdmx/Centros_de_salud.shp", ruta_unidades="../data/unidades_habitacionales_cdmx/Unidades_Habitacionales.shp"):
    """
    Carga los shapefiles. GeoPandas busca automáticamente los archivos
    auxiliares (.dbf, .shx) en la misma carpeta.
    """
    print("--- Cargando Datasets ---")
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


# ==========================================
# 2. GESTIÓN DE PROYECCIONES (CRÍTICO)
# ==========================================
def gestionar_proyecciones(gdf_points, gdf_polys):
    """
    Convierte de Coordenadas Geográficas (Lat/Lon) a UTM Zona 14N (Metros)
    EPSG:32614 es el estándar para el centro de México.
    """
    print("--- Reproyectando a EPSG:32614 (Metros) ---")
    
    # Reproyectamos ambos a metros para poder calcular el buffer de 1km
    gdf_points_utm = gdf_points.to_crs(epsg=32614)
    gdf_polys_utm = gdf_polys.to_crs(epsg=32614)
    
    return gdf_points_utm, gdf_polys_utm

# ==========================================
# 3. ANÁLISIS ESPACIAL (CORE)
# ==========================================
def analisis_cobertura(gdf_hosp_utm, gdf_uni_utm, radio_km=1):
    """
    Genera buffers y determina qué unidades habitacionales tocan esos buffers.
    """
    print(f"--- Generando buffers de {radio_km} km ---")
    
    # 1. Crear Buffer (radio en metros)
    radio_metros = radio_km * 1000
    gdf_hosp_utm['geometry'] = gdf_hosp_utm.geometry.buffer(radio_metros)
    
    # 2. Unificar los buffers para crear una sola "Mancha de Cobertura"
    # Esto evita contar doble si una colonia está cerca de dos hospitales
    zona_cobertura = unary_union(gdf_hosp_utm.geometry)
    
    # 3. Identificar intersecciones (Spatial Join o Intersects)
    # Creamos una columna para marcar si está cubierta
    # Usamos 'intersects': si la unidad toca el buffer, cuenta como cubierta.
    gdf_uni_utm['cubierta'] = gdf_uni_utm.geometry.intersects(zona_cobertura)
    
    return gdf_uni_utm

# ==========================================
# 4. VISUALIZACIÓN Y KPI
# ==========================================
def visualizar_resultados(gdf_uni_procesada, gdf_hospitales_original, filename='../plots/head_map.png'):
    """
    Genera el mapa de calor: Verde (Cubierto) vs Rojo (Desatendido)
    """
    fig, ax = plt.subplots(figsize=(15, 15))
    
    # 1. Ploteamos las NO cubiertas (Rojo)
    no_cubiertas = gdf_uni_procesada[gdf_uni_procesada['cubierta'] == False]
    no_cubiertas.plot(ax=ax, color='#ff4d4d', alpha=0.6, label='Desatendidas')
    
    # 2. Ploteamos las CUBIERTAS (Verde)
    cubiertas = gdf_uni_procesada[gdf_uni_procesada['cubierta'] == True]
    cubiertas.plot(ax=ax, color='#2ecc71', alpha=0.6, label='Con Cobertura')
    
    # 3. Ploteamos los Hospitales (Puntos negros)
    # Nota: Usamos el original (Lat/Lon) o el UTM, pero deben coincidir. 
    # Aquí es más fácil plotear sobre el eje UTM que ya tenemos.
    # Pero para no complicarnos, usaremos las coordenadas de los buffers (centroides originales aprox)
    # O mejor, solo mostramos las zonas. Si quieres los puntos, necesitamos el gdf de puntos UTM original.
    # (Omitido para mantener limpieza visual del mapa de zonas, pero se puede agregar).
    
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



import contextily as ctx # <--- IMPORTANTE: Nueva librería

def visualizar_final_pro(gdf_uni_procesada, gdf_hospitales_original, radio_km=1, filename='../plots/mapa_final_contexto.png'):
    print("--- Generando Visualización con Contexto Geográfico ---")
    
    fig, ax = plt.subplots(figsize=(20, 20))
    
    # ============================================================
    # 1. TRUCO DE MAGIA: Todo a Web Mercator (EPSG:3857)
    # ============================================================
    # Para que el mapa de fondo coincida, los datos deben estar en 3857.
    # OJO: No cambiamos los datos originales, solo copias para plotear.
    
    # Unidades Habitacionales (reproyectar a 3857)
    uni_web = gdf_uni_procesada.to_crs(epsg=3857)
    
    # Hospitales (reproyectar a 3857)
    hosp_web = gdf_hospitales_original.to_crs(epsg=3857)
    
    # Buffers (Truco: Calculamos en UTM para precisión, LUEGO reproyectamos)
    # Primero pasamos a UTM (si no estaba) para medir 1000m reales
    hosp_utm = gdf_hospitales_original.to_crs(epsg=32614) 
    buffers_utm = hosp_utm.geometry.buffer(radio_km * 1000)
    # Ahora pasamos esos círculos a Web Mercator para el mapa
    buffers_web = buffers_utm.to_crs(epsg=3857)

    # ============================================================
    # 2. CAPAS DEL MAPA (Orden importa: Abajo -> Arriba)
    # ============================================================
    
    # Capa A: Buffers Azules (Fondo de datos)
    buffers_web.plot(ax=ax, facecolor='#3498db', edgecolor='#2980b9', alpha=0.15, linewidth=1, zorder=1)

    # Capa B: Unidades Habitacionales (Verde/Rojo)
    # Desatendidas
    uni_web[uni_web['cubierta'] == False].plot(ax=ax, color='#e74c3c', alpha=0.6, zorder=2)
    # Cubiertas
    uni_web[uni_web['cubierta'] == True].plot(ax=ax, color='#2ecc71', alpha=0.6, zorder=3)
    
    # Capa C: Puntos de Hospitales
    hosp_web.plot(ax=ax, color='black', markersize=15, marker='+', zorder=4, alpha=0.8)

    # ============================================================
    # 3. EL BASEMAP (CONTEXTO)
    # ============================================================
    # Aquí agregamos el mapa de calles sutil al fondo.
    # source=ctx.providers.CartoDB.Positron es el estilo limpio (gris).
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=12) # Zoom 12 es bueno para CDMX

    # ============================================================
    # 4. ESTÉTICA Y LEYENDA (Igual que antes)
    # ============================================================
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


def mapa_interactivo_optimizado(gdf_uni_procesada, gdf_hospitales, filename="../plots/mapa_cobertura_cdmx.html"):
    print("--- Generando Mapa Interactivo OPTIMIZADO ---")
    
    # 1. REPROYECCIÓN A WGS84 (Lat/Lon)
    # Convertimos ambos datasets
    colonias_web = gdf_uni_procesada.to_crs(epsg=4326)
    hospitales_web = gdf_hospitales.to_crs(epsg=4326)
    
    # 2. SIMPLIFICACIÓN (Para que no pese tanto el HTML)
    colonias_web['geometry'] = colonias_web.geometry.simplify(tolerance=0.0001, preserve_topology=True)
    
    # 3. CENTRAR EN CDMX
    # Usamos las coordenadas que nos dio tu diagnóstico: 19.37, -99.11
    m = folium.Map(location=[19.3756, -99.1121], zoom_start=11, tiles='CartoDB positron')
    
    # 4. DEFINIR ESTILO (Verde vs Rojo)
    def style_function(feature):
        # Convertimos a string para asegurar comparación, aunque sea boolean
        es_cubierta = feature['properties']['cubierta']
        
        # Color: Verde (#2ecc71) si True, Rojo (#e74c3c) si False
        return {
            'fillColor': '#2ecc71' if es_cubierta else '#e74c3c', 
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.6
        }
    
    # 5. CAPA DE COLONIAS (POLÍGONOS)
    # AQUÍ ESTABA EL ERROR: Usamos las columnas exactas 'Nombre' y 'Alcaldia'
    folium.GeoJson(
        colonias_web,
        name='Cobertura Hospitalaria',
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['Nombre', 'Alcaldia', 'cubierta'], # <--- Nombres EXACTOS del print
            aliases=['Colonia:', 'Alcaldía:', '¿Tiene Hospital?:'],
            localize=True
        )
    ).add_to(m)

    # 6. CAPA DE HOSPITALES (PUNTOS)
    # Agregamos los puntitos azules de los hospitales para referencia
    hospitales_group = folium.FeatureGroup(name="Hospitales")
    for _, row in hospitales_web.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=3,
            color='#2980b9',
            fill=True,
            fill_color='#2980b9',
            popup="Centro de Salud"
        ).add_to(hospitales_group)
    hospitales_group.add_to(m)

    # 7. CONTROLES Y GUARDADO
    folium.LayerControl().add_to(m)
    m.save(filename)
    print(f"[ÉXITO] Mapa interactivo guardado como: {filename}")

# --- EJECUTAR ---
# mapa_interactivo_optimizado(unidades_analizadas, hospitales)



# ==========================================
# EJECUCIÓN (MAIN)
# ==========================================


if __name__ == "__main__":

    # Pipeline de ejecución
    try:
        # 1. Cargar
        hospitales, unidades = cargar_datos()
        
        # 2. Proyectar (De Lat/Lon a Metros)
        hosp_utm, uni_utm = gestionar_proyecciones(hospitales, unidades)
        
        # 3. Analizar (Buffer + Intersección)
        # NOTA: Pasamos una COPIA de hosp_utm para no perder los puntos originales si quisieramos usarlos despues,
        # ya que la función modifica la geometría a polígonos (buffers).
        unidades_analizadas = analisis_cobertura(hosp_utm.copy(), uni_utm, radio_km=1)
        
        # 4. Visualizar
        visualizar_resultados(unidades_analizadas, hospitales)


        # DIAGNÓSTICO
        print("--- COLUMNAS DISPONIBLES ---")
        print(unidades_analizadas.columns) # Para ver el nombre real de la colonia (¿es 'nombre', 'COLONIA', 'ref'?)

        print("\n--- COORDENADAS ---")
        # Vamos a ver una muestra de las geometrías reproyectadas
        test_geo = unidades_analizadas.to_crs(epsg=4326)
        print(f"Centroide aprox (Lat/Lon): {test_geo.geometry.centroid.y.mean()}, {test_geo.geometry.centroid.x.mean()}")
        # Si salen números gigantes (ej. 2000000), falló la reproyección.
        # Si salen números tipo 19.43, -99.13, está bien.

        mapa_interactivo_optimizado(unidades_analizadas, hospitales)
        visualizar_final_pro(unidades_analizadas, hospitales)


    except Exception as e:
        print(f"Error en la ejecución: {e}")
