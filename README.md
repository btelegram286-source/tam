# 🤖 ReisBot Premium

Premium özelliklere sahip gelişmiş Telegram botu. AI sohbet, GitHub entegrasyonu, YouTube indirme ve daha fazlası!

## ✨ Özellikler

### 🤖 Yapay Zeka Özellikleri
- 🤖 OpenAI GPT ile akıllı sohbet
- 🖼️ AI ile görsel oluşturma (DALL-E)
- 🎤 Metin okuma (Text-to-Speech)

### 📁 Geliştirici Araçları
- 📁 GitHub'a otomatik dosya push
- 🔄 Render servis yönetimi
- 📊 Sistem durumu takibi

### 🌐 Bilgi Servisleri
- 🌤️ Gerçek zamanlı hava durumu
- 💱 Döviz kuru takibi
- ₿ Bitcoin fiyat bilgisi

### 🛠️ Utility Araçları
- 🔗 QR kod oluşturucu
- 🎵 YouTube'dan audio indirme
- 📱 Dosya dönüştürme araçları

### 🎯 Diğer Özellikler
- Türkçe dil desteği
- Kullanıcı dostu buton arayüzü
- Komut ve buton ile çift erişim

## 🚀 Kurulum

### 1. Gereksinimler

- Python 3.8+
- Telegram Bot Token
- OpenAI API Key
- GitHub Personal Access Token
- Render API Key (opsiyonel)

### 2. Sanal Ortam Kurulumu

```bash
# Proje dizinine git
cd ReisBot_Premium

# Sanal ortam oluştur
python -m venv venv

# Sanal ortamı aktif et (Windows)
venv\Scripts\activate

# Sanal ortamı aktif et (Linux/Mac)
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 3. Environment Variables Ayarlama

**GÜVENLİK UYARISI:** API anahtarlarını asla doğrudan kod içinde veya version control'de saklamayın!

#### Yöntem 1: Environment Variables (Önerilen)

```bash
# Windows (PowerShell)
$env:BOT_TOKEN="your_bot_token"
$env:GITHUB_TOKEN="your_github_token"
$env:GITHUB_USER="your_github_username"
$env:OPENAI_KEY="your_openai_key"
$env:RENDER_API_KEY="your_render_key"
$env:RENDER_OWNER_ID="your_render_service_id"

# Windows (CMD)
set BOT_TOKEN=your_bot_token
set GITHUB_TOKEN=your_github_token
set GITHUB_USER=your_github_username
set OPENAI_KEY=your_openai_key
set RENDER_API_KEY=your_render_key
set RENDER_OWNER_ID=your_render_service_id

# Linux/Mac
export BOT_TOKEN=your_bot_token
export GITHUB_TOKEN=your_github_token
export GITHUB_USER=your_github_username
export OPENAI_KEY=your_openai_key
export RENDER_API_KEY=your_render_key
export RENDER_OWNER_ID=your_render_service_id
```

#### Yöntem 2: config.env dosyası (Dikkatli kullanın)

```env
BOT_TOKEN=your_bot_token_here
GITHUB_TOKEN=your_github_token_here
GITHUB_USER=your_github_username
OPENAI_KEY=your_openai_api_key_here
RENDER_API_KEY=your_render_api_key_here
RENDER_OWNER_ID=your_render_service_id_here
```

**⚠️ ÖNEMLİ:** config.env dosyasını asla version control'e eklemeyin! `.gitignore` dosyası bu dosyayı otomatik olarak ignore eder.

### 4. Botu Çalıştırma

```bash
python main.py
```

## 🔧 Komutlar

### Temel Komutlar
- `/start` - Botu başlat
- `/help` - Yardım menüsü
- `/status` - Bot durumu

### AI ve Görsel Komutları
- `/ai <soru>` - AI ile sohbet et
- `/image <açıklama>` - AI ile görsel oluştur
- `/tts <metin>` - Metni sese çevir

### Bilgi Komutları
- `/weather <şehir>` - Hava durumu (varsayılan: İstanbul)
- `/exchange <from> <to>` - Döviz kuru (varsayılan: USD TRY)
- `/bitcoin` - Bitcoin fiyatı

### Utility Komutları
- `/qr <metin>` - QR kod oluştur
- `/github <repo> <dosya>` - GitHub'a dosya push et
- `/yt <url>` - YouTube'dan audio indir

### Buton Arayüzü
Tüm özellikler butonlar ile de erişilebilir:
- 🤖 AI Sohbet
- 🖼️ AI Görsel
- 🎤 Ses Çevir
- 🌤️ Hava Durumu
- 💱 Döviz Kuru
- ₿ Bitcoin
- 🔗 QR Kod
- 📁 GitHub Push
- 🎵 YouTube İndir
- 📊 Bot Durumu

## 🌐 Deployment

### Render Üzerinde Deploy

1. GitHub reposuna push et
2. Render dashboard'da yeni Web Service oluştur
3. Environment variables'ları ayarla:
   - BOT_TOKEN
   - GITHUB_TOKEN  
   - GITHUB_USER
   - OPENAI_KEY
   - RENDER_API_KEY
   - RENDER_OWNER_ID

## 🛡️ Güvenlik

- [ ] Tüm API anahtarlarını değiştirin
- [ ] GitHub token'ı sadece gerekli permissions ile oluşturun
- [ ] Environment variables kullanın
- [ ] config.env dosyasını version control'e eklemeyin
- [ ] Düzenli olarak dependency'leri güncelleyin

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## ⚠️ Sorun Giderme

- **Encoding hatası:** `# -*- coding: utf-8 -*-` ekleyin
- **Import hatası:** `pip install -r requirements.txt`
- **API hatası:** Environment variables'ları kontrol edin

## 📞 Destek

Sorularınız için issue açabilir veya Telegram üzerinden ulaşabilirsiniz.
