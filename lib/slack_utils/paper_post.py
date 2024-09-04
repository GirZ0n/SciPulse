from dataclasses import dataclass
from enum import Enum
from textwrap import shorten
from typing import Optional, List, Dict

from dataclasses_json import dataclass_json
from feedparser import FeedParserDict
from html2text import html2text as h2t


class PaperReviewState(Enum):
    ACCEPT = 'accept'
    REJECT = 'reject'

    @classmethod
    def values(cls) -> List[str]:
        return [member.value for member in cls]

    def to_button_text(self) -> str:
        return self.value.capitalize()

    def to_action_text(self) -> str:
        return self.value + 'ed'

    def to_emoji(self) -> str:
        if self == self.ACCEPT:
            return ':white_check_mark:'

        if self == self.REJECT:
            return ':x:'

        return ''


@dataclass_json
@dataclass
class PaperPost:
    title: str
    link: str
    abstract: str
    state: Optional[PaperReviewState] = None
    reviewer: Optional[str] = None

    @classmethod
    def from_arxiv(cls, paper: FeedParserDict) -> "PaperPost":
        return cls(
            title=paper['title'],
            link=paper['link'],
            # TODO: make the extracting abstract better?
            abstract=h2t(paper['description'].split(' ', 5)[5], bodywidth=0),
        )

    @classmethod
    def from_slack_metadata(cls, metadata: Dict) -> "PaperPost":
        return cls.from_dict(metadata['event_payload'])

    def to_slack_metadata(self) -> Dict:
        return {"event_type": "post_created", "event_payload": self.to_dict(encode_json=True)}

    def update_state(self, action: str, username: str):
        if action not in PaperReviewState.values():
            self.state = None
            self.reviewer = None
            return

        self.state = PaperReviewState(action)
        self.reviewer = username

    def to_blocks(self) -> List[Dict]:
        base = [
            # Shorten the title as the maximum length of a header is 150
            {"type": "header", "text": {"type": "plain_text", "text": f"{shorten(self.title, 150)}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Link:* {self.link}"}},
            # Shorten the abstract as the maximum length of a section is 3000
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Abstract:*\n{shorten(self.abstract, 3000)}"}},
        ]

        interactive_elements = []

        if self.state is None:
            interactive_elements.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": PaperReviewState.ACCEPT.to_button_text()},
                    "style": "primary",
                    "action_id": PaperReviewState.ACCEPT.value,
                }
            )

            interactive_elements.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": PaperReviewState.REJECT.to_button_text()},
                    "style": "danger",
                    "action_id": PaperReviewState.REJECT.value,
                }
            )
        else:
            base.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": (
                                f"{self.state.to_emoji()} "
                                f"@{self.reviewer} has {self.state.to_action_text()} this paper."
                            ),
                        },
                    ],
                }
            )

            interactive_elements.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": 'Cancel'},
                    "action_id": 'cancel',
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Are you sure?"},
                        "text": {"type": "plain_text", "text": "Do you want to cancel the review status?"},
                        "confirm": {"type": "plain_text", "text": "Yes"},
                        "deny": {"type": "plain_text", "text": "No"},
                    },
                }
            )

        return base + [{"type": "actions", "elements": interactive_elements}]
