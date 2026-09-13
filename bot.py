import asyncio
import logging
import random
import time
import sqlite3
import json
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

TOKEN = "8824671023:AAHV9Qq3CV_erKzdJtaExDDEd1QDxwS9JQM"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация базы данных SQLite
def init_db():
    conn = sqlite3.connect("alchemy.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            coins INTEGER,
            elements TEXT,
            monsters TEXT,
            selected TEXT,
            upgrades TEXT,
            last_claim_time REAL,
            streak_day INTEGER,
            last_streak_time REAL,
            expedition TEXT,
            arena_attempts INTEGER,
            last_arena_reset REAL,
            quests TEXT,
            achievements TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

BASE_ELEMENTS = ["💧 Вода", "🔥 Огонь", "🪨 Камень", "🍃 Природа"]

RECIPES = {
    ("🔥 Огонь", "💧 Вода"): {"name": "💨 Парник", "rarity": "Обычный", "income": 30, "power": 12, "element": "Пара"},
    ("💧 Вода", "🔥 Огонь"): {"name": "💨 Парник", "rarity": "Обычный", "income": 30, "power": 12, "element": "Пара"},
    ("🔥 Огонь", "🪨 Камень"): {"name": "🌋 Магмовый Слизняк", "rarity": "Редкий", "income": 90, "power": 35, "element": "Огонь"},
    ("🪨 Камень", "🔥 Огонь"): {"name": "🌋 Магмовый Слизняк", "rarity": "Редкий", "income": 90, "power": 35, "element": "Огонь"},
    ("💧 Вода", "🍃 Природа"): {"name": "🌿 Водная Нимфа", "rarity": "Редкий", "income": 110, "power": 30, "element": "Вода"},
    ("🍃 Природа", "💧 Вода"): {"name": "🌿 Водная Нимфа", "rarity": "Редкий", "income": 110, "power": 30, "element": "Вода"},
    ("🪨 Камень", "🍃 Природа"): {"name": "🌳 Каменный Энт", "rarity": "Обычный", "income": 40, "power": 15, "element": "Земля"},
    ("🍃 Природа", "🪨 Камень"): {"name": "🌳 Каменный Энт", "rarity": "Обычный", "income": 40, "power": 15, "element": "Земля"},
}

def get_user(user_id, first_name="Игрок"):
    conn = sqlite3.connect("alchemy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        default_data = {
            "name": first_name,
            "coins": 300,
            "elements": BASE_ELEMENTS.copy(),
            "monsters": [],
            "selected": [],
            "upgrades": {"patent": False, "shield": False},
            "last_claim_time": time.time(),
            "streak_day": 0,
            "last_streak_time": 0,
            "expedition": {"active": False, "end_time": 0},
            "arena_attempts": 3,
            "last_arena_reset": time.time(),
            "quests": {
                "craft": {"progress": 0, "goal": 2, "reward": 150, "claimed": False},
                "arena": {"progress": 0, "goal": 2, "reward": 200, "claimed": False},
                "market": {"progress": 0, "goal": 1, "reward": 100, "claimed": False}
            },
            "achievements": {
                "craft_10": {"name": "Ученый-алхимик (10 синтезов)", "goal": 10, "progress": 0, "reward": 500, "claimed": False},
                "boss_3": {"name": "Гроза боссов (победить 3 боссов)", "goal": 3, "progress": 0, "reward": 1000, "claimed": False},
                "rich": {"name": "Капиталист (накопить 2000 монет)", "goal": 2000, "progress": 0, "reward": 800, "claimed": False}
            }
        }
        cursor.execute("""
            INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, default_data["name"], default_data["coins"],
            json.dumps(default_data["elements"]), json.dumps(default_data["monsters"]),
            json.dumps(default_data["selected"]), json.dumps(default_data["upgrades"]),
            default_data["last_claim_time"], default_data["streak_day"], default_data["last_streak_time"],
            json.dumps(default_data["expedition"]), default_data["arena_attempts"], default_data["last_arena_reset"],
            json.dumps(default_data["quests"]), json.dumps(default_data["achievements"])
        ))
        conn.commit()
        conn.close()
        return get_user(user_id, first_name)
    
    conn.close()
    return {
        "user_id": row[0], "name": row[1], "coins": row[2],
        "elements": json.loads(row[3]), "monsters": json.loads(row[4]),
        "selected": json.loads(row[5]), "upgrades": json.loads(row[6]),
        "last_claim_time": row[7], "streak_day": row[8], "last_streak_time": row[9],
        "expedition": json.loads(row[10]), "arena_attempts": row[11], "last_arena_reset": row[12],
        "quests": json.loads(row[13]), "achievements": json.loads(row[14])
    }

def save_user(u):
    conn = sqlite3.connect("alchemy.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET 
            name=?, coins=?, elements=?, monsters=?, selected=?, upgrades=?, 
            last_claim_time=?, streak_day=?, last_streak_time=?, expedition=?, 
            arena_attempts=?, last_arena_reset=?, quests=?, achievements=?
        WHERE user_id=?
    """, (
        u["name"], u["coins"], json.dumps(u["elements"]), json.dumps(u["monsters"]),
        json.dumps(u["selected"]), json.dumps(u["upgrades"]), u["last_claim_time"],
        u["streak_day"], u["last_streak_time"], json.dumps(u["expedition"]),
        u["arena_attempts"], u["last_arena_reset"], json.dumps(u["quests"]),
        json.dumps(u["achievements"]), u["user_id"]
    ))
    conn.commit()
    conn.close()

def generate_procedural_monster(item1, item2):
    prefixes = ["Неистовый", "Древний", "Теневой", "Лунный", "Электрический", "Хаотичный", "Кристальный", "Пепельный"]
    suffixes = ["Зверь", "Фантом", "Страж", "Химера", "Дух", "Титан", "Странник", "Гомункул"]
    rarities = [("Обычный", 50, 20), ("Редкий", 150, 50), ("Эпический", 350, 120), ("Легендарный", 800, 300)]
    elements = ["Огонь", "Вода", "Земля", "Воздух"]
    
    seed_val = hash(item1 + item2 + str(time.time()))
    rnd = random.Random(seed_val)
    
    p = rnd.choice(prefixes)
    s = rnd.choice(suffixes)
    r_data = rnd.choices(rarities, weights=[50, 30, 15, 5])[0]
    elem = rnd.choice(elements)
    
    is_shiny = rnd.random() < 0.05
    name_prefix = "🌟 SHINY " if is_shiny else "✨ "
    name = f"{name_prefix}{p} {s}"
    
    income = r_data[1] * 2 if is_shiny else r_data[1]
    power = r_data[2] * 2 if is_shiny else r_data[2]
    rarity = f"{r_data[0]} (Блестящий)" if is_shiny else r_data[0]
    
    return {"name": name, "rarity": rarity, "income": income, "power": power, "element": elem, "is_shiny": is_shiny}

@dp.message(CommandStart())
async def cmd_start(message: Message):
    get_user(message.from_user.id, message.from_user.first_name)
    await show_main_menu(message)

async def show_main_menu(message_or_callback, is_edit=False):
    user_id = message_or_callback.from_user.id if isinstance(message_or_callback, CallbackQuery) else message_or_callback.chat.id
    u = get_user(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Календарь наград", callback_data="calendar_menu"),
         InlineKeyboardButton(text="📜 Задания", callback_data="quests_menu")],
        [InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements_menu")],
        [InlineKeyboardButton(text="🧪 Лаборатория синтеза", callback_data="lab_page_0")],
        [InlineKeyboardButton(text="🎒 Моя армия и Ферма", callback_data="inv_page_0")],
        [InlineKeyboardButton(text="🧭 Экспедиция (6 часов)", callback_data="expedition_menu")],
        [InlineKeyboardButton(text="🛒 Магазин улучшений", callback_data="shop_menu")],
        [InlineKeyboardButton(text="⚔️ Босс-Арена (5 уровней)", callback_data="arena_bosses")],
        [InlineKeyboardButton(text="💰 Биржа (Рынок)", callback_data="market_page_0")]
    ])
    
    text = (
        f"👑 **Алхимическая Империя**\n\n"
        f"💰 Монеты: **{u['coins']} 🪙**\n"
        f"🐉 Всего существ: **{len(u['monsters'])}**\n\n"
        f"Выберите раздел:"
    )
    
    if is_edit:
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "calendar_menu")
async def calendar_menu(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Забрать награду за день", callback_data="claim_calendar")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        f"📅 **Календарь ежедневных наград**\n\nТекущий день серии: **День {u['streak_day'] + 1} из 7**",
        parse_mode="Markdown", reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "claim_calendar")
async def claim_calendar(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    now = time.time()
    if now - u["last_streak_time"] < 24 * 3600:
        await callback.answer("⏳ Награда за сегодня уже получена!", show_alert=True)
        return
        
    u["last_streak_time"] = now
    day = u["streak_day"] % 7
    rewards = [
        ("150 монет", 150, None), ("300 монет", 300, None), ("500 монет", 500, None),
        ("Королевская колба", 0, "flask"), ("800 монет", 800, None), ("1200 монет", 1200, None),
        ("👑 Легендарный питомец + 2000 монет", 2000, "legendary")
    ]
    desc, coin_bonus, special = rewards[day]
    u["coins"] += coin_bonus
    
    if special == "flask":
        u["monsters"].append({"name": "🌟 Королевский Грифон", "rarity": "Эпический", "income": 250, "power": 140, "element": "Воздух", "is_shiny": False})
    elif special == "legendary":
        u["monsters"].append({"name": "💎 Кристальный Дракон", "rarity": "Легендарный (Блестящий)", "income": 1000, "power": 800, "element": "Огонь", "is_shiny": True})
        
    u["streak_day"] += 1
    save_user(u)
    await callback.answer(f"🎉 День {day + 1}: получено ({desc})!", show_alert=True)
    await calendar_menu(callback)

@dp.callback_query(F.data == "achievements_menu")
async def achievements_menu(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    if u["coins"] >= 2000:
        u["achievements"]["rich"]["progress"] = 2000
        save_user(u)
        
    keyboard_buttons = []
    for key, ach in u["achievements"].items():
        status = "✅ Получено" if ach["claimed"] else (f"🎁 Забрать (+{ach['reward']}🪙)" if ach["progress"] >= ach["goal"] else f"⏳ ({ach['progress']}/{ach['goal']})")
        keyboard_buttons.append([InlineKeyboardButton(text=f"{ach['name']} — {status}", callback_data=f"get_ach_{key}")])
    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])
    
    await callback.message.edit_text("🏆 **Система достижений**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("get_ach_"))
async def claim_achievement(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    ach_key = callback.data.replace("get_ach_", "")
    ach = u["achievements"][ach_key]
    
    if not ach["claimed"] and ach["progress"] >= ach["goal"]:
        ach["claimed"] = True
        u["coins"] += ach["reward"]
        save_user(u)
        await callback.answer(f"🏆 Награда: +{ach['reward']} 🪙", show_alert=True)
    else:
        await callback.answer("❌ Еще не выполнено или уже забрано!", show_alert=True)
    await achievements_menu(callback)

@dp.callback_query(F.data == "expedition_menu")
async def expedition_menu(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    exp = u["expedition"]
    now = time.time()
    keyboard_rows = []
    
    if not exp["active"]:
        keyboard_rows.append([InlineKeyboardButton(text="🧭 Отправить отряд в поход (6ч)", callback_data="start_expedition")])
        status_text = "🧭 Отряд свободен. Поход длится 6 часов."
    else:
        if now >= exp["end_time"]:
            keyboard_rows.append([InlineKeyboardButton(text="🎁 Забрать награду экспедиции!", callback_data="claim_expedition")])
            status_text = "🎉 Экспедиция завершена!"
        else:
            hours_left = int((exp["end_time"] - now) // 3600)
            mins_left = int(((exp["end_time"] - now) % 3600) // 60)
            status_text = f"⏳ Осталось: **{hours_left} ч. {mins_left} мин.**"
            
    keyboard_rows.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])
    await callback.message.edit_text(f"🧭 **Экспедиции**\n\n{status_text}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))
    await callback.answer()

@dp.callback_query(F.data == "start_expedition")
async def start_expedition(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    if not u["monsters"]:
        await callback.answer("❌ Армия пуста!", show_alert=True)
        return
    u["expedition"]["active"] = True
    u["expedition"]["end_time"] = time.time() + (6 * 3600)
    save_user(u)
    await callback.answer("🧭 Отряд отправлен!", show_alert=True)
    await expedition_menu(callback)

@dp.callback_query(F.data == "claim_expedition")
async def claim_expedition(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    u["expedition"]["active"] = False
    reward_coins = random.randint(400, 800)
    u["coins"] += reward_coins
    
    bonus_msg = ""
    if random.random() < 0.4:
        bonus_pet = generate_procedural_monster("Экспедиция", "Руины")
        u["monsters"].append(bonus_pet)
        bonus_msg = f"\n🎁 Найден питомец: **{bonus_pet['name']}**!"
        
    save_user(u)
    await callback.answer(f"Экспедиция принесла +{reward_coins} монет!", show_alert=True)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")]])
    await callback.message.edit_text(f"🏆 **Экспедиция завершена!**\n💰 Награда: **+{reward_coins} 🪙**{bonus_msg}", parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "arena_bosses")
async def arena_bosses_menu(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    if time.time() - u["last_arena_reset"] > 24 * 3600:
        u["arena_attempts"] = 3
        u["last_arena_reset"] = time.time()
        save_user(u)
        
    bosses = [
        {"id": 1, "name": "Goblin Боцман", "power": 30, "reward": 100},
        {"id": 2, "name": "🔥 Огненный Страж", "power": 90, "reward": 300},
        {"id": 3, "name": "🐉 Драконид-Ветеран", "power": 250, "reward": 800},
        {"id": 4, "name": "👑 Король Бездны", "power": 700, "reward": 2500},
        {"id": 5, "name": "💀 Архидемон Хаоса", "power": 1800, "reward": 7000}
    ]
    
    keyboard_buttons = []
    for b in bosses:
        keyboard_buttons.append([InlineKeyboardButton(text=f"⚔️ Ур.{b['id']}: {b['name']} (Сила: {b['power']})", callback_data=f"fight_boss_{b['id']}")])
    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])
    
    total_power = sum(m["power"] for m in u["monsters"]) if u["monsters"] else 5
    await callback.message.edit_text(f"⚔️ **Арена Боссов**\n⚡ Попыток: **{u['arena_attempts']}/3**\n💪 Мощь вашей армии: **{total_power}**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("fight_boss_"))
async def fight_boss(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    boss_id = int(callback.data.replace("fight_boss_", ""))
    if u["arena_attempts"] <= 0:
        await callback.answer("❌ Закончились попытки на сегодня!", show_alert=True)
        return
        
    bosses_dict = {
        1: {"name": "Goblin Боцман", "power": 30, "reward": 100},
        2: {"name": "Огненный Страж", "power": 90, "reward": 300},
        3: {"name": "Драконид-Ветеран", "power": 250, "reward": 800},
        4: {"name": "Король Бездны", "power": 700, "reward": 2500},
        5: {"name": "Архидемон Хаоса", "power": 1800, "reward": 7000}
    }
    boss = bosses_dict[boss_id]
    u["arena_attempts"] -= 1
    total_power = sum(m["power"] for m in u["monsters"]) if u["monsters"] else 5
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ К боссам", callback_data="arena_bosses")], [InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")]])
    
    if total_power >= boss["power"]:
        u["coins"] += boss["reward"]
        if not u["quests"]["arena"]["claimed"]:
            u["quests"]["arena"]["progress"] = min(u["quests"]["arena"]["goal"], u["quests"]["arena"]["progress"] + 1)
        u["achievements"]["boss_3"]["progress"] = min(u["achievements"]["boss_3"]["goal"], u["achievements"]["boss_3"]["progress"] + 1)
        text = f"🏆 **Победа над {boss['name']}!**\nНаграда: **+{boss['reward']} 🪙**"
    else:
        if u["upgrades"]["shield"]:
            text = f"🛡 **Щит спас армию!** Поражение отменено."
        else:
            text = f"💀 **Поражение!** Босс ({boss['power']}) сильнее вашей армии ({total_power})."
            
    save_user(u)
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "quests_menu")
async def quests_menu(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    q = u["quests"]
    def status_txt(quest):
        if quest["claimed"]: return "✅ Выполнено"
        elif quest["progress"] >= quest["goal"]: return "🎁 Забрать!"
        else: return f"⏳ ({quest['progress']}/{quest['goal']})"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🧪 Синтез (2) — {status_txt(q['craft'])}", callback_data="get_q_craft")],
        [InlineKeyboardButton(text=f"⚔️ Арена (2) — {status_txt(q['arena'])}", callback_data="get_q_arena")],
        [InlineKeyboardButton(text=f"💰 Рынок (1) — {status_txt(q['market'])}", callback_data="get_q_market")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")]
    ])
    await callback.message.edit_text("📜 **Ежедневные задания**", parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("get_q_"))
async def claim_quest(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    q_key = callback.data.replace("get_q_", "")
    quest = u["quests"][q_key]
    if not quest["claimed"] and quest["progress"] >= quest["goal"]:
        quest["claimed"] = True
        u["coins"] += quest["reward"]
        save_user(u)
        await callback.answer(f"🎉 Награда: +{quest['reward']} 🪙!", show_alert=True)
    else:
        await callback.answer("❌ Не выполнено или уже забрано!", show_alert=True)
    await quests_menu(callback)

@dp.callback_query(F.data == "shop_menu")
async def shop_menu(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    patent_status = "✅ Куплено" if u["upgrades"]["patent"] else "10 000 🪙"
    shield_status = "✅ Куплено" if u["upgrades"]["shield"] else "200 🪙"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Королевская колба (350 🪙)", callback_data="buy_royal_flask")],
        [InlineKeyboardButton(text=f"📜 Магический патент ({patent_status})", callback_data="buy_patent")],
        [InlineKeyboardButton(text=f"🛡 Щит арены ({shield_status})", callback_data="buy_shield")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")]
    ])
    await callback.message.edit_text(f"🛒 **Магазин**\nБаланс: **{u['coins']} 🪙**", parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "buy_royal_flask")
async def buy_royal_flask(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    if u["coins"] >= 350:
        u["coins"] -= 350
        reward = generate_procedural_monster("Королевская", "Колба")
        u["monsters"].append(reward)
        save_user(u)
        await callback.answer(f"🎉 Вы получили {reward['name']}!", show_alert=True)
    else:
        await callback.answer("❌ Нужно 350 монет!", show_alert=True)
    await shop_menu(callback)

@dp.callback_query(F.data == "buy_patent")
async def buy_patent(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    if u["upgrades"]["patent"]:
        await callback.answer("Уже куплено!", show_alert=True)
    elif u["coins"] >= 10000:
        u["coins"] -= 10000
        u["upgrades"]["patent"] = True
        save_user(u)
        await callback.answer("✅ Магический патент куплен! (+50% доход фермы)", show_alert=True)
    else:
        await callback.answer("❌ Нужно 10 000 монет!", show_alert=True)
    await shop_menu(callback)

@dp.callback_query(F.data == "buy_shield")
async def buy_shield(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    if u["upgrades"]["shield"]:
        await callback.answer("Уже куплено!", show_alert=True)
    elif u["coins"] >= 200:
        u["coins"] -= 200
        u["upgrades"]["shield"] = True
        save_user(u)
        await callback.answer("🛡 Щит активирован!", show_alert=True)
    else:
        await callback.answer("❌ Нужно 200 монет!", show_alert=True)
    await shop_menu(callback)

@dp.callback_query(F.data.startswith("inv_page_"))
async def show_inventory_paginated(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    page = int(callback.data.replace("inv_page_", ""))
    
    stacked_dict = {}
    for m in u["monsters"]:
        key = m["name"]
        if key not in stacked_dict:
            stacked_dict[key] = {"data": m, "count": 0}
        stacked_dict[key]["count"] += 1
        
    stacked_list = list(stacked_dict.values())
    per_page = 5
    total_pages = max(1, (len(stacked_list) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    chunk = stacked_list[page * per_page : (page + 1) * per_page]
    
    base_income = sum(m["income"] for m in u["monsters"])
    hourly_income = int(base_income * 1.5) if u["upgrades"]["patent"] else base_income
    
    text_lines = [f"🎒 **Армия и Ферма ({page + 1}/{total_pages}):**\n", f"⚡ Доход: **+{hourly_income}/час**\n"]
    if chunk:
        for item in chunk:
            m = item["data"]
            count_str = f" x{item['count']}" if item['count'] > 1 else ""
            text_lines.append(f"• **{m['name']}**{count_str} `[{m['rarity']}]` (Сила: {m['power']})")
    else:
        text_lines.append("Армия пуста.")
        
    nav_buttons = []
    if page > 0: nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"inv_page_{page - 1}"))
    if page < total_pages - 1: nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"inv_page_{page + 1}"))
    
    keyboard_rows = []
    if nav_buttons: keyboard_rows.append(nav_buttons)
    keyboard_rows.append([InlineKeyboardButton(text="📥 Собрать доход (за 6ч)", callback_data="claim_income")])
    keyboard_rows.append([InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")])
    
    await callback.message.edit_text("\n".join(text_lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows))
    await callback.answer()

@dp.callback_query(F.data == "claim_income")
async def claim_income(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    now = time.time()
    elapsed_hours = (now - u["last_claim_time"]) / 3600.0
    if elapsed_hours < 0.1:
        await callback.answer("⏳ Рано собирать!", show_alert=True)
        return
    base_income = sum(m["income"] for m in u["monsters"])
    hourly_income = int(base_income * 1.5) if u["upgrades"]["patent"] else base_income
    earned = int(hourly_income * min(elapsed_hours, 6.0))
    if earned > 0:
        u["coins"] += earned
        u["last_claim_time"] = now
        save_user(u)
        await callback.answer(f"💰 Собрано: +{earned} 🪙", show_alert=True)
    else:
        await callback.answer("На ферме пусто.", show_alert=True)
    await show_inventory_paginated(callback)

@dp.callback_query(F.data.startswith("lab_page_"))
async def open_lab_paginated(callback: CallbackQuery):
    page = int(callback.data.replace("lab_page_", ""))
    await render_lab_page(callback, page)
    await callback.answer()

async def render_lab_page(callback: CallbackQuery, page: int):
    u = get_user(callback.from_user.id)
    selected = u.get("selected", [])
    sel_text = " + ".join(selected) if selected else "Пусто"
    
    unique_monsters_names = list(set([m["name"] for m in u["monsters"]]))
    available_items = u["elements"] + unique_monsters_names
    
    per_page = 6
    total_pages = max(1, (len(available_items) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    chunk = available_items[page * per_page : (page + 1) * per_page]
    
    keyboard_buttons = []
    row = []
    for item in chunk:
        row.append(InlineKeyboardButton(text=item, callback_data=f"elem_{item}_{page}"))
        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []
    if row: keyboard_buttons.append(row)
    
    nav_buttons = []
    if page > 0: nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"lab_page_{page - 1}"))
    if page < total_pages - 1: nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"lab_page_{page + 1}"))
    if nav_buttons: keyboard_buttons.append(nav_buttons)
    
    if len(selected) == 2:
        keyboard_buttons.append([InlineKeyboardButton(text="⚡ Провести Синтез!", callback_data="do_craft")])
    keyboard_buttons.append([InlineKeyboardButton(text="🗑 Очистить", callback_data="reset_lab")])
    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")])
    
    await callback.message.edit_text(f"🧪 **Лаборатория ({page + 1}/{total_pages}):**\nВыбрано: [ {sel_text} ]", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))

@dp.callback_query(F.data.startswith("elem_"))
async def select_element(callback: CallbackQuery):
    parts = callback.data.split("_")
    elem = "_".join(parts[1:-1])
    page = int(parts[-1])
    u = get_user(callback.from_user.id)
    if "selected" not in u: u["selected"] = []
    if len(u["selected"]) < 2 and elem not in u["selected"]:
        u["selected"].append(elem)
        save_user(u)
    await render_lab_page(callback, page)
    await callback.answer()

@dp.callback_query(F.data == "reset_lab")
async def reset_lab(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    u["selected"] = []
    save_user(u)
    await render_lab_page(callback, 0)
    await callback.answer()

@dp.callback_query(F.data == "do_craft")
async def do_craft(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    selected = tuple(u.get("selected", []))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧪 Еще", callback_data="lab_page_0")], [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inv_page_0")]])
    
    if len(selected) == 2:
        if selected in RECIPES:
            monster = RECIPES[selected].copy()
        else:
            rev_sel = (selected[1], selected[0])
            if rev_sel in RECIPES:
                monster = RECIPES[rev_sel].copy()
            else:
                monster = generate_procedural_monster(selected[0], selected[1])
                
        u["monsters"].append(monster)
        u["selected"] = []
        
        if not u["quests"]["craft"]["claimed"]:
            u["quests"]["craft"]["progress"] = min(u["quests"]["craft"]["goal"], u["quests"]["craft"]["progress"] + 1)
        u["achievements"]["craft_10"]["progress"] = min(u["achievements"]["craft_10"]["goal"], u["achievements"]["craft_10"]["progress"] + 1)
        save_user(u)
        
        shiny_txt = " ⭐ СВЕРХРЕДКАЯ SHINY МУТАЦИЯ!" if monster.get("is_shiny") else ""
        await callback.message.edit_text(f"🎉 **Синтез успешен!**{shiny_txt}\n\nСоздан: **{monster['name']}** `[{monster['rarity']}]`\n⚔️ Сила: `{monster['power']}`", parse_mode="Markdown", reply_markup=keyboard)
    else:
        u["selected"] = []
        save_user(u)
        await callback.message.edit_text("💥 Ошибка!", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("market_page_"))
async def market_menu_paginated(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    page = int(callback.data.replace("market_page_", ""))
    per_page = 4
    total_pages = max(1, (len(u["monsters"]) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * per_page
    current_chunk = u["monsters"][start_idx:start_idx + per_page]
    
    keyboard_buttons = []
    for offset, m in enumerate(current_chunk):
        real_idx = start_idx + offset
        keyboard_buttons.append([InlineKeyboardButton(text=f"Продать {m['name']} за 50🪙", callback_data=f"sell_{real_idx}_{page}")])
        
    nav_buttons = []
    if page > 0: nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"market_page_{page - 1}"))
    if page < total_pages - 1: nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"market_page_{page + 1}"))
    if nav_buttons: keyboard_buttons.append(nav_buttons)
    keyboard_buttons.append([InlineKeyboardButton(text="◀️ Меню", callback_data="main_menu")])
    
    await callback.message.edit_text(f"💰 **Рынок ({page + 1}/{total_pages}):**\nБаланс: **{u['coins']} 🪙**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_"))
async def sell_monster(callback: CallbackQuery):
    u = get_user(callback.from_user.id)
    parts = callback.data.split("_")
    idx = int(parts[1])
    page = int(parts[2])
    if idx < len(u["monsters"]):
        sold = u["monsters"].pop(idx)
        u["coins"] += 50
        if not u["quests"]["market"]["claimed"]:
            u["quests"]["market"]["progress"] = min(u["quests"]["market"]["goal"], u["quests"]["market"]["progress"] + 1)
        save_user(u)
        await callback.answer(f"Продан {sold['name']}!", show_alert=True)
    callback.data = f"market_page_{page}"
    await market_menu_paginated(callback)

@dp.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await show_main_menu(callback, is_edit=True)
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот с базой данных SQLite успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
