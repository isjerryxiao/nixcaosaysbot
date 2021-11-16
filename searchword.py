from whoosh import index
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh import scoring
from jieba.analyse import ChineseAnalyzer
import jieba

from utils import find_cjk_letters, back_readline_s_lastline

from pathlib import Path
from threading import Lock
import json
import logging
import re

logger = logging.getLogger(__name__)
jieba.initialize()

class Search:
    def __init__(self):
        self._ix = None
        self._jsonl = Path("nickcaosays.txt")
        self._jsonl_last = Path("nickcaosays.txt.last")
        self._writelock = Lock()
        self._index_dir = Path("search-index")
        assert not self._index_dir.exists() or self._index_dir.absolute().is_dir()
        if not self._index_dir.exists():
            logger.info("making dir..")
            self._index_dir.mkdir()
        if not index.exists_in(str(self._index_dir), indexname="0"):
            logger.info("making index..")
            schema = Schema(id=ID(unique=True), text=TEXT(stored=True, analyzer=ChineseAnalyzer()))
            create_in(str(self._index_dir), schema, indexname="0")
    def add(self, fpath=None):
        fpath = fpath if fpath else self._jsonl
        logger.info("adding..")
        def textlen(text):
            cjklen = len(find_cjk_letters(text))
            noncjklen = len(text) - cjklen
            return cjklen * 2 + noncjklen/0.6
        MAX_TEXT_LENGTH = 8*2 * 4
        _line_last = self._jsonl_last.read_text().strip("\n") if self._jsonl_last.exists() else ""
        with open(fpath, "rb") as f, self._writelock:
            writer = self._ix.writer()
            try:
                pos = None
                if _line_last:
                    for line, pos in back_readline_s_lastline(f):
                        if line == _line_last:
                            logger.info(f"found last {line=} at {pos=}")
                            break
                if pos is not None:
                    logger.debug(f"seek {pos=}")
                    f.seek(pos, 2)
                w = 0
                rline = None
                while (line := f.readline()):
                    line = line.decode("utf-8")
                    _rline = line
                    line = line.strip()
                    if line:
                        text = json.loads(line)["text"]
                        if textlen(text) > MAX_TEXT_LENGTH:
                            continue
                        writer.add_document(id=text, text=text)
                        w += 1
                        if w % 1000 == 0:
                            print('\r', end='', flush=True)
                            print(f"[+{w//1000}k]", end='', flush=True)
                        rline = line
                print()
            except (Exception, KeyboardInterrupt):
                logger.exception("error while adding, cancelling..")
                writer.cancel()
            else:
                if w > 0:
                    logger.info('committing..')
                    writer.commit()
                    if getattr(self, '_searcher', None):
                        self._searcher = self._searcher.refresh()
                        self.search("")
                else:
                    writer.cancel()
                logger.info(f"added {w} entries")
                if rline is not None:
                    logger.info(f"writing last {rline=}")
                    self._jsonl_last.write_text(rline)
                return w
    def search(self, query):
        myquery = self._parser.parse(query)
        result = self._searcher.search(myquery, limit=20, collapse="id", collapse_limit=1)
        got = [r["text"] for r in result]
        logger.info(f"{query=} {got=} {result.runtime=}")
        return got
    def __enter__(self):
        self._ix = open_dir(str(self._index_dir), indexname="0")
        self._parser = QueryParser("text", self._ix.schema)
        self._searcher = self._ix.searcher(weighting=scoring.BM25F(B=0.9))
        self.search("")
        return self
    def __exit__(self, *_) -> None:
        if self._searcher:
            self._searcher.close()
        if self._ix:
            self._ix.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    with Search() as s:
        while i:=input(">"):
            if i == "/add":
                s.add()
            else:
                s.search(i)
