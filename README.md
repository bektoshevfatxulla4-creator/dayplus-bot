# Day+ 📦

Mahsulotlarning muddat sanasini kuzatuvchi Telegram bot.

## Xususiyatlar

- 📸 Mahsulot rasmi bilan qo'shish
- ⏰ Muddat eslatmalari (har kuni 09:00)
- 🎨 Avtomatik chegirma rasmi generatsiyasi
- 📦 Barcha mahsulotlarni ko'rish va boshqarish

## O'rnatish

```bash
# 1. Reponi clone qiling
git clone ...
cd dayplus

# 2. Virtual muhit yarating
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Kutubxonalarni o'rnating
pip install -r requirements.txt

# 4. Font papkasini yarating
mkdir -p fonts
# DejaVuSans.ttf va DejaVuSans-Bold.ttf ni fonts/ papkasiga qo'ying

# 5. .env faylini yarating
cp .env.example .env
# BOT_TOKEN ni to'ldiring

# 6. Botni ishga tushiring
python main.py
```

## Railway/Render deploy

1. GitHub ga push qiling
2. Railway/Render da yangi project oching
3. `BOT_TOKEN` environment variable qo'shing
4. Deploy!

## Fayl tuzilishi

```
dayplus/
├── main.py          # Bot va barcha handler lar
├── database.py      # SQLite — ma'lumotlar bazasi
├── scheduler.py     # Kunlik tekshirish (09:00)
├── notifications.py # Eslatma formatlash va yuborish
├── image_gen.py     # Chegirma rasmi generatsiyasi
├── requirements.txt
├── Procfile         # Railway/Render uchun
└── fonts/           # DejaVuSans fontlari
```
