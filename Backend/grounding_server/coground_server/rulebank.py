"""ルールバンクをファイルに残す（サーバーを再起動しても、ルールが消えないようにする）。

残すもの（住人が決めたもの）:
  norms          家庭ルールと片付けルール（origin = norm / tidy）
  zones          住人が決めた領域（進入禁止の範囲など。zones.define）
  pending_rules  登録の途中のルール（rules.confirm で確定する）
残さないもの: シーン、依頼、Plan、手で指定した行き先、属性の訂正（その場の状態なので）

COGROUND_RULE_BANK にファイルのパスを書くと有効になる（compose.yaml では /app/data/rule_bank.json）。
空なら何もしない（テストは StateStore を直接作るので、ファイルに触らない）。

- 起動時にファイルがあれば読み込む。読めなければ、壊れたファイルを *.broken に退避して、空から始める
- ルールが変わるたびに書き出す（中身が前と同じなら書かない）。一時ファイルに書いてから置き換えるので、途中で落ちても壊れない
- 形はルール画面（/rules）の「書き出す」と同じ {"rules": [...], "norms": [...]} に zones / pending_rules を足したもの。
  ただし norms には片付けルール（origin = tidy）も入る。片付けルールは、Unity の CoGroundRulesSender が
  つながるたびに rules.set で置き換える（Send On Connect をオフにすれば、ここに残したものを使い続ける）
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import SceneRegion
from .norms.model import NormRule, PendingRule

if TYPE_CHECKING:
    from .state import StateStore

log = logging.getLogger(__name__)

FORMAT_VERSION = 1


class RuleBank:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._last: str | None = None  # 最後に書いた（読んだ）中身。同じなら書かない

    @classmethod
    def from_env(cls) -> RuleBank | None:
        path = os.environ.get("COGROUND_RULE_BANK", "").strip()
        return cls(path) if path else None

    # ------------------------------------------------------------------ 中身

    @staticmethod
    def dump(state: StateStore) -> dict[str, Any]:
        return {
            "format": FORMAT_VERSION,
            "norms": [n.model_dump(mode="json", by_alias=True) for n in state.norms],
            "zones": [z.model_dump(mode="json") for z in state.zones.values()],
            "pending_rules": [p.model_dump(mode="json", by_alias=True) for p in state.pending_rules],
        }

    @staticmethod
    def _text(data: dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    # ------------------------------------------------------------------ 読み書き

    def load(self, state: StateStore) -> bool:
        """ファイルがあれば state に入れる。入れたら True"""
        if not self.path.exists():
            log.info("rule bank: %s が無いので、空から始める（ルールが変わったら作る）", self.path)
            return False
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            norms = [NormRule.model_validate(n) for n in data.get("norms", [])]
            zones = [SceneRegion.model_validate(z) for z in data.get("zones", [])]
            pending = [PendingRule.model_validate(p) for p in data.get("pending_rules", [])]
        except Exception as e:  # noqa: BLE001 壊れていても起動はする
            broken = self.path.with_suffix(self.path.suffix + ".broken")
            log.error("rule bank: %s を読めない（%s）。%s に退避して、空から始める", self.path, e, broken)
            try:
                self.path.replace(broken)
            except OSError:
                pass
            return False
        ids = [n.id for n in norms]
        if len(set(ids)) != len(ids):
            log.warning("rule bank: ID が重なっているルールがある: %s", sorted({i for i in ids if ids.count(i) > 1}))
        state.restore_rule_bank(norms, zones, pending)
        self._last = self._text(self.dump(state))
        log.info("rule bank: %s から読み込んだ（ルール %d、領域 %d、登録の途中 %d）",
                 self.path, len(norms), len(zones), len(pending))
        return True

    def save_if_changed(self, state: StateStore) -> bool:
        """中身が前と変わっていれば書き出す。書いたら True（失敗してもサーバーは止めない）"""
        try:
            text = self._text(self.dump(state))
        except Exception as e:  # noqa: BLE001
            log.error("rule bank: 書き出す中身を作れない: %s", e)
            return False
        if text == self._last:
            return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as e:
            log.error("rule bank: %s に書けない: %s", self.path, e)
            return False
        self._last = text
        log.info("rule bank: %s に書き出した", self.path)
        return True
