from __future__ import annotations

import re
from typing import Optional

from app.domains.conversations.model import AnswerSessionVO


class FollowUpDetector:
    NEW_TOPIC_PATTERNS = [
        r"\bsummarize\b",
        r"\boverall\b",
        r"\bin general\b",
        r"\bstart over\b",
        r"\bnew question\b",
        r"\bchange topic\b",
        r"换个问题",
        r"另一个问题",
        r"重新开始",
    ]

    FOLLOW_UP_PATTERNS = [
        r"^\s*(what about|how about|then|so|why|how)\b",
        r"^\s*(那|那么|所以|这个|这里|它)\b",
        r"\bmore details\b",
        r"\bexplain more\b",
        r"\bwhy\b",
        r"\bhow\b",
    ]

    def is_follow_up(
        self,
        question: str,
        session: Optional[AnswerSessionVO],
        document_id: Optional[int],
    ) -> bool:
        if not session:
            return False

        if session.document_id != document_id:
            return False

        q = (question or "").strip().lower()
        if not q:
            return False

        for pattern in self.NEW_TOPIC_PATTERNS:
            if re.search(pattern, q):
                return False

        for pattern in self.FOLLOW_UP_PATTERNS:
            if re.search(pattern, q):
                return True

        if len(q.split()) <= 8 and bool(getattr(session, "active_chunk_ids", [])):
            return True

        return False