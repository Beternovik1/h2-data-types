import pandas as pd
import math
import networkx as nx
import folium

def cargar_y_limpiar_datos(path="../data/"):
    cols_airports = ["airport_id", "name", "city", "country", "IATA", "ICAO",
                     "latitude", "longitude", "altitude", "timezone", "DST",
                     "TZ", "type", "source"]
    cols_routes = ["airline", "airline_id", "source_airport", "source_airport_id",
                    "dest_airport", "dest_airport_id", "codeshare", "stops", "equipment"]    
    
    df_airports = pd.read_csv(f"{path}airports.dat", header=None, names=cols_airports, sep=",", na_values='\\N')
    df_routes = pd.read_csv(f"{path}routes.dat", header=None, names=cols_routes, sep=",", na_values='\\N')

    # Limpieza aeropuertos (solo ocupamos latitud, longitud y el id del aeropuerto)
    df_airports = df_airports.dropna(subset=["latitude", "longitude", "airport_id"])
    # forzamos el id a numerico y lo establecemos como el inidice del nuevo df
    df_airports['airport_id'] = pd.to_numeric(df_airports['airport_id'], errors='coerce')
    df_airports = df_airports.dropna(subset=['airport_id'])
    df_airports['airport_id'] = df_airports['airport_id'].astype(int)
    df_airports.set_index('airport_id', inplace=True)
    
    # Limpieza de las rutas. 
    # forzando la conversion de los ids foraneos
    df_routes['source_airport_id'] = pd.to_numeric(df_routes['source_airport_id'], errors='coerce')
    df_routes['dest_airport_id'] = pd.to_numeric(df_routes['dest_airport_id'], errors='coerce')

    # eliminando datos basura, rutas que no tienen id de origen o de destino
    df_routes = df_routes.dropna(subset=['source_airport_id', 'dest_airport_id'])
    df_routes['source_airport_id'] = df_routes['source_airport_id'].astype(int)
    df_routes['dest_airport_id'] = df_routes['dest_airport_id'].astype(int)

    return df_airports, df_routes

def calcular_haversine(lat1, lon1, lat2, lon2):
    """
    calculando la distancia en km entre dos puntos
    """
    # radio de la tierra en km
    r = 6371.0
    # convirtiendo coordenadas a radianes
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # diferencias
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    # haversine formula
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    distancia = r * c
    return distancia

def construir_grafo_con_pesos(df_airports, df_routes):
    """
    construyendo el grafo asignando la distancia de haversine como peso
    a las aristas
    """
    print("Construyendo grafo con pesos en las aristas...")
    G = nx.DiGraph()

    # agregando nodos
    for airport_id, row in df_airports.iterrows():
        G.add_node(
            airport_id,
            name=row['name'],
            iata=row['IATA'],
            lat=row['latitude'],
            lon=row['longitude']
        )

    # validando la integridad de las rutas
    nodos_validos = set(G.nodes)
    rutas_seguras = df_routes[
        df_routes['source_airport_id'].isin(nodos_validos) &
        df_routes['dest_airport_id'].isin(nodos_validos)
    ]

    # agregando aristas con pesos
    dict_coords = df_airports[['latitude', 'longitude']].to_dict('index')
    
    aristas_con_atributos = []

    for row in rutas_seguras.itertuples():
        origen = row.source_airport_id
        destino = row.dest_airport_id

        # extrayendo coordenadas del diccionario
        lat_orig = dict_coords[origen]['latitude']
        lon_orig = dict_coords[origen]['longitude']
        lat_dest = dict_coords[destino]['latitude']
        lon_dest = dict_coords[destino]['longitude']

        # calculando el costo de la ruta
        distancia_km = calcular_haversine(lat_orig, lon_orig, lat_dest, lon_dest)
        # guardando la arista con los atributos distancia y paradas
        aristas_con_atributos.append((origen, destino, {'distancia': distancia_km, 'stops': row.stops}))

    G.add_edges_from(aristas_con_atributos)
    print(f"Grafo finalizado: {G.number_of_nodes()} nodos y {G.number_of_edges()} aristas con peso")
    return G

def obtener_id_por_iata(G, codigo_iata):
     """
     buscando el codigo de 3 letras IATA de cada aeropuerto
     """
     for nodo, atributos in G.nodes(data=True):
          if atributos.get('iata') == codigo_iata:
               return nodo
     return None

def buscar_mejor_ruta(G, iata_origen, iata_destino, optimizar_por=None):
     """
     buscando el camino mas corto mediante Dijkstra
     """
     print(f"Buscando ruta mas corta de: {iata_origen} -> {iata_destino}...")
     id_origen = obtener_id_por_iata(G, iata_origen)
     id_destino = obtener_id_por_iata(G, iata_destino)

     if not id_origen or not id_destino:
          print("Error !. el codigo IATA de origen o destino no se encontro")
          return None
     try:
        # weight dicta si evaluamos escalas o kilometros
        ruta_ids = nx.shortest_path(G, source=id_origen, target=id_destino, weight=optimizar_por)

        print(f"Criterio de optimizacion: {'Menos escalas' if optimizar_por is None else 'Menos km'}")
        print("Itinerario de vuelo: ")

        distancia_total = 0.0

        for i in range(len(ruta_ids)):
            nodo_actual = ruta_ids[i]
            datos_nodo = G.nodes[nodo_actual]

            print(f" {i+1}. {datos_nodo['name']} ({datos_nodo['iata']})")

            if i < len(ruta_ids) - 1:
                nodo_siguiente = ruta_ids[i+1]
                distancia_tramo = G[nodo_actual][nodo_siguiente]['distancia']
                distancia_total += distancia_tramo
        if optimizar_por == 'distancia':
            print(f"Distancia total estimada: {distancia_total:.2f} km")
        return ruta_ids
     except nx.NetworkXNoPath:
        print("No existe una ruta de vuelos comerciales que conecte estos aeropuertos :'(")


def visualizar_ruta_mapa(G, ruta_ids, nombre_archivo="../plots/ruta_vuelo.html"):
    """
    toma una lista de rutas o nodos, extrae sus coordenadas y genera un mapa HTML interactivo con la ruta trazada
    """
    if not ruta_ids:
        print("No hay ruta para visualizar.")
        return

    print(f"\nGenerando mapa interactivo: {nombre_archivo}...")
    
    # iniciar el mapa centrado en el primer aeropuerto de la ruta
    nodo_inicio = ruta_ids[0]
    lat_inicio = G.nodes[nodo_inicio]['lat']
    lon_inicio = G.nodes[nodo_inicio]['lon']
    # zoom_start=4 nos da una buena vista continental
    mapa = folium.Map(location=[lat_inicio, lon_inicio], zoom_start=4)
    coordenadas_ruta = []
    # iterar sobre los aeropuertos para poner marcadores y trazar la línea
    for i, nodo in enumerate(ruta_ids):
        datos = G.nodes[nodo]
        lat = datos['lat']
        lon = datos['lon']
        nombre = datos['name']
        iata = datos['iata']
        coordenadas_ruta.append((lat, lon))
        # origen y destino en azul, escalas en verde
        color_marcador = "blue" if i == 0 or i == len(ruta_ids)-1 else "green"
        folium.Marker(
            location=[lat, lon],
            popup=f"<b>{nombre}</b><br>IATA: {iata}",
            tooltip=iata,
            icon=folium.Icon(color=color_marcador, icon="info-sign")
        ).add_to(mapa)
    # dibujando la línea que conecta los puntos
    folium.PolyLine(
        locations=coordenadas_ruta,
        color="red",
        weight=4,
        opacity=0.7,
        tooltip="Ruta de vuelo"
    ).add_to(mapa)
    
    mapa.save(nombre_archivo)
    print(f"mapa guardado exitosamente!")

if __name__ == "__main__":
        df_airports, df_routes = cargar_y_limpiar_datos()
        grafo_vuelos = construir_grafo_con_pesos(df_airports, df_routes)
        print(f"Total de aeropuertos (Nodos): {grafo_vuelos.number_of_nodes()}")
        print(f"Total de rutas validas (Aristas): {grafo_vuelos.number_of_edges()}")

        # escenario A: quiero llegar a tokio haciendo la menor catidad de conexiones
        print("+++++++++++++++++++++++++++++++++++")
        buscar_mejor_ruta(grafo_vuelos, iata_origen="BJX", iata_destino="NRT", optimizar_por=None)
        print("+++++++++++++++++++++++++++++++++++")
        # escenario B: quiero llegar a tokio volando la menor catidad de km
        ruta_optima_km = buscar_mejor_ruta(grafo_vuelos, iata_origen="BJX", iata_destino="NRT", optimizar_por="distancia")
        visualizar_ruta_mapa(grafo_vuelos, ruta_optima_km)