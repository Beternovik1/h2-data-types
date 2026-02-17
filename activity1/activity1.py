import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import folium

def loading_data(path):
    """Cargando los datos"""
    try:
        df = pd.read_csv(path, encoding='latin1')
        print("Perfectly imported...")
        return df
    except FileNotFoundError:
        print("Error: We couldn't find the file")
        return None
    
def clean_data(df):
    """
    Como el df es de estaciones de bicicletas publicas en CDMX
    la latitud esta entre 19.0 y 19.6
    la longitud esta entre -99.0 y -99.4
    eliminando filas con valores na
    """
    df_clean = df.dropna()
    mask = (df_clean["latitud"] > 18) & (df_clean['latitud'] < 20) & (df_clean['longitud'] > -100) & (df_clean['longitud'] < -98)

    df_clean = df_clean[mask]
    return df_clean


def exploratory_plot(df, filename="plots/mapa_exploratorio2.png"):
    plt.figure(figsize=(10, 8))
    if 'Cluster' in df.columns:
        plt.scatter(df['longitud'], df['latitud'], s=15, alpha=0.6, c=df['Cluster'], cmap='viridis')
        plt.title(f"Distribución con {df['Cluster'].nunique()} Clusters")    
    else:
        plt.scatter(df['longitud'], df['latitud'], s=5, alpha=0.6, c='blue')
        plt.title("Distribución de estaciones (df_limpio)")
    plt.xlabel("Longitud")
    plt.ylabel("Latitud")
    plt.grid(True)

    plt.savefig(filename)
    print("Plot guardado !")
    plt.close()

def best_k(df, filename="plots/elbow_method.png"):
    """
    Generando el grafico del codo para decidir el mejor k
    """
    print("Calculando el metodo del codo...")
    X = df[['latitud', 'longitud']]
    inercia = []
    rango_k = range(1, 11)

    for k in rango_k:
        # Calculando k-means para cada k
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        inercia.append(kmeans.inertia_) # Guardando la suma de errores al cuadrado

    plt.figure()
    plt.plot(rango_k, inercia, marker='o', linestyle='--')
    plt.title('Método del Codo: ¿Cuántos perfiles existen?')
    plt.xlabel('Numero de clusters (k)')
    plt.ylabel('Inercia')
    plt.grid(True)
    
    plt.savefig(filename)
    print("Plot guardado !")
    plt.close()

def clustering(df, n_clusters=4):
    """
    creando n_clusters usando K-means y agregando
    la columna cluster al df
    """
    print("Calculando clusters...")
    X = df[['latitud', 'longitud']]
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    df['Cluster'] = clusters
    return df

def create_map(df, filename="plots/mapa_final.html"):
    """
    Genrando mapa interactivo con Folium
    con circules y distintos colores por cluster
    """
    print("Generando mapa interactivo...")

    centro = [df['latitud'].mean(), df['longitud'].mean()]
    m = folium.Map(location=centro, zoom_start=13, tiles='CartoDB positron')

    colores = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'beige']

    # Iterar osbre cada estacin para poner el punto
    for _, row in df.iterrows():
         capacidad = 20
         radio = (capacidad - 10) / 2
         
         estacion_id = row['num_cicloe']
         nombre = row['calle_prin']
         colonia = row['colonia']

         cluster_id = int(row['Cluster'])
         color_punto = colores[cluster_id % len(colores)]

         folium.CircleMarker(
                     location=[row['latitud'], row['longitud']],
                     radius=radio,
                     # Popup con datos reales
                     popup=f"<b>ID:</b> {estacion_id}<br><b>Calle:</b> {nombre}<br><b>Colonia:</b> {colonia}<br><b>Cluster:</b> {cluster_id}",
                     tooltip=f"{nombre} ({colonia})",
                     color=color_punto,
                     fill=True,
                     fill_color=color_punto,
                     fill_opacity=0.7
                 ).add_to(m)
    m.save(filename)
    print(f"Mapa interactivo guarado en {filename}")


if __name__ == "__main__":
    df = loading_data("data/cicloestaciones_ecobici.csv")
    df_clean = clean_data(df)
    # exploratory_plot(df)

    best_k(df_clean)
    df_cluster = clustering(df_clean, 4)
    exploratory_plot(df_cluster)
    # print(df_cluster.head(4))
    create_map(df_cluster)
