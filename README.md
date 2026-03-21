# 🎬 Cineflix Bot — Deploy Guide

## Environment Variables (Required)
| Variable | Description | Example |
|---|---|---|
| `BOT_TOKEN` | BotFather থেকে পাওয়া token | `123456:ABC-DEF...` |
| `MONGO_URI` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster...` |
| `ADMIN_ID` | তোমার Telegram numeric ID | `123456789` |

## Deploy on Railway (Recommended — Free)
1. railway.app এ account খোলো
2. "New Project" → "Deploy from GitHub repo"
3. এই folder টা GitHub এ push করো
4. Railway dashboard এ Variables tab এ তিনটা env var দাও
5. Deploy হয়ে যাবে ✅

## Deploy on Render (Alternative — Free)
1. render.com এ account খোলো  
2. "New" → "Background Worker"
3. GitHub repo connect করো
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python bot.py`
6. Environment Variables দাও
7. Deploy ✅

## MongoDB Atlas Setup (Free)
1. mongodb.com/atlas এ account খোলো
2. Free cluster বানাও (M0)
3. Database User বানাও
4. Network Access → Allow from anywhere (0.0.0.0/0)
5. Connect → Drivers → Connection string copy করো
6. সেটা MONGO_URI তে দাও

## Admin ID কীভাবে পাবে?
Telegram এ @userinfobot কে message করো → সে তোমার ID দেবে
