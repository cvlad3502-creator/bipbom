"""BipBom - бот с демо-кредитами и «витриной» рубли/Stars.

Три баланса:
  credits — демо, единственная валюта ставок и кейсов со случайным выигрышем;
  rub     — реальные рубли (копейки), только пополнение и благодарственные покупки без выигрыша;
  stars   — Telegram Stars, только разблокировка оформления бота.

Ни одна платная валюта не попадает в ставки и не обменивается на кредиты.
"""

import asyncio
import os
import random
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import BaseFilter, Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()
START_CREDITS = 1000
DAILY_GRANT = 150

# Цены. Stars — целые, рубли — в копейках.
STAR_SKINS = 50          # оформление профиля бота
RUB_PACKS = {            # благодарность разработчику, без награды и выигрыша
    "rub_small": (49, "Поддержать · 49 ₽"),
    "rub_medium": (149, "Поддержать · 149 ₽"),
}
PRICES_CREDITS = {"bomzh": 9, "slabochek": 14, "manifor": 39}
IAP = {str(RUB_PACKS[k][0] * 100): k for k in RUB_PACKS}  # payload -> ключ
IAP_STARS = "stars_skin"

DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
DB = sqlite3.connect(os.path.join(DATA_DIR, "bipbom.db"), check_same_thread=False)
DB.row_factory = sqlite3.Row
DB.executescript(
    """
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        name TEXT,
        balance INTEGER NOT NULL DEFAULT 0,   -- демо-кредиты
        max_bet INTEGER NOT NULL DEFAULT 50,
        daily_at TEXT,
        weekly_at TEXT,
        skin TEXT
    );
    CREATE TABLE IF NOT EXISTS wallet(
        user_id INTEGER NOT NULL,
        currency TEXT NOT NULL,
        amount INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(user_id, currency)
    );
    CREATE TABLE IF NOT EXISTS ledger(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game TEXT NOT NULL,
        currency TEXT NOT NULL DEFAULT 'credits',
        amount INTEGER NOT NULL,
        balance_after INTEGER NOT NULL,
        ts TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS payments(
        charge_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        currency TEXT NOT NULL,
        amount INTEGER NOT NULL,
        payload TEXT,
        refunded INTEGER NOT NULL DEFAULT 0,
        ts TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """
)
# миграция старой базы
cols = {r["name"] for r in DB.execute("PRAGMA table_info(users)")}
for c, ddl in {"skin": "TEXT"}.items():
    if c not in cols:
        DB.execute(f"ALTER TABLE users ADD COLUMN {c} {ddl}")
lcols = {r["name"] for r in DB.execute("PRAGMA table_info(ledger)")}
if "currency" not in lcols:
    DB.execute("ALTER TABLE ledger ADD COLUMN currency TEXT NOT NULL DEFAULT 'credits'")
DB.commit()

dp = Dispatcher()


# ---------- кошелёк ----------

def user(uid: int, name: str = "") -> sqlite3.Row:
    row = DB.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if row is None:
        DB.execute(
            "INSERT INTO users(id, name, balance) VALUES(?,?,?)",
            (uid, name or str(uid), START_CREDITS),
        )
        DB.execute(
            "INSERT INTO ledger(user_id, game, currency, amount, balance_after) VALUES(?,?,?,?,?)",
            (uid, "welcome", "credits", START_CREDITS, START_CREDITS),
        )
        DB.commit()
        row = DB.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    elif name and row["name"] != name:
        DB.execute("UPDATE users SET name=? WHERE id=?", (name, uid))
        DB.commit()
    return row


def wallet(uid: int, cur: str) -> int:
    """Баланс любой валюты. credits живёт в users, остальные — в wallet."""
    if cur == "credits":
        return user(uid)["balance"]
    DB.execute(
        "INSERT OR IGNORE INTO wallet(user_id, currency, amount) VALUES(?,?,0)", (uid, cur)
    )
    DB.commit()
    return DB.execute(
        "SELECT amount FROM wallet WHERE user_id=? AND currency=?", (uid, cur)
    ).fetchone()["amount"]


def move(uid: int, cur: str, delta: int, game: str) -> int:
    """Единственная точка изменения баланса. Отрицательный итог не допускается."""
    if cur == "credits":
        new = user(uid)["balance"] + delta
        if new < 0:
            raise ValueError("Недостаточно кредитов")
        DB.execute("UPDATE users SET balance=? WHERE id=?", (new, uid))
    else:
        new = wallet(uid, cur) + delta
        if new < 0:
            raise ValueError("Недостаточно средств")
        DB.execute(
            "UPDATE wallet SET amount=? WHERE user_id=? AND currency=?", (new, uid, cur)
        )
    DB.execute(
        "INSERT INTO ledger(user_id, game, currency, amount, balance_after) VALUES(?,?,?,?,?)",
        (uid, game, cur, delta, new),
    )
    DB.commit()
    return new


def fmt(n: int, cur: str = "credits") -> str:
    if cur == "rub":
        return f"{n / 100:.2f} ₽"
    if cur == "stars":
        return f"{n} ⭐"
    return f"{n:,}".replace(",", " ") + " кред."


def wallet_text(uid: int) -> str:
    return (
        f"☭ Кредиты (демо): <b>{fmt(wallet(uid, 'credits'))}</b>\n"
        f"₽ Рубли: <b>{fmt(wallet(uid, 'rub'), 'rub')}</b>\n"
        f"⭐ Stars: <b>{fmt(wallet(uid, 'stars'), 'stars')}</b>"
    )


# ---------- меню ----------

def menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Кошелёк", callback_data="wal")],
        [
            InlineKeyboardButton(text="Мины", callback_data="g:mines:10"),
            InlineKeyboardButton(text="Ракета", callback_data="g:rocket:10"),
        ],
        [
            InlineKeyboardButton(text="Башня", callback_data="g:tower:10"),
            InlineKeyboardButton(text="Футбол", callback_data="g:football:10"),
        ],
        [InlineKeyboardButton(text="Баскетбол", callback_data="g:basket:10")],
        [
            InlineKeyboardButton(text="Кейс ежедневный", callback_data="c:daily"),
            InlineKeyboardButton(text="Кейс еженедельный", callback_data="c:weekly"),
        ],
        [
            InlineKeyboardButton(text="Бомж · 9 кред.", callback_data="c:bomzh"),
            InlineKeyboardButton(text="Слабочек · 14 кред.", callback_data="c:slabochek"),
        ],
        [InlineKeyboardButton(text="Манифор · 39 кред.", callback_data="c:manifor")],
        [InlineKeyboardButton(text="Пополнить рубли", callback_data="top:rub")],
        [InlineKeyboardButton(text="⭐ Оформление за Stars", callback_data="top:stars")],
    ]
    if WEBAPP_URL.startswith("https://"):
        rows.append(
            [InlineKeyboardButton(text="Открыть BipBom WebApp", web_app=None, url=WEBAPP_URL)]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


HELP = (
    "<b>BipBom</b>\n"
    "☭ Кредиты — демо-валюта, только она ставится в играх и кейсах. "
    "Её нельзя купить, обменять или вывести.\n"
    "₽ Рубли и ⭐ Stars — для оформления и поддержки бота, в играх не участвуют.\n\n"
    "Ставка 1–{cap} кредитов. Игры считаются с преимуществом 4%."
)


# ---------- игры ----------

def play(uid: int, game: str, bet: int) -> str:
    row = user(uid)
    if bet < 1:
        return "Ставка должна быть положительной."
    if bet > row["max_bet"]:
        return f"Максимальная ставка в демо: {row['max_bet']}."
    if bet > row["balance"]:
        return "Недостаточно кредитов."
    move(uid, "credits", -bet, game + ":bet")

    if game == "mines":
        hits = random.randint(0, 4)
        prize = int(bet * 2.5) if hits < 3 else 0
        text = f"Мин подорвалось: <b>{hits}</b>"
    elif game == "rocket":
        crash = random.randint(1, 100)
        take = random.choice([0.5, 1, 1.5, 2, 2.5])
        prize = 0 if crash < take * 40 else int(bet * take)
        text = f"Ракета взорвалась на х{crash / 10:.1f}, вы забрали х{take}"
    elif game == "tower":
        floor = 0
        while floor < 10 and random.random() > 0.35:
            floor += 1
        mult = 1.2 if floor < 3 else 2.5 if floor < 6 else 5 if floor < 9 else 12
        prize = int(bet * mult)
        text = f"Пройдено этажей: <b>{floor}</b> (x{mult})"
    elif game == "football":
        outcome = random.choices(["goal", "miss", "post"], [45, 35, 20])[0]
        prize = int(bet * {"goal": 2.0, "miss": 0.0, "post": 1.6}[outcome])
        text = {"goal": "Гол! ⚽", "miss": "Мимо ворот.", "post": "Рикошет от штанги!"}[outcome]
    elif game == "basket":
        hit = random.random() < 0.5
        prize = int(bet * 1.9) if hit else 0
        text = "Мяч залетел! 🏀" if hit else "Не залетел."
    else:
        move(uid, "credits", bet, "error:unknown")
        return "Неизвестная игра."

    if prize:
        move(uid, "credits", prize, game + ":win")
    net = prize - bet
    return (
        f"{text}\nСтавка {fmt(bet)} → выигрыш {fmt(prize)} "
        f"({'+' if net >= 0 else '−'}{fmt(abs(net))})\n"
        f"Баланс: <b>{fmt(wallet(uid, 'credits'))}</b>"
    )


CASES = {
    "daily": {"min": 10, "max": 40},
    "weekly": {"min": 60, "max": 200},
    "bomzh": {"min": 5, "max": 15},
    "slabochek": {"min": 10, "max": 30},
    "manifor": {"min": 30, "max": 70},
}


def open_case(uid: int, name: str) -> str:
    case = CASES[name]
    row = user(uid)
    if name in ("daily", "weekly"):
        period = "-1 day" if name == "daily" else "-7 days"
        now = row["daily_at"] if name == "daily" else row["weekly_at"]
        if now and DB.execute(
            "SELECT datetime(?) > datetime('now', ?) AS ok", (now, period)
        ).fetchone()["ok"]:
            return "Кейс ещё не готов."
        if name == "daily":
            if row["balance"] < DAILY_GRANT:
                return "Ежедневный бонус — только для нулевого баланса."
            DB.execute("UPDATE users SET daily_at=datetime('now') WHERE id=?", (uid,))
            DB.commit()
    else:
        price = PRICES_CREDITS[name]
        if row["balance"] < price:
            return f"Недостаточно кредитов: нужно {price}."
        move(uid, "credits", -price, f"case:{name}:bet")
    prize = random.randint(case["min"], case["max"])
    move(uid, "credits", prize, f"case:{name}:win")
    return (
        f"Кейс <b>{name}</b>: выпало <b>{fmt(prize)}</b>.\n"
        f"Баланс: <b>{fmt(wallet(uid, 'credits'))}</b>"
    )


# ---------- пополнения ----------

async def pay_rub(bot: Bot, uid: int) -> str:
    # provider empty = Telegram Stars (XTR); при заданных ЮKassa — рубли.
    provider = os.getenv("PROVIDER_TOKEN", "")
    price, title = RUB_PACKS["rub_small"]
    rub = provider != ""
    try:
        await bot.send_invoice(
            chat_id=uid,
            title=title,
            description="Поддержка разработчика BipBom. Награды в игре нет.",
            payload=f"rub_small:{random.randint(1000, 9999)}",
            provider_token="" if not rub else provider,
            currency="RUB" if rub else "XTR",
            prices=[LabeledPrice(label=title, amount=price * 100 if rub else price)],
        )
        return "" if rub else "Оплата пойдёт в Stars: рубли ещё не подключены."
    except Exception as e:
        return f"Платёж недоступен: {type(e).__name__}"


async def pay_stars(bot: Bot, uid: int) -> str:
    try:
        await bot.send_invoice(
            chat_id=uid,
            title="Оформление BipBom",
            description="Открывает оформление профиля бота. Не даёт кредитов и ставок.",
            payload=IAP_STARS,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Оформление", amount=STAR_SKINS)],
        )
        return ""
    except Exception as e:
        return f"Платёж доступен только в клиентах с Telegram Stars: {type(e).__name__}"


# ---------- хендлеры ----------

class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        return bool(ADMIN_ID) and getattr(event.from_user, "id", None) == ADMIN_ID


def title_for(uid: int) -> str:
    u = user(uid)
    return HELP.format(cap=u["max_bet"])


@dp.message(Command("start"))
async def cmd_start(msg: Message) -> None:
    user(msg.from_user.id, msg.from_user.username or msg.from_user.first_name)
    await msg.answer(title_for(msg.from_user.id) + "\n\nВыберите действие:", reply_markup=menu())


@dp.message(Command("help"))
async def cmd_help(msg: Message) -> None:
    await msg.answer(title_for(msg.from_user.id), reply_markup=menu())


@dp.message(Command("balance"))
async def cmd_balance(msg: Message) -> None:
    await msg.answer(wallet_text(msg.from_user.id))


@dp.message(Command("topup"))
async def cmd_topup(msg: Message) -> None:
    await msg.answer(
        "Пополнение доступно для рублей и Stars. Кредиты не пополняются: это демо-валюта.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Пополнить рубли", callback_data="top:rub")],
                [InlineKeyboardButton(text="⭐ Оформление", callback_data="top:stars")],
            ]
        ),
    )


@dp.message(Command("refund"))
async def cmd_refund(msg: Message) -> None:
    uid = msg.from_user.id
    last = DB.execute(
        "SELECT amount FROM ledger WHERE user_id=? AND currency='credits' AND game LIKE '%:bet'"
        " ORDER BY id DESC LIMIT 1",
        (uid,),
    ).fetchone()
    if not last:
        await msg.answer("Возвращать нечего.")
        return
    back = min(-last["amount"], user(uid)["max_bet"])
    move(uid, "credits", back, "refund")
    await msg.answer(f"Последняя ставка {fmt(back)} возвращена (демо).")


@dp.message(Command("admin"), IsAdmin())
async def cmd_admin(bot: Bot, msg: Message) -> None:
    parts = msg.text.split()
    if len(parts) == 1 or parts[1] == "stats":
        u = DB.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        l = DB.execute("SELECT COUNT(*) c FROM ledger").fetchone()["c"]
        cash = DB.execute(
            "SELECT currency, SUM(amount) s FROM wallet GROUP BY currency"
        ).fetchall()
        lines = [f"Пользователей: {u}\nЗаписей в логе: {l}"]
        for r in cash:
            lines.append(f"{r['currency']}: {fmt(r['s'], r['currency'])}")
        await msg.answer("\n".join(lines))
    elif parts[1] == "ledger":
        uid = int(parts[2])
        rows = DB.execute(
            "SELECT currency, game, amount, balance_after, ts FROM ledger"
            " WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (uid,),
        ).fetchall()
        await msg.answer(
            "\n".join(
                f"{r['ts']} {r['currency']} {r['game']} {r['amount']:+d} → {r['balance_after']}"
                for r in rows
            )
            or "Записей нет."
        )
    elif parts[1] == "bet":
        uid, cap = int(parts[2]), int(parts[3])
        DB.execute("UPDATE users SET max_bet=? WHERE id=?", (cap, uid))
        DB.commit()
        await msg.answer(f"Лимит ставки {uid}: {cap} кредитов.")
    elif parts[1] == "refund" and len(parts) > 2:
        p = DB.execute(
            "SELECT * FROM payments WHERE charge_id=? AND refunded=0", (parts[2],)
        ).fetchone()
        if not p:
            await msg.answer("Платёж не найден или уже возвращён.")
            return
        if p["currency"] == "XTR":
            await bot.refund_star_payment(p["user_id"], p["charge_id"])
        else:
            await msg.answer("Возврат рублей — через панель провайдера, вручную.")
        DB.execute("UPDATE payments SET refunded=1 WHERE charge_id=?", (p["charge_id"],))
        DB.execute(
            "INSERT INTO ledger(user_id, game, currency, amount, balance_after) VALUES(?,?,?,?,?)",
            (p["user_id"], "refund", p["currency"], -p["amount"], wallet(p["user_id"], p["currency"])),
        )
        DB.commit()
        await msg.answer(f"Возврат {fmt(p['amount'], p['currency'])} оформлен.")
    elif parts[1] == "url":
        await msg.answer(f"WEBAPP_URL: {WEBAPP_URL or 'не задан'}")


@dp.callback_query(F.data == "wal")
async def cb_wallet(q: CallbackQuery) -> None:
    await q.message.answer(wallet_text(q.from_user.id))
    await q.answer()


@dp.callback_query(F.data.startswith("g:"))
async def cb_game(q: CallbackQuery) -> None:
    _, game, bet = q.data.split(":")
    cap = user(q.from_user.id)["max_bet"]
    bet = max(1, min(int(bet), cap))
    text = play(q.from_user.id, game, bet)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ещё раз", callback_data=f"g:{game}:{bet}"),
                InlineKeyboardButton(text="Меню", callback_data="menu"),
            ],
            [
                InlineKeyboardButton("−5", callback_data=f"g:{game}:{max(1, bet - 5)}"),
                InlineKeyboardButton("+5", callback_data=f"g:{game}:{min(cap, bet + 5)}"),
            ],
        ]
    )
    await q.message.answer(f"{game.capitalize()} · ставка {fmt(bet)}\n{text}", reply_markup=kb)
    await q.answer()


@dp.callback_query(F.data.startswith("c:"))
async def cb_case(q: CallbackQuery) -> None:
    await q.message.answer(open_case(q.from_user.id, q.data.split(":")[1]), reply_markup=menu())
    await q.answer()


@dp.callback_query(F.data == "menu")
async def cb_menu(q: CallbackQuery) -> None:
    await q.message.answer("Меню:", reply_markup=menu())
    await q.answer()


@dp.callback_query(F.data == "top:rub")
async def cb_top_rub(q: CallbackQuery, bot: Bot) -> None:
    await q.answer()
    note = await pay_rub(bot, q.from_user.id)
    if note:
        await q.message.answer(note)


@dp.callback_query(F.data == "top:stars")
async def cb_top_stars(q: CallbackQuery, bot: Bot) -> None:
    await q.answer()
    note = await pay_stars(bot, q.from_user.id)
    if note:
        await q.message.answer(note)


@dp.pre_checkout_query()
async def on_pre_checkout(q: PreCheckoutQuery) -> None:
    await q.answer(ok=q.payload in IAP or q.payload == IAP_STARS)


@dp.message(F.successful_payment)
async def on_paid(msg: Message) -> None:
    sp = msg.successful_payment
    uid = msg.from_user.id
    cur = "stars" if sp.currency == "XTR" else "rub"
    amount = sp.total_amount if cur == "rub" else sp.total_amount  # копейки / звёзды
    DB.execute(
        "INSERT OR IGNORE INTO payments(charge_id, user_id, currency, amount, payload)"
        " VALUES(?,?,?,?,?)",
        (sp.telegram_payment_charge_id, uid, cur, amount, sp.invoice_payload),
    )
    DB.commit()
    if sp.invoice_payload == IAP_STARS:
        DB.execute("UPDATE users SET skin='default' WHERE id=?", (uid,))
        DB.commit()
        await msg.answer("Оформление открыто. Спасибо!")
    else:
        move(uid, cur, amount, "topup")
        await msg.answer(
            f"Платёж получен: {fmt(amount, cur)}. Это поддержка — кредитов и ставок он не даёт.",
            reply_markup=menu(),
        )


def one_shot(args: str, uid: int) -> None:
    """Локальные команды: py bot.py grant <user_id> <кредиты>."""
    parts = args.split()
    if len(parts) == 3 and parts[0] == "grant":
        target, n = int(parts[1]), int(parts[2])
        user(target)
        print("Баланс:", fmt(move(target, "credits", n, "admin:grant")))
        return
    print("Usage: py bot.py grant <user_id> <кредиты>")


def main() -> None:
    args = " ".join(os.sys.argv[1:])
    if args:
        one_shot(args, 0)
        return
    if not TOKEN:
        raise SystemExit("BOT_TOKEN не задан.")
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print(f"BipBom запущен. WEBAPP_URL: {WEBAPP_URL or 'не задан'}")
    asyncio.run(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))


if __name__ == "__main__":
    main()
