import logging
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN="token_here"
STICKER_CHANNEL = -1000000000000
OWNER = 0
CMDTEMPLATE='(let* (\n        (myimage (car (gimp-image-new 1 1 0)))\n        (mylayer (car (gimp-text-layer-new myimage "{text}" "Noto Sans" 41 0)))\n    )\n    (gimp-image-insert-layer myimage mylayer 0 0)\n    (gimp-text-layer-set-color mylayer \'(255 255 255))\n    (gimp-item-transform-translate mylayer 0 0)\n    (gimp-image-resize-to-layers myimage)\n    (file-png-save-defaults RUN-NONINTERACTIVE myimage (car(gimp-image-get-active-drawable myimage)) "{file}" "{file}")\n)\n(gimp-quit 0)\n'

import sqlite3
from uuid import uuid4
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, Filters
from telegram import InlineQueryResultCachedSticker, InlineQueryResultArticle, InputTextMessageContent

from pathlib import Path
import subprocess
from threading import Lock
import json
from PIL import Image, ImageDraw
from io import BytesIO
from time import time

from searchword import Search

class DB:
    _database = Path("stickers.sqlite")
    _table = "stickers"
    _timeout = 5
    _migrate_from = Path("nixcao_stickers.jsonl")
    def __init__(self):
        con = sqlite3.connect(self._database, timeout=self._timeout)
        cur = con.cursor()
        cur.execute(f"CREATE TABLE if not exists {self._table} (text TEXT primary key not null, id TEXT not null)")
        con.commit()
        con.close()
        if self._migrate_from.exists():
            self._migrate()
    def _migrate(self):
        con = sqlite3.connect(self._database, timeout=self._timeout)
        cur = con.cursor()
        with open(self._migrate_from, "r") as f:
            while (line := f.readline()):
                l = line.strip()
                if l:
                    j = json.loads(l)
                    cur.execute(f"INSERT or REPLACE into {self._table} values (?, ?)", (str(j["text"]), str(j["id"])))
        con.commit()
        con.close()
    def write(self, text, sid):
        con = sqlite3.connect(self._database, timeout=self._timeout)
        cur = con.cursor()
        cur.execute(f"INSERT or REPLACE into {self._table} values (?, ?)", (str(text), str(sid)))
        con.commit()
        con.close()
        return None
    def read(self, text):
        con = sqlite3.connect(self._database, timeout=self._timeout)
        cur = con.cursor()
        for _, sid in cur.execute(f"SELECT * from {self._table} where text = ?", (text,)):
            return sid
        con.close()
        return None

def search(pattern):
    return searchmgr.search(pattern)

def _gimp_draw(*args):
    draw_lock = Lock()
    title_layer_b = BytesIO(Path("nickcao_120_20_1a1429.png").read_bytes())
    msgbox_layer_b = BytesIO(Path("nickcao_msgbox.png").read_bytes())
    title_layer = Image.open(title_layer_b)
    msgbox_layer = Image.open(msgbox_layer_b)
    s_title_layer_b = BytesIO(Path("service_120_20_1a1429.png").read_bytes())
    s_msgbox_layer_b = BytesIO(Path("service_msgbox.png").read_bytes())
    s_title_layer = Image.open(s_title_layer_b)
    s_msgbox_layer = Image.open(s_msgbox_layer_b)
    del title_layer_b, msgbox_layer_b, s_title_layer_b, s_msgbox_layer_b
    MSGBOX_MINX = 96
    MSGBOX_MAXX = 512
    MSGBOX_MAXY = 161
    MSGBOX_SPLITX = 160
    TITLE_X = 120
    TITLE_Y = 20
    TEXT_X = 123
    TEXT_Y_MIN = 71
    TEXT_Y_MAX = TEXT_Y_MIN+60
    msgbox_left = msgbox_layer.crop((0, 0, MSGBOX_SPLITX, msgbox_layer.height))
    msgbox_right = msgbox_layer.crop((MSGBOX_SPLITX, 0, msgbox_layer.width, msgbox_layer.height))
    s_msgbox_left = s_msgbox_layer.crop((0, 0, MSGBOX_SPLITX, msgbox_layer.height))
    s_msgbox_right = s_msgbox_layer.crop((MSGBOX_SPLITX, 0, msgbox_layer.width, msgbox_layer.height))
    def draw(text, service=False):
        with draw_lock:
            logger.info(f"gimp_draw {text}")
            _title_layer = s_title_layer if service else title_layer
            _msgbox_layer = s_msgbox_layer if service else msgbox_layer
            _msgbox_left = s_msgbox_left if service else msgbox_left
            _msgbox_right = s_msgbox_right if service else msgbox_right
            gimpfpath = Path("/tmp/nixcao_text.png")
            commands = CMDTEMPLATE.format(file=gimpfpath, text=text)
            subprocess.run(["gimp", "-i", "-b", "-"], input=commands.encode("utf-8"), capture_output=True, check=True, timeout=30)
            assert gimpfpath.exists()
            text_layer_b = BytesIO(gimpfpath.read_bytes())
            gimpfpath.unlink()
            text_layer = Image.open(text_layer_b)
            outimg_width = max(text_layer.width - ((MSGBOX_MAXX - (TEXT_X - MSGBOX_MINX)) - TEXT_X), 0) + _msgbox_layer.width
            outimg = Image.new("RGBA", (outimg_width, _msgbox_layer.height), color=(0,0,0,0))
            outimg.paste(_msgbox_left)
            outdraw = ImageDraw.Draw(outimg)
            rect_x2 = MSGBOX_SPLITX+outimg.width-_msgbox_layer.width
            outdraw.rectangle((MSGBOX_SPLITX, 0, rect_x2-1, MSGBOX_MAXY-1), (0x1a, 0x14, 0x29, 0xff))
            outimg.paste(_msgbox_right, (rect_x2, 0))
            outimg.paste(_title_layer, (TITLE_X, TITLE_Y))
            outimg.alpha_composite(text_layer, (TEXT_X, TEXT_Y_MAX-text_layer.height))
            outbio = BytesIO()
            outimg.save(outbio, format="webp", quality=90)
            return outbio.getvalue()
    return draw
gimp_draw = _gimp_draw()

def get_sticker_id(bot, text, service=False):
    origtext = text
    text = text.lstrip("\x00")
    text = text.replace("\\", "\\\\",).replace("\"", "\\\"")
    image = gimp_draw(text, service)
    msg = bot.send_sticker(STICKER_CHANNEL, image)
    sticker_id = str(msg.sticker.file_id)
    assert sticker_id
    db.write(origtext, sticker_id)
    return sticker_id


def handle_inline_query(update, context):
    fallback_msg = InlineQueryResultArticle(
        id="error",
        title="不行！",
        description="你可草没说过这话！",
        input_message_content=InputTextMessageContent(
            message_text="你可草可没说过这话，换一句吧。",
            disable_web_page_preview=True
        ),
        reply_markup=None,
        thumb_url="https://en.gravatar.com/userimage/88118864/d5357d40ac798193f13ee95e1c1eb86a.png",
        thumb_width=80,
        thumb_height=80
    )
    query = update.inline_query.query.strip()
    results = list()
    try:
        if query:
            search_result = search(query)
            logger.info(f"query {query=} from {update.effective_user.first_name} {update.effective_user.id} {search_result=}")
            if search_result:
                stickers_gen = 0
                for stickers_idx, s in enumerate(search_result):
                    if "\x00" in s:
                        continue
                    if stickers_gen >= 1:
                        _msg = f"\x00有{len(search_result)-stickers_idx}条结果未列出！"
                        _sticker_id = db.read(_msg)
                        if _sticker_id is None:
                            _sticker_id = get_sticker_id(context.bot, _msg, service=True)
                        results.append(InlineQueryResultCachedSticker(id=str(uuid4()), sticker_file_id=_sticker_id))
                        break
                    sticker_id = db.read(s)
                    if sticker_id is None:
                        stickers_gen += 1
                        sticker_id = get_sticker_id(context.bot, s)
                    results.append(InlineQueryResultCachedSticker(id=str(uuid4()), sticker_file_id=sticker_id))
        else:
            fallback_msg.title = "啥都没有！"
            fallback_msg.description="请输入"
    except Exception:
        errid = hash(str(time()))
        logger.exception(f"rayid: {errid}")
        fallback_msg.title = "不好！出问题了！"
        fallback_msg.description=f"错误id: {errid}"
        fallback_msg.input_message_content.message_text=f"bot怕怕了，错误id: {errid}"
        results.clear()
    if not results:
        results.append(fallback_msg)
    update.inline_query.answer(results, cache_time=0, is_personal=False)

def handle_command_start(update, context):
    logger.info(f"start from {update.effective_user.first_name} {update.effective_user.id}")
    update.effective_message.reply_text("/say something")
def handle_command_addword(update, context):
    logger.warning(f"addword from {update.effective_user.first_name} {update.effective_user.id}")
    if update.effective_user.id != OWNER:
        return
    try:
        logger.warning("performing addword")
        words = searchmgr.add()
    except Exception as err:
        logger.exception("addword failed")
        update.effective_message.reply_text(repr(err))
    else:
        update.effective_message.reply_text(f"added {words=}")
def handle_command_say(update, context):
    query = " ".join(context.args)
    query = query[:50]
    if query:
        logger.info(f"say {context.args=} from {update.effective_user.first_name} {update.effective_user.id} {query=}")
        sticker_id = db.read(query) or get_sticker_id(context.bot, query)
        context.bot.send_sticker(update.effective_chat.id, sticker_id, reply_to_message_id=update.effective_message.message_id)
    else:
        update.effective_message.reply_text("/say something")

if __name__ == "__main__":
    db = DB()
    with Search() as searchmgr:
        updater = Updater(TOKEN, workers=1, use_context=True)
        updater.dispatcher.add_handler(InlineQueryHandler(handle_inline_query))
        updater.dispatcher.add_handler(CommandHandler('start', handle_command_start, Filters.chat_type.private))
        updater.dispatcher.add_handler(CommandHandler('say', handle_command_say, Filters.chat_type.private))
        updater.dispatcher.add_handler(CommandHandler('addword', handle_command_addword))
        updater.start_polling()
        updater.idle()
