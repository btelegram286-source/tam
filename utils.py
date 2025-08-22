# -*- coding: utf-8 -*-
import os
import io
import requests
from PIL import Image
import qrcode
from gtts import gTTS
import pyttsx3
from pydub import AudioSegment
import python_weather
import forex_python.converter
from forex_python.bitcoin import BtcConverter
import logging

logger = logging.getLogger(__name__)

def generate_qr_code(data, filename='qrcode.png'):
    """QR kodu oluştur"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        return filename
    except Exception as e:
        logger.error(f"QR kodu oluşturma hatası: {e}")
        return None

def text_to_speech(text, lang='tr', filename='speech.mp3'):
    """Metni sese çevir"""
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filename)
        return filename
    except Exception as e:
        logger.error(f"Metin okuma hatası: {e}")
        return None

def convert_audio_format(input_file, output_format='mp3'):
    """Ses dosyası formatını dönüştür"""
    try:
        audio = AudioSegment.from_file(input_file)
        output_file = f"converted.{output_format}"
        audio.export(output_file, format=output_format)
        return output_file
    except Exception as e:
        logger.error(f"Ses dönüştürme hatası: {e}")
        return None

def get_weather(city='Istanbul'):
    """Hava durumu bilgisi al"""
    try:
        # OpenWeatherMap API kullanarak basit hava durumu
        api_key = "demo"  # Demo amaçlı
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=tr"
        
        # Basit mock data döndür (gerçek API key olmadığı için)
        weather_info = {
            'city': city,
            'temperature': 22,
            'description': 'Açık',
            'humidity': 65,
            'wind_speed': 5.2,
            'feels_like': 24
        }
        return weather_info
    except Exception as e:
        logger.error(f"Hava durumu hatası: {e}")
        return None

def get_exchange_rate(from_currency='USD', to_currency='TRY'):
    """Döviz kuru al"""
    try:
        # Demo amaçlı mock data
        rates = {
            'USD_TRY': 34.25,
            'EUR_TRY': 37.15,
            'GBP_TRY': 43.80,
            'USD_EUR': 0.92,
            'EUR_USD': 1.09
        }
        
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key in rates:
            return rates[rate_key]
        else:
            return 34.25  # Varsayılan USD/TRY
    except Exception as e:
        logger.error(f"Döviz kuru hatası: {e}")
        return None

def get_bitcoin_price(currency='USD'):
    """Bitcoin fiyatı al"""
    try:
        # Demo amaçlı mock data
        prices = {
            'USD': 67500.00,
            'TRY': 2310000.00,
            'EUR': 62100.00
        }
        
        return prices.get(currency, 67500.00)
    except Exception as e:
        logger.error(f"Bitcoin fiyat hatası: {e}")
        return None

def resize_image(input_path, output_path, size=(800, 600)):
    """Görsel boyutlandır"""
    try:
        with Image.open(input_path) as img:
            img = img.resize(size, Image.Resampling.LANCZOS)
            img.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"Görsel boyutlandırma hatası: {e}")
        return None

def generate_ai_image(prompt, size="1024x1024"):
    """AI ile görsel oluştur"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        logger.error(f"AI görsel oluşturma hatası: {e}")
        return None

def download_file_from_url(url, filename):
    """URL'den dosya indir"""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return filename
        return None
    except Exception as e:
        logger.error(f"Dosya indirme hatası: {e}")
        return None
