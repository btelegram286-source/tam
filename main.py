# -*- coding: utf-8 -*-
import os
import logging
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import telebot
from telebot import types
from github import Github
import openai
import youtube_dl
from bs4 import BeautifulSoup
import utils
from github_manager import GitHubManager
from render_manager import RenderManager
from scheduler import BotScheduler
from premium_features import PremiumFeatures

# ENV YÜKLE
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.env")
load_dotenv(config_path)

# API ANAHTARLARI
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USER = os.getenv("GITHUB_USER")
OPENAI_API_KEY = os.getenv("OPENAI_KEY")
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_OWNER_ID")  # RENDER_OWNER_ID olarak değiştirildi

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# TELEGRAM BOT
bot = telebot.TeleBot(BOT_TOKEN)

# OPENAI KURULUM
if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
    openai.api_key = OPENAI_API_KEY
    AI_ENABLED = True
else:
    AI_ENABLED = False
    logger.warning("OpenAI API anahtarı bulunamadı. AI özellikleri devre dışı.")

# GITHUB KURULUM
if GITHUB_TOKEN:
    try:
        github = Github(GITHUB_TOKEN)
        github_manager = GitHubManager(GITHUB_TOKEN, GITHUB_USER)
        GITHUB_ENABLED = True
    except Exception as e:
        logger.error(f"GitHub bağlantı hatası: {e}")
        GITHUB_ENABLED = False
        github_manager = None
else:
    GITHUB_ENABLED = False
    github_manager = None
    logger.warning("GitHub token bulunamadı. GitHub özellikleri devre dışı.")

# RENDER KURULUM
if RENDER_API_KEY and RENDER_SERVICE_ID:
    try:
        render_manager = RenderManager(RENDER_API_KEY, RENDER_SERVICE_ID)
        RENDER_ENABLED = True
    except Exception as e:
        logger.error(f"Render bağlantı hatası: {e}")
        RENDER_ENABLED = False
        render_manager = None
else:
    RENDER_ENABLED = False
    render_manager = None
    logger.warning("Render API anahtarları bulunamadı. Render özellikleri devre dışı.")

# SCHEDULER KURULUM
scheduler = None
if github_manager and render_manager:
    try:
        scheduler = BotScheduler(bot, github_manager, render_manager)
        SCHEDULER_ENABLED = True
    except Exception as e:
        logger.error(f"Scheduler kurulum hatası: {e}")
        SCHEDULER_ENABLED = False
else:
    SCHEDULER_ENABLED = False
    logger.warning("Scheduler için gerekli bileşenler eksik.")

# PREMIUM FEATURES KURULUM
try:
    premium = PremiumFeatures()
    PREMIUM_ENABLED = True
    logger.info("✅ Premium özellikler aktif!")
except Exception as e:
    logger.error(f"Premium features kurulum hatası: {e}")
    PREMIUM_ENABLED = False
    premium = None

# AI 429 cooldown kontrolü (saniye cinsinden epoch zaman)
AI_COOLDOWN_UNTIL = 0

# YARDIMCI FONKSİYONLAR
def get_ai_response(prompt):
    """OpenAI ile sohbet cevabı al"""
    if not AI_ENABLED:
        return "❌ OpenAI servisi şu anda kullanılamıyor."
    
    # 429 sonrası cooldown kontrolü
    try:
        global AI_COOLDOWN_UNTIL
        now = time.time()
        if now < AI_COOLDOWN_UNTIL:
            remaining = int((AI_COOLDOWN_UNTIL - now) // 60) + 1
            return f"❌ OpenAI kullanım limiti geçici olarak doldu. Lütfen {remaining} dk sonra tekrar deneyin."
    except Exception:
        # Her ihtimale karşı cooldown hataları sessiz geçilir
        pass

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e).lower()
        # 429 veya kota/limit -> cooldown başlat
        if "429" in error_msg or "quota" in error_msg or "limit" in error_msg:
            try:
                AI_COOLDOWN_UNTIL = time.time() + 10 * 60  # 10 dakika
            except Exception:
                pass
            return "❌ OpenAI kotası dolmuş veya çok fazla istek gönderildi. 10 dk sonra tekrar deneyin."
        elif "invalid" in error_msg and "key" in error_msg:
            return "❌ OpenAI API anahtarı geçersiz. Lütfen yönetici ile iletişime geçin."
        elif "rate" in error_msg:
            return "❌ Çok fazla istek gönderildi. Lütfen birkaç saniye bekleyin ve tekrar deneyin."
        else:
            return f"❌ AI hatası: {str(e)}"

def github_push_to_repo(repo_name, file_content, file_name="bot_update.py"):
    """GitHub'a dosya push et"""
    if not GITHUB_ENABLED:
        return "❌ GitHub servisi şu anda kullanılamıyor."
    
    try:
        user = github.get_user()
        try:
            repo = user.get_repo(repo_name)
        except:
            repo = user.create_repo(repo_name)
        
        try:
            contents = repo.get_contents(file_name)
            repo.update_file(contents.path, f"Update {file_name}", file_content, contents.sha)
            return f"✅ {file_name} dosyası güncellendi!"
        except:
            repo.create_file(file_name, f"Create {file_name}", file_content)
            return f"✅ {file_name} dosyası oluşturuldu!"
    except Exception as e:
        return f"❌ GitHub hatası: {str(e)}"

def download_youtube_audio(url):
    """YouTube'dan audio indir"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'downloads/%(title)s.%(ext)s',
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return f"✅ İndirme tamamlandı: {info['title']}"
    except Exception as e:
        return f"❌ İndirme hatası: {str(e)}"

# KOMUTLAR
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Kullanıcıyı veritabanına ekle
    if PREMIUM_ENABLED and premium is not None:
        try:
            premium.add_user(
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name
            )
        except Exception as e:
            logger.error(f"Kullanıcı ekleme hatası: {e}")
    
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    buttons = [
        "🤖 AI Sohbet",
        "📁 GitHub Yönetimi", 
        "🔄 Render Yönetimi",
        "🎵 YouTube İndir",
        "📊 Bot Durumu",
        "🌤️ Hava Durumu",
        "💱 Döviz Kuru",
        "₿ Bitcoin",
        "🔗 QR Kod",
        "🎤 Ses Çevir",
        "🖼️ AI Görsel",
        "📝 Makale Yaz",
        "🌍 Çeviri",
        "🔐 Şifre Üret",
        "📋 Notlarım",
        "⏰ Hatırlatıcı",
        "🧮 Hesap Makinesi",
        "🔗 URL Kısalt",
        "💭 Motivasyon",
        "📈 İstatistiklerim"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    
    welcome_text = """
    🚀 *ReisBot Premium'a Hoşgeldin!*

    *🎯 SÜPER PREMIUM ÖZELLİKLER:*
    
    **🤖 AI & Automation:**
    • Yapay Zeka Sohbeti & Görsel Üretme
    • GitHub Tam Yönetimi (CRUD, Commits)
    • Render Otomatik Deploy & Monitoring
    • 7/24 Cron Job Sistemi
    
    **📝 Content & Productivity:**
    • Makale/Blog Yazma Asistanı
    • 50+ Dil Çeviri Servisi
    • Güvenli Şifre Üretici
    • Kişisel Not Defteri
    • Akıllı Hatırlatıcı Sistemi
    
    **🛠️ Utilities & Tools:**
    • Gelişmiş Hesap Makinesi
    • URL Kısaltma Servisi
    • QR Kod & Ses İşleme
    • Hava Durumu & Finans Takibi
    • Günlük Motivasyon Sözleri
    
    **📊 Analytics & Stats:**
    • Kişisel Kullanım İstatistikleri
    • Sistem Performans Raporları
    • Otomatik Yedekleme & Sync

    /help ile tüm komutları görebilirsin!
    """
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
    *🤖 ReisBot Premium Komutları:*

    */start* - Botu başlat
    */help* - Yardım menüsü
    */status* - Bot durumu

    *AI & Medya:*
    */ai <soru>* - AI ile sohbet et
    */image <prompt>* - AI görsel oluştur
    */yt <url>* - YouTube'dan indir
    */tts <metin>* - Metni sese çevir

    *GitHub & Deploy:*
    */github <repo> <dosya>* - GitHub'a dosya push et
    */autodeploy <repo> [zip]* - Otomatik repo oluştur & deploy

    *Bilgi & Araçlar:*
    */weather <şehir>* - Hava durumu
    */exchange <from> <to>* - Döviz kuru
    */bitcoin* - Bitcoin fiyatı
    */qr <metin>* - QR kod oluştur
    */calc <ifade>* - Hesap makinesi (örn: 2*(3+4))
    */translate <dil> <metin>* - Çeviri (örn: en merhaba dünya)
    */shorten <url>* - URL kısalt
    */password <uzunluk> <evet/hayır>* - Şifre üret (semboller)

    *Not & Hatırlatıcı:*
    */notes* - Notlarımı listele
    */addnote <başlık> | <içerik>* - Not ekle
    */delnote <id>* - Not sil
    */remind <YYYY-MM-DD HH:MM> | <mesaj>* - Hatırlatıcı ekle
    */reminders* - Hatırlatıcıları listele
    */motivate* - Günün sözü
    */mystats* - Kullanım istatistiklerim

    *Buton Özellikleri:*
    • 🤖 AI Sohbet
    • 📁 GitHub Yönetimi
    • 🔄 Render Yönetimi
    • 🎵 YouTube İndir
    • 🌤️ Hava Durumu
    • 💱 Döviz Kuru
    • ₿ Bitcoin
    • 🔗 QR Kod
    • 🎤 Ses Çevir
    • 🖼️ AI Görsel
    • 🧮 Hesap Makinesi
    • 🌍 Çeviri
    • 🔗 URL Kısalt
    • 🔐 Şifre Üret
    • 📋 Notlarım
    • ⏰ Hatırlatıcı
    • 💭 Motivasyon
    • 📈 İstatistiklerim
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['ai'])
def ai_chat(message):
    try:
        question = message.text.replace("/ai", "").strip()
        if not question:
            bot.reply_to(message, "❌ Lütfen bir soru yaz reis. Örnek: /ai Python nedir?")
            return
        
        bot.send_chat_action(message.chat.id, 'typing')
        response = get_ai_response(question)
        
        # Split long responses
        if len(response) > 4096:
            # Telegram message limit is 4096 characters
            for i in range(0, len(response), 4096):
                chunk = response[i:i+4096]
                if i == 0:
                    bot.reply_to(message, chunk)
                else:
                    bot.send_message(message.chat.id, chunk)
        else:
            bot.reply_to(message, response)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['github'])
def github_command(message):
    if not GITHUB_ENABLED:
        bot.reply_to(message, "❌ GitHub servisi şu anda kullanılamıyor.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "❌ Kullanım: /github <repo_adi> <dosya_adi>")
            return
        
        repo_name = parts[1]
        file_name = parts[2]
        
        # Örnek dosya içeriği
        file_content = f"""
# {file_name} - Otomatik oluşturuldu
# Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

print("Merhaba ReisBot!")
print("Bu dosya otomatik olarak oluşturuldu.")
"""
        
        result = github_push_to_repo(repo_name, file_content, file_name)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ GitHub hatası: {str(e)}")

@bot.message_handler(commands=['autodeploy'])
def auto_deploy_command(message):
    """Otomatik GitHub repo oluştur ve Render'a deploy et"""
    if not GITHUB_ENABLED or not RENDER_ENABLED:
        bot.reply_to(message, "❌ GitHub veya Render servisi şu anda kullanılamıyor.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Kullanım: /autodeploy <repo_adi> [zip_dosya_yolu]")
            return
        
        repo_name = parts[1]
        zip_file_path = parts[2] if len(parts) > 2 else None
        
        bot.send_chat_action(message.chat.id, 'typing')
        
        # 1. GitHub'da yeni repo oluştur
        bot.send_message(message.chat.id, f"🔄 GitHub'da yeni repository oluşturuluyor: {repo_name}...")
        repo_result = github_manager.create_repository(repo_name, f"Otomatik oluşturulan repo: {repo_name}")
        
        if "❌" in repo_result:
            bot.reply_to(message, repo_result)
            return
        
        bot.send_message(message.chat.id, "✅ Repository başarıyla oluşturuldu!")
        
        # 2. Eğer zip dosyası varsa, dosyaları yükle
        if zip_file_path and os.path.exists(zip_file_path):
            bot.send_message(message.chat.id, f"📦 Zip dosyası yükleniyor: {zip_file_path}...")
            upload_result = github_manager.upload_zip_to_repo(repo_name, zip_file_path)
            bot.send_message(message.chat.id, f"📤 Zip yükleme sonucu:\n{upload_result}")
        else:
            # Varsayılan dosyaları yükle
            bot.send_message(message.chat.id, "📁 Varsayılan bot dosyaları yükleniyor...")
            upload_result = github_manager.upload_current_bot(repo_name)
            bot.send_message(message.chat.id, f"📤 Dosya yükleme sonucu:\n{upload_result}")
        
        # 3. Render'da otomatik servis oluştur ve deploy et
        github_repo_url = f"https://github.com/{GITHUB_USER}/{repo_name}"
        bot.send_message(message.chat.id, f"🚀 Render'da yeni servis oluşturuluyor: {repo_name}...")
        
        deploy_result = render_manager.auto_create_and_deploy(repo_name, github_repo_url)
        
        final_result = f"""
🎉 *Otomatik Deploy Tamamlandı!*

📁 *GitHub:*
{repo_result}

📤 *Dosya Yükleme:*
{upload_result}

🚀 *Render Deploy:*
{deploy_result}

✅ Tüm işlemler başarıyla tamamlandı!
        """
        
        bot.reply_to(message, final_result, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Otomatik deploy hatası: {str(e)}")

@bot.message_handler(commands=['yt'])
def youtube_download(message):
    try:
        url = message.text.replace("/yt", "").strip()
        if not url:
            bot.reply_to(message, "❌ Lütfen YouTube URL'si yaz. Örnek: /yt https://youtube.com/...")
            return
        
        if "youtube.com" not in url and "youtu.be" not in url:
            bot.reply_to(message, "❌ Geçerli bir YouTube URL'si girmelisin.")
            return
        
        bot.send_chat_action(message.chat.id, 'upload_document')
        result = download_youtube_audio(url)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ İndirme hatası: {str(e)}")

@bot.message_handler(commands=['status'])
def bot_status(message):
    status_text = f"""
    📊 *ReisBot Durumu*

    *Bot:* ✅ Çalışıyor
    *AI Servis:* {'✅ Aktif' if AI_ENABLED else '❌ Devre Dışı'}
    *GitHub:* {'✅ Bağlı' if GITHUB_ENABLED else '❌ Bağlantı Yok'}
    *Zaman:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    *Chat ID:* {message.chat.id}
    """
    bot.reply_to(message, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['weather'])
def weather_command(message):
    try:
        city = message.text.replace("/weather", "").strip()
        if not city:
            city = "Istanbul"
        
        bot.send_chat_action(message.chat.id, 'typing')
        weather_info = utils.get_weather(city)
        
        if weather_info:
            weather_text = f"""
🌤️ *{weather_info['city']} Hava Durumu*

🌡️ *Sıcaklık:* {weather_info['temperature']}°C
🌡️ *Hissedilen:* {weather_info['feels_like']}°C
☁️ *Durum:* {weather_info['description']}
💧 *Nem:* {weather_info['humidity']}%
💨 *Rüzgar:* {weather_info['wind_speed']} km/h
            """
            bot.reply_to(message, weather_text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Hava durumu bilgisi alınamadı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['exchange'])
def exchange_command(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            # Varsayılan USD/TRY
            from_currency = "USD"
            to_currency = "TRY"
        else:
            from_currency = parts[1].upper()
            to_currency = parts[2].upper()
        
        bot.send_chat_action(message.chat.id, 'typing')
        rate = utils.get_exchange_rate(from_currency, to_currency)
        
        if rate:
            exchange_text = f"""
💱 *Döviz Kuru*

1 {from_currency} = {rate:.4f} {to_currency}

📊 Güncel kur bilgisi
            """
            bot.reply_to(message, exchange_text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Döviz kuru bilgisi alınamadı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['bitcoin'])
def bitcoin_command(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        btc_usd = utils.get_bitcoin_price('USD')
        btc_try = utils.get_bitcoin_price('TRY')
        
        if btc_usd and btc_try:
            bitcoin_text = f"""
₿ *Bitcoin Fiyatı*

💵 *USD:* ${btc_usd:,.2f}
💰 *TRY:* ₺{btc_try:,.2f}

📊 Güncel Bitcoin fiyatı
            """
            bot.reply_to(message, bitcoin_text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Bitcoin fiyat bilgisi alınamadı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['qr'])
def qr_command(message):
    try:
        text = message.text.replace("/qr", "").strip()
        if not text:
            bot.reply_to(message, "❌ QR kod için metin yaz. Örnek: /qr https://google.com")
            return
        
        bot.send_chat_action(message.chat.id, 'upload_photo')
        qr_file = utils.generate_qr_code(text, f"qr_{message.chat.id}.png")
        
        if qr_file and os.path.exists(qr_file):
            with open(qr_file, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"🔗 QR Kod: {text}")
            os.remove(qr_file)  # Dosyayı temizle
        else:
            bot.reply_to(message, "❌ QR kod oluşturulamadı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['tts'])
def tts_command(message):
    try:
        text = message.text.replace("/tts", "").strip()
        if not text:
            bot.reply_to(message, "❌ Okutulacak metni yaz. Örnek: /tts Merhaba dünya")
            return
        
        bot.send_chat_action(message.chat.id, 'upload_audio')
        audio_file = utils.text_to_speech(text, 'tr', f"tts_{message.chat.id}.mp3")
        
        if audio_file and os.path.exists(audio_file):
            with open(audio_file, 'rb') as audio:
                bot.send_audio(message.chat.id, audio, caption=f"🎤 Metin: {text}")
            os.remove(audio_file)  # Dosyayı temizle
        else:
            bot.reply_to(message, "❌ Ses dosyası oluşturulamadı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

@bot.message_handler(commands=['image'])
def image_command(message):
    try:
        prompt = message.text.replace("/image", "").strip()
        if not prompt:
            bot.reply_to(message, "❌ Görsel için açıklama yaz. Örnek: /image güzel bir manzara")
            return
        
        bot.send_chat_action(message.chat.id, 'upload_photo')
        image_url = utils.generate_ai_image(prompt)
        
        if image_url:
            # Görseli indir ve gönder
            image_file = utils.download_file_from_url(image_url, f"ai_image_{message.chat.id}.png")
            if image_file and os.path.exists(image_file):
                with open(image_file, 'rb') as photo:
                    bot.send_photo(message.chat.id, photo, caption=f"🖼️ AI Görsel: {prompt}")
                os.remove(image_file)  # Dosyayı temizle
            else:
                bot.reply_to(message, f"🖼️ AI Görsel: {prompt}\n\n{image_url}")
        else:
            bot.reply_to(message, "❌ AI görsel oluşturulamadı.")
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

# BUTON İŞLEMLERİ
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text == "🤖 AI Sohbet":
        msg = bot.reply_to(message, "🤖 Sorunu yaz reis, AI cevaplayacak:")
        bot.register_next_step_handler(msg, process_ai_question)
    
    elif message.text == "📁 GitHub Yönetimi":
        if GITHUB_ENABLED:
            show_github_menu(message)
        else:
            bot.reply_to(message, "❌ GitHub servisi devre dışı!")
    
    elif message.text == "🔄 Render Yönetimi":
        if RENDER_ENABLED:
            show_render_menu(message)
        else:
            bot.reply_to(message, "❌ Render servisi devre dışı!")
    
    elif message.text == "🎵 YouTube İndir":
        msg = bot.reply_to(message, "🎵 YouTube URL'si yaz:")
        bot.register_next_step_handler(msg, process_youtube_download)
    
    elif message.text == "📊 Bot Durumu":
        bot_status(message)
    
    elif message.text == "🌤️ Hava Durumu":
        msg = bot.reply_to(message, "🌤️ Hangi şehrin hava durumunu öğrenmek istiyorsun? (Varsayılan: İstanbul)")
        bot.register_next_step_handler(msg, process_weather_request)
    
    elif message.text == "💱 Döviz Kuru":
        msg = bot.reply_to(message, "💱 Hangi döviz kurunu öğrenmek istiyorsun? (örn: USD TRY veya boş bırak)")
        bot.register_next_step_handler(msg, process_exchange_request)
    
    elif message.text == "₿ Bitcoin":
        bitcoin_command(message)
    
    elif message.text == "🔗 QR Kod":
        msg = bot.reply_to(message, "🔗 QR kod için metin veya URL yaz:")
        bot.register_next_step_handler(msg, process_qr_request)
    
    elif message.text == "🎤 Ses Çevir":
        msg = bot.reply_to(message, "🎤 Okutulacak metni yaz:")
        bot.register_next_step_handler(msg, process_tts_request)
    
    elif message.text == "🖼️ AI Görsel":
        msg = bot.reply_to(message, "🖼️ Oluşturulacak görselin açıklamasını yaz:")
        bot.register_next_step_handler(msg, process_image_request)

    elif message.text == "🧮 Hesap Makinesi":
        msg = bot.reply_to(message, "🧮 İfadeyi yaz (örn: 2*(3+4)):")
        bot.register_next_step_handler(msg, process_calc_request)

    elif message.text == "🌍 Çeviri":
        msg = bot.reply_to(message, "🌍 Hedef dil ve metni yaz (örn: en merhaba dünya):")
        bot.register_next_step_handler(msg, process_translate_request)

    elif message.text == "🔗 URL Kısalt":
        msg = bot.reply_to(message, "🔗 Kısaltılacak URL'yi yaz:")
        bot.register_next_step_handler(msg, process_shorten_request)

    elif message.text == "🔐 Şifre Üret":
        msg = bot.reply_to(message, "🔐 Uzunluk ve semboller (örn: 12 evet/hayır):")
        bot.register_next_step_handler(msg, process_password_request)

    elif message.text == "📋 Notlarım":
        # Notları listele ve ekleme için prompt ver
        process_list_notes(message)
        msg = bot.reply_to(message, "📝 Yeni not eklemek için 'Başlık | İçerik' yaz:")
        bot.register_next_step_handler(msg, process_addnote_request)

    elif message.text == "⏰ Hatırlatıcı":
        msg = bot.reply_to(message, "⏰ Tarih/Saat ve mesaj yaz (örn: 2025-08-31 09:00 | toplantı):")
        bot.register_next_step_handler(msg, process_remind_request)

    elif message.text == "💭 Motivasyon":
        process_motivate(message)

    elif message.text == "📈 İstatistiklerim":
        process_mystats(message)
    
    else:
        bot.reply_to(message, "❌ Anlamadım reis. /help yazabilirsin.")

def process_ai_question(message):
    bot.send_chat_action(message.chat.id, 'typing')
    response = get_ai_response(message.text)
    
    # Split long responses
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            chunk = response[i:i+4096]
            if i == 0:
                bot.reply_to(message, chunk)
            else:
                bot.send_message(message.chat.id, chunk)
    else:
        bot.reply_to(message, response)

def process_github_push(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Repo adı ve dosya adı gerekli!")
            return
        
        repo_name = parts[0]
        file_name = parts[1] if len(parts) > 1 else "bot_file.py"
        
        file_content = f"""
# {file_name} - ReisBot tarafından oluşturuldu
# Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

def main():
    print("ReisBot GitHub Push başarılı!")
    
if __name__ == "__main__":
    main()
"""
        
        result = github_push_to_repo(repo_name, file_content, file_name)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)}")

def process_youtube_download(message):
    url = message.text.strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        bot.reply_to(message, "❌ Geçerli YouTube URL'si gerekli!")
        return
    
    bot.send_chat_action(message.chat.id, 'upload_document')
    result = download_youtube_audio(url)
    bot.reply_to(message, result)

def process_weather_request(message):
    city = message.text.strip()
    if not city:
        city = "Istanbul"
    
    bot.send_chat_action(message.chat.id, 'typing')
    weather_info = utils.get_weather(city)
    
    if weather_info:
        weather_text = f"""
🌤️ *{weather_info['city']} Hava Durumu*

🌡️ *Sıcaklık:* {weather_info['temperature']}°C
🌡️ *Hissedilen:* {weather_info['feels_like']}°C
☁️ *Durum:* {weather_info['description']}
💧 *Nem:* {weather_info['humidity']}%
💨 *Rüzgar:* {weather_info['wind_speed']} km/h
        """
        bot.reply_to(message, weather_text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Hava durumu bilgisi alınamadı.")

def process_exchange_request(message):
    text = message.text.strip()
    if not text:
        from_currency = "USD"
        to_currency = "TRY"
    else:
        parts = text.split()
        if len(parts) >= 2:
            from_currency = parts[0].upper()
            to_currency = parts[1].upper()
        else:
            from_currency = "USD"
            to_currency = "TRY"
    
    bot.send_chat_action(message.chat.id, 'typing')
    rate = utils.get_exchange_rate(from_currency, to_currency)
    
    if rate:
        exchange_text = f"""
💱 *Döviz Kuru*

1 {from_currency} = {rate:.4f} {to_currency}

📊 Güncel kur bilgisi
        """
        bot.reply_to(message, exchange_text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Döviz kuru bilgisi alınamadı.")

def process_qr_request(message):
    text = message.text.strip()
    if not text:
        bot.reply_to(message, "❌ QR kod için metin gerekli!")
        return
    
    bot.send_chat_action(message.chat.id, 'upload_photo')
    qr_file = utils.generate_qr_code(text, f"qr_{message.chat.id}.png")
    
    if qr_file and os.path.exists(qr_file):
        with open(qr_file, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"🔗 QR Kod: {text}")
        os.remove(qr_file)
    else:
        bot.reply_to(message, "❌ QR kod oluşturulamadı.")

def process_tts_request(message):
    text = message.text.strip()
    if not text:
        bot.reply_to(message, "❌ Okutulacak metin gerekli!")
        return
    
    bot.send_chat_action(message.chat.id, 'upload_audio')
    audio_file = utils.text_to_speech(text, 'tr', f"tts_{message.chat.id}.mp3")
    
    if audio_file and os.path.exists(audio_file):
        with open(audio_file, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, caption=f"🎤 Metin: {text}")
        os.remove(audio_file)
    else:
        bot.reply_to(message, "❌ Ses dosyası oluşturulamadı.")

def process_image_request(message):
    prompt = message.text.strip()
    if not prompt:
        bot.reply_to(message, "❌ Görsel açıklaması gerekli!")
        return
    
    bot.send_chat_action(message.chat.id, 'upload_photo')
    image_url = utils.generate_ai_image(prompt)
    
    if image_url:
        # Görseli indir ve gönder
        image_file = utils.download_file_from_url(image_url, f"ai_image_{message.chat.id}.png")
        if image_file and os.path.exists(image_file):
            with open(image_file, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"🖼️ AI Görsel: {prompt}")
            os.remove(image_file)  # Dosyayı temizle
        else:
            bot.reply_to(message, f"🖼️ AI Görsel: {prompt}\n\n{image_url}")
    else:
        bot.reply_to(message, "❌ AI görsel oluşturulamadı.")

# GITHUB YÖNETİMİ FONKSİYONLARI
def show_github_menu(message):
    """GitHub yönetim menüsünü göster"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("📋 Repo Listesi", callback_data="github_list_repos"),
        types.InlineKeyboardButton("📁 Dosya Listesi", callback_data="github_list_files"),
        types.InlineKeyboardButton("📤 Dosya Yükle", callback_data="github_upload_file"),
        types.InlineKeyboardButton("🗑️ Dosya Sil", callback_data="github_delete_file"),
        types.InlineKeyboardButton("📝 Dosya Güncelle", callback_data="github_update_file"),
        types.InlineKeyboardButton("📜 Commit Geçmişi", callback_data="github_commits"),
        types.InlineKeyboardButton("🔄 Bot'u Yükle", callback_data="github_upload_bot"),
        types.InlineKeyboardButton("❌ Kapat", callback_data="close_menu")
    ]
    markup.add(*buttons)
    
    menu_text = """
📁 *GitHub Yönetim Paneli*

Yapmak istediğin işlemi seç:
• 📋 Repo Listesi - Tüm repolarını görüntüle
• 📁 Dosya Listesi - Repo dosyalarını listele
• 📤 Dosya Yükle - Yeni dosya oluştur
• 🗑️ Dosya Sil - Dosya sil
• 📝 Dosya Güncelle - Mevcut dosyayı güncelle
• 📜 Commit Geçmişi - Son commit'leri görüntüle
• 🔄 Bot'u Yükle - Mevcut botu GitHub'a yükle
    """
    
    bot.send_message(message.chat.id, menu_text, parse_mode='Markdown', reply_markup=markup)

def show_render_menu(message):
    """Render yönetim menüsünü göster"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("🚀 Servis Listesi", callback_data="render_list_services"),
        types.InlineKeyboardButton("📊 Servis Detayı", callback_data="render_service_details"),
        types.InlineKeyboardButton("🔄 Deploy Et", callback_data="render_deploy"),
        types.InlineKeyboardButton("📜 Deploy Geçmişi", callback_data="render_deploys"),
        types.InlineKeyboardButton("📋 Logları Görüntüle", callback_data="render_logs"),
        types.InlineKeyboardButton("🔁 Servisi Yeniden Başlat", callback_data="render_restart"),
        types.InlineKeyboardButton("⚙️ Env Variables", callback_data="render_env_vars"),
        types.InlineKeyboardButton("❌ Kapat", callback_data="close_menu")
    ]
    markup.add(*buttons)
    
    menu_text = """
🔄 *Render Yönetim Paneli*

Yapmak istediğin işlemi seç:
• 🚀 Servis Listesi - Tüm servislerini görüntüle
• 📊 Servis Detayı - Detaylı servis bilgisi
• 🔄 Deploy Et - Yeni deployment başlat
• 📜 Deploy Geçmişi - Son deployment'ları görüntüle
• 📋 Logları Görüntüle - Servis loglarını incele
• 🔁 Servisi Yeniden Başlat - Servisi restart et
• ⚙️ Env Variables - Environment variables yönet
    """
    
    bot.send_message(message.chat.id, menu_text, parse_mode='Markdown', reply_markup=markup)

# CALLBACK HANDLER
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Inline buton callback'lerini işle"""
    try:
        if call.data == "close_menu":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        
        # GitHub Callbacks
        elif call.data == "github_list_repos":
            handle_github_list_repos(call)
        elif call.data == "github_list_files":
            handle_github_list_files(call)
        elif call.data == "github_upload_file":
            handle_github_upload_file(call)
        elif call.data == "github_delete_file":
            handle_github_delete_file(call)
        elif call.data == "github_update_file":
            handle_github_update_file(call)
        elif call.data == "github_commits":
            handle_github_commits(call)
        elif call.data == "github_upload_bot":
            handle_github_upload_bot(call)
        
        # Render Callbacks
        elif call.data == "render_list_services":
            handle_render_list_services(call)
        elif call.data == "render_service_details":
            handle_render_service_details(call)
        elif call.data == "render_deploy":
            handle_render_deploy(call)
        elif call.data == "render_deploys":
            handle_render_deploys(call)
        elif call.data == "render_logs":
            handle_render_logs(call)
        elif call.data == "render_restart":
            handle_render_restart(call)
        elif call.data == "render_env_vars":
            handle_render_env_vars(call)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Hata: {str(e)}")

# GITHUB CALLBACK HANDLERs
def handle_github_list_repos(call):
    """GitHub repo listesini göster"""
    try:
        repos = github_manager.list_repositories()
        if repos:
            repo_text = "📋 *GitHub Repolarınız:*\n\n"
            for repo in repos[:10]:  # İlk 10 repo
                status = "🔒" if repo['private'] else "🌐"
                repo_text += f"{status} *{repo['name']}*\n"
                repo_text += f"   📝 {repo['description'][:50]}...\n"
                repo_text += f"   📅 {repo['updated']} | 💾 {repo['size']} KB\n\n"
            
            if len(repos) > 10:
                repo_text += f"... ve {len(repos) - 10} repo daha"
        else:
            repo_text = "❌ Hiç repo bulunamadı."
        
        bot.edit_message_text(repo_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ Repo listesi alınamadı: {str(e)}", call.message.chat.id, call.message.message_id)

def handle_github_list_files(call):
    """GitHub dosya listesini göster"""
    msg = bot.send_message(call.message.chat.id, "📁 Hangi repo'nun dosyalarını listelemek istiyorsun? Repo adını yaz:")
    bot.register_next_step_handler(msg, process_github_list_files)

def process_github_list_files(message):
    """GitHub dosya listesi işlemi"""
    try:
        repo_name = message.text.strip()
        files = github_manager.get_repository_files(repo_name)
        
        if files:
            file_text = f"📁 *{repo_name} Dosyaları:*\n\n"
            for file in files[:15]:  # İlk 15 dosya
                icon = "📁" if file['type'] == 'dir' else "📄"
                size = f" ({file['size']} bytes)" if file['type'] == 'file' else ""
                file_text += f"{icon} `{file['name']}`{size}\n"
            
            if len(files) > 15:
                file_text += f"\n... ve {len(files) - 15} dosya daha"
        else:
            file_text = "❌ Dosya bulunamadı veya repo mevcut değil."
        
        bot.reply_to(message, file_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Dosya listesi alınamadı: {str(e)}")

def handle_github_upload_file(call):
    """GitHub dosya yükleme"""
    msg = bot.send_message(call.message.chat.id, "📤 Repo adı, dosya adı ve içeriği yaz (örn: myrepo test.py print('hello'))")
    bot.register_next_step_handler(msg, process_github_upload_file)

def process_github_upload_file(message):
    """GitHub dosya yükleme işlemi"""
    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Format: repo_adı dosya_adı dosya_içeriği")
            return
        
        repo_name, file_name, content = parts
        result = github_manager.create_file(repo_name, file_name, content)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ Dosya yükleme hatası: {str(e)}")

def handle_github_delete_file(call):
    """GitHub dosya silme"""
    msg = bot.send_message(call.message.chat.id, "🗑️ Silinecek dosyanın repo adı ve dosya yolunu yaz (örn: myrepo src/main.py)")
    bot.register_next_step_handler(msg, process_github_delete_file)

def process_github_delete_file(message):
    """GitHub dosya silme işlemi"""
    try:
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Format: repo_adı dosya_yolu")
            return
        
        repo_name, file_path = parts
        result = github_manager.delete_file(repo_name, file_path)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ Dosya silme hatası: {str(e)}")

def handle_github_update_file(call):
    """GitHub dosya güncelleme"""
    msg = bot.send_message(call.message.chat.id, "📝 Güncellenecek dosyanın repo adı, dosya yolu ve yeni içeriği yaz")
    bot.register_next_step_handler(msg, process_github_update_file)

def process_github_update_file(message):
    """GitHub dosya güncelleme işlemi"""
    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Format: repo_adı dosya_yolu yeni_içerik")
            return
        
        repo_name, file_path, new_content = parts
        result = github_manager.update_file(repo_name, file_path, new_content)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ Dosya güncelleme hatası: {str(e)}")

def handle_github_commits(call):
    """GitHub commit geçmişi"""
    msg = bot.send_message(call.message.chat.id, "📜 Hangi repo'nun commit geçmişini görmek istiyorsun? Repo adını yaz:")
    bot.register_next_step_handler(msg, process_github_commits)

def process_github_commits(message):
    """GitHub commit geçmişi işlemi"""
    try:
        repo_name = message.text.strip()
        commits = github_manager.get_commits(repo_name, 10)
        
        if commits:
            commit_text = f"📜 *{repo_name} Son Commit'ler:*\n\n"
            for commit in commits:
                commit_text += f"🔸 `{commit['sha']}` - {commit['author']}\n"
                commit_text += f"   📝 {commit['message'][:60]}...\n"
                commit_text += f"   📅 {commit['date']}\n\n"
        else:
            commit_text = "❌ Commit geçmişi bulunamadı."
        
        bot.reply_to(message, commit_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Commit geçmişi alınamadı: {str(e)}")

def handle_github_upload_bot(call):
    """Mevcut botu GitHub'a yükle"""
    try:
        bot.send_message(call.message.chat.id, "🔄 Bot dosyaları GitHub'a yükleniyor...")
        result = github_manager.upload_current_bot("ReisBot_Premium")
        bot.send_message(call.message.chat.id, f"📤 *Bot Yükleme Sonucu:*\n\n{result}", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Bot yükleme hatası: {str(e)}")

# RENDER CALLBACK HANDLERs
def handle_render_list_services(call):
    """Render servis listesini göster"""
    try:
        services = render_manager.get_services()
        if services:
            service_text = "🚀 *Render Servisleriniz:*\n\n"
            for service in services:
                status_icon = "✅" if service['status'] == 'active' else "❌"
                service_text += f"{status_icon} *{service['name']}*\n"
                service_text += f"   🔗 {service['url'] or 'URL yok'}\n"
                service_text += f"   📅 {service['updated']}\n\n"
        else:
            service_text = "❌ Hiç servis bulunamadı."
        
        bot.edit_message_text(service_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ Servis listesi alınamadı: {str(e)}", call.message.chat.id, call.message.message_id)

def handle_render_service_details(call):
    """Render servis detayları"""
    msg = bot.send_message(call.message.chat.id, "📊 Hangi servisin detaylarını görmek istiyorsun? Servis ID'sini yaz:")
    bot.register_next_step_handler(msg, process_render_service_details)

def process_render_service_details(message):
    """Render servis detayları işlemi"""
    try:
        service_id = message.text.strip()
        details = render_manager.get_service_details(service_id)
        
        if details:
            detail_text = f"📊 *Servis Detayları:*\n\n"
            detail_text += f"📛 *Ad:* {details['name']}\n"
            detail_text += f"🔗 *URL:* {details['url'] or 'Yok'}\n"
            detail_text += f"📊 *Durum:* {details['status']}\n"
            detail_text += f"🌿 *Branch:* {details['branch']}\n"
            detail_text += f"🔧 *Build Cmd:* `{details['build_command']}`\n"
            detail_text += f"▶️ *Start Cmd:* `{details['start_command']}`\n"
            detail_text += f"📅 *Oluşturulma:* {details['created'][:10]}\n"
        else:
            detail_text = "❌ Servis detayları bulunamadı."
        
        bot.reply_to(message, detail_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Servis detayları alınamadı: {str(e)}")

def handle_render_deploy(call):
    """Render deploy başlat"""
    msg = bot.send_message(call.message.chat.id, "🔄 Hangi servisi deploy etmek istiyorsun? Servis ID'sini yaz:")
    bot.register_next_step_handler(msg, process_render_deploy)

def process_render_deploy(message):
    """Render deploy işlemi"""
    try:
        service_id = message.text.strip()
        bot.send_message(message.chat.id, "🔄 Deploy başlatılıyor...")
        result = render_manager.deploy_service(service_id)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ Deploy hatası: {str(e)}")

def handle_render_deploys(call):
    """Render deploy geçmişi"""
    msg = bot.send_message(call.message.chat.id, "📜 Hangi servisin deploy geçmişini görmek istiyorsun? Servis ID'sini yaz:")
    bot.register_next_step_handler(msg, process_render_deploys)

def process_render_deploys(message):
    """Render deploy geçmişi işlemi"""
    try:
        service_id = message.text.strip()
        deploys = render_manager.get_deploys(service_id, 10)
        
        if deploys:
            deploy_text = f"📜 *Son Deploy'lar:*\n\n"
            for deploy in deploys:
                status_icon = "✅" if deploy['status'] == 'live' else "🔄" if deploy['status'] == 'build_in_progress' else "❌"
                deploy_text += f"{status_icon} `{deploy['id'][:8]}...`\n"
                deploy_text += f"   📅 {deploy['created']} - {deploy['finished']}\n\n"
        else:
            deploy_text = "❌ Deploy geçmişi bulunamadı."
        
        bot.reply_to(message, deploy_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Deploy geçmişi alınamadı: {str(e)}")

def handle_render_logs(call):
    """Render logları göster"""
    msg = bot.send_message(call.message.chat.id, "📋 Hangi servisin loglarını görmek istiyorsun? Servis ID'sini yaz:")
    bot.register_next_step_handler(msg, process_render_logs)

def process_render_logs(message):
    """Render logları işlemi"""
    try:
        service_id = message.text.strip()
        logs = render_manager.get_logs(service_id, 50)
        
        if logs:
            log_text = f"📋 *Son Loglar:*\n\n"
            # Logları işle (format render API'sine göre değişebilir)
            log_text += "```\n"
            for log in logs[-10:]:  # Son 10 log
                log_text += f"{log}\n"
            log_text += "```"
        else:
            log_text = "❌ Log bulunamadı."
        
        bot.reply_to(message, log_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Log alma hatası: {str(e)}")

def handle_render_restart(call):
    """Render servisi yeniden başlat"""
    msg = bot.send_message(call.message.chat.id, "🔁 Hangi servisi yeniden başlatmak istiyorsun? Servis ID'sini yaz:")
    bot.register_next_step_handler(msg, process_render_restart)

def process_render_restart(message):
    """Render restart işlemi"""
    try:
        service_id = message.text.strip()
        bot.send_message(message.chat.id, "🔁 Servis yeniden başlatılıyor...")
        result = render_manager.restart_service(service_id)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"❌ Restart hatası: {str(e)}")

def handle_render_env_vars(call):
    """Render environment variables"""
    bot.send_message(call.message.chat.id, "⚙️ Environment variables yönetimi yakında eklenecek!")

# BOTU BAŞLAT
if __name__ == "__main__":
    logger.info("🤖 ReisBot Premium başlatılıyor...")
    logger.info(f"AI Durumu: {'Aktif' if AI_ENABLED else 'Devre Dışı'}")
    logger.info(f"GitHub Durumu: {'Bağlı' if GITHUB_ENABLED else 'Bağlantı Yok'}")
    logger.info(f"Render Durumu: {'Bağlı' if RENDER_ENABLED else 'Bağlantı Yok'}")
    logger.info(f"Scheduler Durumu: {'Aktif' if SCHEDULER_ENABLED else 'Devre Dışı'}")
    
    # Scheduler'ı başlat
    if SCHEDULER_ENABLED:
        scheduler.setup_default_jobs()
        scheduler.start_scheduler()
        logger.info("⏰ Cron job'lar başlatıldı!")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot hatası: {e}")
        if SCHEDULER_ENABLED:
            scheduler.stop_scheduler()
        time.sleep(5)
        bot.infinity_polling()
