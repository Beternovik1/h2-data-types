import os
import rdflib
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network

def crear_directorios():
    """Crea el directorio local para almacenar las visualizaciones generadas."""
    if not os.path.exists('plots'):
        os.makedirs('plots')

def construir_grafo_semantico():
    """Construye y puebla un grafo de conocimiento RDF con datos de universidades."""
    g = Graph()
    
    EX = Namespace("http://ejemplo.org/edu#")
    g.bind("ex", EX)
    g.bind("xsd", XSD)
    
    # Definición de entidades y relaciones
    Universidad, Ciudad = EX.Universidad, EX.Ciudad
    ubicada_en, fundada_en = EX.ubicada_en, EX.fundada_en
    es_publica, alumnos = EX.es_publica, EX.numero_alumnos

    # Dataset de matrículas y fundaciones
    datos_unis = {
        EX.UNAM: {"ciudad": EX.CDMX, "anio": 1910, "publica": True, "alumnos": 257747},
        EX.IPN: {"ciudad": EX.CDMX, "anio": 1936, "publica": True, "alumnos": 140806},
        EX.Tec_Monterrey: {"ciudad": EX.Monterrey, "anio": 1943, "publica": False, "alumnos": 62168},
        EX.UAM: {"ciudad": EX.CDMX, "anio": 1974, "publica": True, "alumnos": 46512},
        EX.UG: {"ciudad": EX.Guanajuato, "anio": 1732, "publica": True, "alumnos": 30855}
    }

    # Inserción de triplas con tipado fuerte (XSD)
    for uri, datos in datos_unis.items():
        g.add((uri, RDF.type, Universidad))
        g.add((datos["ciudad"], RDF.type, Ciudad))
        g.add((uri, ubicada_en, datos["ciudad"]))
        g.add((uri, fundada_en, Literal(datos["anio"], datatype=XSD.integer)))
        g.add((uri, es_publica, Literal(datos["publica"], datatype=XSD.boolean)))
        g.add((uri, alumnos, Literal(datos["alumnos"], datatype=XSD.integer)))

    return g, EX

def visualizacion_estatica_premium(g):
    """Genera un grafo estático optimizando la distribución espacial para evitar solapamientos."""
    G_nx = nx.DiGraph()
    
    # Extracción de nodos omitiendo la clase tipada de RDF
    for s, p, o in g:
        if p == RDF.type: continue 
        sujeto = s.split('#')[-1]
        predicado = p.split('#')[-1]
        objeto = str(o).split('#')[-1] if '#' in str(o) else str(o)
        
        G_nx.add_edge(sujeto, objeto, relacion=predicado)

    # Asignación de heurísticas visuales (colores y tamaños)
    colores, tamanos = [], []
    for nodo in G_nx.nodes():
        if nodo in ['UNAM', 'IPN', 'Tec_Monterrey', 'UAM', 'UG']:
            colores.append('#a2d2ff') 
            tamanos.append(3000)
        elif nodo in ['CDMX', 'Monterrey', 'Guanajuato']:
            colores.append('#ffb5a7') 
            tamanos.append(2500)
        else:
            colores.append('#e9ecef') 
            tamanos.append(1200)

    plt.figure(figsize=(26, 16)) 
    
    # Cálculo de posiciones base y escalado para aprovechar dimensiones del lienzo
    pos = nx.spring_layout(G_nx, k=5, iterations=300, seed=42)
    for nodo in pos:
        pos[nodo][0] *= 1.5 
        pos[nodo][1] *= 1.2 
    
    # Renderizado
    nx.draw_networkx_edges(G_nx, pos, edge_color='#ced4da', arrows=True, arrowsize=20, width=1.5, alpha=0.8)
    nx.draw_networkx_nodes(G_nx, pos, node_size=tamanos, node_color=colores, edgecolors='#495057', linewidths=1.5)
    
    # Ajuste del eje Y en las etiquetas para mejorar la legibilidad sobre las aristas
    pos_labels = {nodo: (coords[0], coords[1] + 0.05) for nodo, coords in pos.items()}
    nx.draw_networkx_labels(G_nx, pos_labels, font_size=12, font_weight='bold', font_color='black',
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.9, pad=2))
    
    edge_labels = nx.get_edge_attributes(G_nx, 'relacion')
    nx.draw_networkx_edge_labels(G_nx, pos, edge_labels=edge_labels, font_size=10, font_color='#d62828',
                                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.9, pad=1))
    
    plt.title("Grafo Semántico de Universidades Mexicanas", fontsize=26, fontweight='bold', pad=20)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('plots/grafo_semantico_estatico.png', dpi=300, bbox_inches='tight')

def visualizacion_interactiva_html(g):
    """Genera un grafo interactivo web configurando físicas para estabilización rápida."""
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", directed=True)
    net.barnes_hut(gravity=-2000, central_gravity=0.1, spring_length=200, spring_strength=0.01, damping=0.5)

    for s, p, o in g:
        if p == RDF.type: continue
        
        sujeto = s.split('#')[-1]
        predicado = p.split('#')[-1]
        objeto = str(o).split('#')[-1] if '#' in str(o) else str(o)
        
        net.add_node(sujeto, label=sujeto, color="#4ea8de", size=25)
        
        if objeto in ['CDMX', 'Monterrey', 'Guanajuato']:
            net.add_node(objeto, label=objeto, color="#f15bb5", size=20)
        else:
            net.add_node(objeto, label=objeto, color="#e5e5e5", size=15)

        net.add_edge(sujeto, objeto, title=predicado, label=predicado, color="#9c89b8")

    net.save_graph("plots/grafo_semantico_interactivo.html")

if __name__ == "__main__":
    crear_directorios()
    grafo, namespace = construir_grafo_semantico()
    
    # Serialización del modelo semántico
    grafo.serialize(destination="universidades_mexicanas.ttl", format="turtle")
    
    # Generación de outputs
    visualizacion_estatica_premium(grafo)
    visualizacion_interactiva_html(grafo)