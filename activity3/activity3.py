import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from statsmodels.tsa.seasonal import seasonal_decompose
from pmdarima import auto_arima
from sklearn.metrics import root_mean_squared_error



def cargando_datos(path="data/wine_sales.xlsx"):
    """
    cargando los datos
    """
    df = pd.read_excel(path)
    return df

def transformando_datos(df):
    """
    transformando los datos
        - renombrando columnas 
        - convirtiendo la fecha de int a datetime
        - creando nuevo df con columnas utiles
    """
    # Renombrando columnas
    nuevas_columnas = ['id', 'date_int', 'product_name', 'price', 'sales', 'reviews', 'brand', 'searches']
    df.columns = nuevas_columnas
    
    # Convirtiendo a datetime la fecha
    df['date'] = pd.to_datetime(df['date_int'], format='%Y%m')

    # sumar todas las ventas de cada mes 
    # Aqui pandas devuelve una serie
    ventas_mensuales = df.groupby('date')['sales'].sum()

    # ordenamos por fecha
    ventas_mensuales = ventas_mensuales.sort_index()

    # .asfreq('MS') obliga a la serie a tener un dato cada incio de mes
    # si falta un mes, lo crea y pone na y con fillna(0) los cambiamos por 0
    # Asignar la frecuencia 
    ventas_mensuales = ventas_mensuales.asfreq('MS').fillna(0)
    ventas_mensuales.name = 'Total wine sales'
    print(f"Datos transformados !. {len(ventas_mensuales)} meses")
    return ventas_mensuales

def visualizacion_serie_tiempo(ts, filename='plots/time_seres.png'):
    """
    vizualizando la serie de tiempo de la fecha y las ventas
    """
    plt.figure(figsize=(12,6))

    plt.plot(ts.index, ts.values, marker='o', linestyle='-', color='#800020')
    plt.title(f'Analisis de series de tiempo: {ts.name}')
    plt.xlabel("Fecha")
    plt.ylabel("Ventas")
    plt.grid(True, alpha=0.3)

    plt.savefig(filename)
    print("Figure guardada !")
    plt.close()

def descomposicion(ts, filename="plots/decomposition.png"):
    """
    el df solo tiene 10 meses si buscamos patrones por 12 meses la 
    descomposicion fallara, por eso usare perdio=3 para los 3 meses
    """
    descomposicion = seasonal_decompose(ts, model='additive', period=3)
    
    fig = descomposicion.plot()
    fig.set_size_inches(10, 8)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print("Grafica de descomposicion guardada...")

def sarima_pipeline(ts, filename="plots/final_forecast.png"):
    """
    como solo tenemos 
    """
    # train = primeros 8 meses
    train_size= len(ts) - 2
    train = ts.iloc[:train_size]
    # test = ultimos 2 meses
    test = ts.iloc[train_size:]

    print(f"Datos totales: {len(ts)} | Train: {len(train)} | Test: {len(test)}")
    print("Buscando mejores parametros...")

    model = auto_arima(train, 
                        seasonal=True, m=3,
                        
                        # --- CONFIGURACIÓN BLINDADA ---
                        d=1,                 # Forzamos diferencia de tendencia (evita test KPSS/ADF)
                        D=1,                 # Forzamos diferencia estacional (evita test OCSB/CH)
                        test='ignore',       # Ignorar tests de estacionariedad
                        seasonal_test='ignore', # Ignorar tests estacionales
                        
                        # Mantenemos el modelo simple
                        start_p=0, start_q=0, max_p=1, max_q=1,
                        start_P=0, start_Q=0, max_P=1, max_Q=1,
                        
                        trace=True, 
                        error_action='ignore', 
                        suppress_warnings=True)
    print(f"Mejor modelo encontrado: {model.order} {model.seasonal_order}")

    # Prediccion
    prediction, conf_int = model.predict(n_periods=len(test), return_conf_int=True)
    prediction = pd.Series(prediction, index=test.index)

    # Evaluacion
    rmse = root_mean_squared_error(test, prediction)
    print(f"RMSE Error Cuadratido Medio): {rmse:.2f}")

    # Visualizacion
    plt.figure(figsize=(12, 6))
    plt.plot(train.index, train, label='Entrenamiento', color='blue')
    plt.plot(test.index, test, label='Realidad', color='green')
    plt.plot(prediction.index, prediction, label='Pronóstico SARIMA', color='red', linestyle='--')
    
    # Graficar intervalo de confianza (incertidumbre del modelo)
    plt.fill_between(test.index, conf_int[:, 0], conf_int[:, 1], color='pink', alpha=0.3)
    
    plt.title('SARIMA Forecast vs Realidad (RMSE Evaluation)')
    plt.legend()
    plt.savefig(filename)
    plt.close()
    print(f"Resultado final guardado en {filename}")

if __name__ == "__main__":
    df = cargando_datos()
    print(df.head(5))
    ts = transformando_datos(df)
    print(ts.head(12))
    # print(df_2.info())
    visualizacion_serie_tiempo(ts)
    descomposicion(ts)
    sarima_pipeline(ts)