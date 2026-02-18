import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import warnings

# librerías
from statsmodels.tsa.seasonal import seasonal_decompose
from pmdarima import auto_arima
from sklearn.metrics import mean_squared_error 

# configuración
plt.style.use('ggplot')
warnings.filterwarnings("ignore")


def cargar_datos(path="data/wine_sales.xlsx"):
    """
    cargando los datos
    """
    df = pd.read_excel(path)
    return df

def transformar_datos(df):
    """
    transformación Mensual y limpieza de outliers
    """
    # renombrar columnas
    nuevas_columnas = ['id', 'date_int', 'product_name', 'price', 'sales', 'reviews', 'brand', 'searches']
    df.columns = nuevas_columnas

    # agrupando por mes y sumando las ventas por mes    
    df['date'] = pd.to_datetime(df['date_int'], format='%Y%m')
    ventas_mensuales = df.groupby('date')['sales'].sum().sort_index()
    
    # frecuencia MS -> month start
    ventas_mensuales = ventas_mensuales.asfreq('MS')
    
    # reemplazamos 0 por NaN para interpolarlos
    ventas_mensuales = ventas_mensuales.replace(0, np.nan)
    
    # interpolamos los meses faltantes (con 0 ventas) antes de convertirlos a semanas
    ventas_mensuales = ventas_mensuales.interpolate(method='linear')
    
    # si quedaron na al inicio o al final, los llenamos con 0 
    ventas_mensuales = ventas_mensuales.fillna(0)

    ventas_mensuales.name = 'Ventas totales de vino por mes'
    print(f"Datos mensuales limpios: {len(ventas_mensuales)} meses.")
    return ventas_mensuales

def cambiar_meses_a_semanas(ts_monthly, filename='plots/1_augmentation_check.png'):
    """
    convirtiendo a semanal
    """
    print("refinando granularidad")
    ts_weekly = ts_monthly.resample('W').mean()
    
    try:
        ts_weekly = ts_weekly.interpolate(method='spline', order=2)
    except:
        ts_weekly = ts_weekly.interpolate(method='linear')
    
    ts_weekly = ts_weekly.clip(lower=0).round(0)
    ts_weekly.name = "Ventas de vino por semana"
    
    # visualizacion
    if not os.path.exists('plots'): os.makedirs('plots')
    plt.figure(figsize=(10, 4))
    plt.plot(ts_monthly.index, ts_monthly, 'o', color='red', label='Mensual Limpio')
    plt.plot(ts_weekly.index, ts_weekly, '-', color='blue', alpha=0.5, label='Semanal')
    plt.legend()
    plt.savefig(filename)
    print(f"Resultado guardado en: {filename}")
    plt.close()
    
    return ts_weekly

def analizar_decomposicion(ts, filename='plots/2_decomposition.png'):
    print("analizando Componentes")
    decomposition = seasonal_decompose(ts, model='additive', period=4)
    fig = decomposition.plot()
    fig.set_size_inches(10, 8)
    plt.tight_layout()
    plt.savefig(filename)
    print(f"Resultado guardado en: {filename}")
    plt.close()

def sarima_pipeline(ts, filename="plots/3_final_forecast.png"):
    """
    tranformacion logaritmica y modelo sarima
    """
    print("Iniciando modelado sarima")
    
    # conversion logaritmica
    # convertimos escala gigante (600k) a escala logarítmica (13.5)
    # Esto estabiliza la varianza y ayuda a ARIMA a converger mejor
    ts_log = np.log1p(ts) 
    
    # split
    test_weeks = 8
    train_log = ts_log.iloc[:-test_weeks]
    test_log = ts_log.iloc[-test_weeks:]
    
    # guardamos el test real(sin log) para calcular el error real al final
    test_real = ts.iloc[-test_weeks:]
    
    print(f"Train: {len(train_log)} | Test: {len(test_log)}")
    
    # auto-arima sobre datos log
    print("Entrenando modelo en espacio logarítmico...")
    model = auto_arima(train_log, 
                       seasonal=True, m=4, 
                       trace=True, 
                       error_action='ignore', 
                       suppress_warnings=True)
    
    print(f"mejor modelo: {model.order} {model.seasonal_order}")
    
    # forecast en log
    pred_log, conf_int_log = model.predict(n_periods=len(test_log), return_conf_int=True)
    
    # transformacion inversa
    # Regresamos de Log a Ventas Reales (np.expm1 es la inversa de np.log1p)
    prediction = pd.Series(np.expm1(pred_log), index=test_log.index)
    
    # Intervalos de confianza también se regresan
    lower_conf = np.expm1(conf_int_log[:, 0])
    upper_conf = np.expm1(conf_int_log[:, 1])
    
    # evaluacion sobre datos reales
    rmse = np.sqrt(mean_squared_error(test_real, prediction))
    print(f"RMSE MEJORADO: {rmse:.2f}")
    
    # visualizacion
    plt.figure(figsize=(12, 6))
    
    # graficacion en escala real
    train_real = ts.iloc[:-test_weeks]
    
    plt.plot(train_real.index, train_real, label='Historia', color='blue')
    plt.plot(test_real.index, test_real, label='Realidad', color='green', linewidth=2)
    plt.plot(prediction.index, prediction, label='Pronóstico SARIMA (Log)', color='red', linestyle='--')
    
    plt.fill_between(test_real.index, lower_conf, upper_conf, color='pink', alpha=0.3)
    plt.title(f'Pronóstico Optimizado (Log-Transform + Imputación) | RMSE: {rmse:.2f}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.savefig('plots/3_final_forecast_pro.png')
    plt.close()
    print(f"Resultado guardado en: {filename}")

if __name__ == "__main__":
    print("PIPELINE")
    
    df = cargar_datos()
    ts_monthly = transformar_datos(df)       
    ts_weekly = cambiar_meses_a_semanas(ts_monthly)
    analizar_decomposicion(ts_weekly)
    sarima_pipeline(ts_weekly)        
        
