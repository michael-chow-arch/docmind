from __future__ import annotations

import re
from typing import Optional

from app.domains.conversations.model import AnswerSessionVO


class FollowUpDetector:
    # Heuristic: phrases that usually signal a new topic (not a follow-up).
    NEW_TOPIC_SIGNALS = [
        r"\bsummarize\b",
        r"\boverall\b",
        r"\bin general\b",
        r"\bstart over\b",
        r"\bnew question\b",
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
        question_lower = question.lower()
        for pattern in self.NEW_TOPIC_SIGNALS:
            if re.search(pattern, question_lower):
                return False
        return True
