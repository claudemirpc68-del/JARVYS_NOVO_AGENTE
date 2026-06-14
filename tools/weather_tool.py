import logging
import httpx

logger = logging.getLogger(__name__)

# Tabela de códigos meteorológicos da OMM (WMO Weather Codes)
WMO_CODES = {
    0: "Céu limpo ☀️",
    1: "Principalmente limpo 🌤️",
    2: "Parcialmente nublado ⛅",
    3: "Encoberto ☁️",
    45: "Nevoeiro 🌫️",
    48: "Nevoeiro com formação de geada 🌫️❄️",
    51: "Chuvisco leve 🌧️",
    53: "Chuvisco moderado 🌧️",
    55: "Chuvisco denso 🌧️",
    56: "Chuvisco congelante leve 🌧️❄️",
    57: "Chuvisco congelante denso 🌧️❄️",
    61: "Chuva fraca 🌧️",
    63: "Chuva moderada 🌧️",
    65: "Chuva forte 🌧️",
    66: "Chuva congelante leve 🌧️❄️",
    67: "Chuva congelante forte 🌧️❄️",
    71: "Queda de neve fraca ❄️",
    73: "Queda de neve moderada ❄️",
    75: "Queda de neve forte ❄️",
    77: "Grãos de neve ❄️",
    80: "Pancadas de chuva fracas 🌦️",
    81: "Pancadas de chuva moderadas 🌦️",
    82: "Pancadas de chuva violentas ⛈️",
    85: "Pancadas de neve fracas 🌨️",
    86: "Pancadas de neve fortes 🌨️",
    95: "Tempestade leve ou moderada ⛈️",
    96: "Tempestade com granizo leve ⛈️🌨️",
    99: "Tempestade com granizo forte ⛈️🌨️"
}

def get_condition_desc(code: int) -> str:
    """Retorna a descrição textual em português a partir do código WMO"""
    return WMO_CODES.get(code, "Condição desconhecida 🌤️")

async def get_weather(location: str) -> str:
    """
    Busca a latitude e longitude da localização usando a Geocoding API do Open-Meteo
    e depois consulta a previsão do tempo no Open-Meteo Forecast.
    Retorna uma string em linguagem natural contendo o relatório do tempo.
    """
    if not location or not location.strip():
        return "Por favor, informe uma cidade para consultar a previsão do tempo."

    location = location.strip()
    logger.info(f"Buscando coordenadas de geolocalização para: '{location}'...")

    # 1. Geocodificação (Cidade para Lat/Lon)
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=pt"
    
    try:
        async with httpx.AsyncClient() as client:
            geo_resp = await client.get(geo_url, timeout=15.0)
            
            if geo_resp.status_code != 200:
                logger.error(f"Erro na Geocoding API do Open-Meteo ({geo_resp.status_code}): {geo_resp.text}")
                return f"Desculpe, não consegui consultar a geolocalização para '{location}' no momento."

            geo_data = geo_resp.json()
            results = geo_data.get("results")
            
            if not results or len(results) == 0:
                logger.warning(f"Nenhum resultado de geolocalização encontrado para '{location}'.")
                return f"Não encontrei nenhuma cidade chamada '{location}'. Por favor, verifique se a grafia está correta."

            # Extrair o primeiro resultado
            match = results[0]
            lat = match.get("latitude")
            lon = match.get("longitude")
            city_name = match.get("name")
            country = match.get("country", "")
            admin1 = match.get("admin1", "")  # Estado/Província
            
            display_name = city_name
            if admin1:
                display_name += f", {admin1}"
            if country:
                display_name += f", {country}"

            logger.info(f"Coordenadas encontradas para '{location}': Lat {lat}, Lon {lon} ({display_name})")

            # 2. Obter previsão do tempo usando as coordenadas
            forecast_url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                "timezone": "auto"
            }

            weather_resp = await client.get(forecast_url, params=params, timeout=15.0)

            if weather_resp.status_code != 200:
                logger.error(f"Erro na Forecast API do Open-Meteo ({weather_resp.status_code}): {weather_resp.text}")
                return f"Desculpe, não consegui obter os dados meteorológicos para '{display_name}' no momento."

            weather_data = weather_resp.json()
            current = weather_data.get("current")

            if not current:
                logger.error(f"Formato de resposta meteorológica inválido: {weather_data}")
                return "Desculpe, a resposta da previsão do tempo veio em formato inválido."

            temp = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            apparent_temp = current.get("apparent_temperature")
            precip = current.get("precipitation", 0.0)
            weather_code = current.get("weather_code", 0)
            wind_speed = current.get("wind_speed_10m")

            condition = get_condition_desc(weather_code)

            # Formatar o relatório final do tempo
            report = (
                f"🌤️ **Previsão do Tempo para {display_name}**:\n\n"
                f"• **Condição**: {condition}\n"
                f"• **Temperatura atual**: {temp}°C\n"
                f"• **Sensação térmica**: {apparent_temp}°C\n"
                f"• **Umidade relativa**: {humidity}%\n"
                f"• **Vento**: {wind_speed} km/h\n"
                f"• **Precipitação**: {precip} mm"
            )

            logger.info(f"Relatório meteorológico gerado com sucesso para {display_name}.")
            return report

    except Exception as e:
        logger.error(f"Falha de comunicação ou processamento da skill de clima para '{location}': {e}")
        return f"Desculpe, ocorreu um erro ao consultar o clima de '{location}'. Detalhe: {str(e)}"
