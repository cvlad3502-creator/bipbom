import random, sqlite3, os, sys
os.chdir(r"C:\Users\виктория\Documents\MultiTool\BipBom")
if os.path.exists("bipbom.db"): os.remove("bipbom.db")
import bot
u = 777
bot.user(u, "tester")
assert bot.user(u)["balance"] == 1000
for g in ["mines","rocket","tower","football","basket"]:
    for _ in range(200):
        t = bot.play(u, g, 10)
        assert "Баланс" in t, (g, t)
print("games ok")
assert bot.play(u, "mines", 0).startswith("Ставка")
assert bot.play(u, "mines", 10**7).startswith("Недостаточно")
print("errors ok")
for c in ["bomzh","slabochek","manifor"]:
    assert "кредитов" in bot.open_case(u, c)
print("paid cases ok", "Баланс" in bot.open_case(u, "daily"))
assert "не готов" in bot.open_case(u, "daily")
print("daily lock ok")
before = bot.user(u)["balance"]
bot.charge(u, "football", 10); bot.credit(u, "refund", 10)
print("ledger rows", bot.DB.execute("select count(*) from ledger").fetchone()[0])
c = bot.DB.execute("select sum(amount) from ledger").fetchone()[0]
print("sum", c, "balance", bot.user(u)["balance"])
