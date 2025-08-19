import operator
import os
import time
from typing import List

import feedparser
from feedparser import FeedParserDict
from grazie.api.client.chat.prompt import ChatPrompt
from grazie.api.client.endpoints import GrazieApiGatewayUrls
from grazie.api.client.gateway import GrazieApiGatewayClient, AuthType, GrazieAgent
from grazie.api.client.profiles import Profile
from slack_sdk import WebClient

from lib.slack_utils.paper_post import PaperReviewState, PaperPost, PaperCategory
from lib.slack_utils.wrappers import find_channels_with_app, send_message, update_message

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("post_papers")

TAG_WHITELIST = ("cs.HC", "cs.AI", "cs.CY", "cs.SE", "cs.LG", "cs.CL", "cs.IR", "cs.PL")

def _get_grazie_auth_type() -> AuthType:
    match os.environ["GRAZIE_AUTH_TYPE"]:
        case "SERVICE":
            return AuthType.SERVICE
        case "APPLICATION":
            return AuthType.APPLICATION
        case "USER":
            return AuthType.USER
        case _:
            raise ValueError(f"Invalid GRAZIE_AUTH_TYPE: {os.environ['GRAZIE_AUTH_TYPE']}")


def _fetch_papers_from_arxiv_tag(subject: str) -> List[FeedParserDict]:
    parsed_feed = feedparser.parse(f"https://rss.arxiv.org/rss/{subject}")
    return [item for item in parsed_feed["items"] if item["arxiv_announce_type"] not in ("replace", "replace-cross")]


def fetch_arxiv_papers() -> List[FeedParserDict]:
    cs_cy_papers = _fetch_papers_from_arxiv_tag("cs.CY")
    logger.debug(f"Fetched {len(cs_cy_papers)} CS.CY papers")

    cs_hc_papers = _fetch_papers_from_arxiv_tag("cs.HC")
    logger.debug(f"Fetched {len(cs_hc_papers)} CS.HC papers")

    unfiltered_arxiv_papers = cs_cy_papers + cs_hc_papers
    logger.debug(f"Fetched {len(unfiltered_arxiv_papers)} unfiltered papers")

    unique_arxiv_papers = list({paper["link"]: paper for paper in unfiltered_arxiv_papers}.values())
    logger.debug(f"Fetched {len(unique_arxiv_papers)} unique papers")

    return [
        paper
        for paper in unique_arxiv_papers
        if all(map(lambda tag: tag in TAG_WHITELIST, set(map(operator.itemgetter("term"), paper["tags"]))))
    ]

def resolve_papers_using_llm(slack_client: WebClient, channel: str, paper_posts_ts: dict[str, PaperPost]):
    bot_id = slack_client.auth_test()["user_id"]

    grazie_client = GrazieApiGatewayClient(
        url=GrazieApiGatewayUrls.PRODUCTION,
        grazie_jwt_token=os.environ["GRAZIE_JWT_TOKEN"],
        auth_type=_get_grazie_auth_type(),
        grazie_agent=GrazieAgent(name="openai-gpt-4o", version="dev"),
    )

    for paper_post_ts, paper_post in paper_posts_ts.items():
        prompt = ChatPrompt()

        prompt.add_system(
            """
            **You are an expert reviewer of scientific papers in the field of educational research.**

            Your task: **Given a paper's title and abstract, identify the most appropriate research field** from the list below.
            
            ### Research Fields:
            - Metaphors and Analogies in Education  
            - Research design  
            - Apply LLM for education  
            - Test generation  
            - Using subgoals in programming education  
            - Personalized help  
            - Low/no code in Edu  
            - Tracking Student Data  
            - Debugging  
            - Learning/teaching practices  
            - Gamified learning
            
            ### Response Rules:
            1. If the paper clearly fits one of the listed fields, **respond with the exact name** of that field.
            2. If the paper is about education but **does not fit** any listed field:
               - Respond with:  
                 - **"Others (ML-related)"** if the paper is education-related and uses machine learning  
                 - **"Others (non-ML-related)"** if it’s education-related but **not** ML-based
            3. If the paper is **not about education at all**, respond with **"Unknown"**.
            
            **Respond with only the field name — no explanation, no extra text, not quotes**
            """
        )

        prompt.add_user(f"Title: {paper_post.title}\n\nAbstract: {paper_post.abstract}")

        try:
            response = grazie_client.chat(prompt, Profile.OPENAI_GPT_4_O)
            logger.debug(f"Response: {response}")
        except Exception as e:
            logger.exception(f"Error occurred while waiting for response from Grazie API Gateway: {e}")
            continue

        if response.content == PaperCategory.UNKNOWN.value:
            paper_post.update_state(PaperReviewState.REJECT.value, bot_id, PaperCategory.UNKNOWN)
        elif response.content in PaperCategory.values():
            paper_post.update_state(PaperReviewState.ACCEPT.value, bot_id, PaperCategory(response.content))
        else:
            logger.error(f"Unexpected response: {response.content}")
            continue

        update_message(
            slack_client,
            channel=channel,
            ts=paper_post_ts,
            blocks=paper_post.to_blocks(),
            metadata=paper_post.to_slack_metadata(),
            text=f"An error occurred while posting {paper_post.link}",
        )


def main():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    slack_client = WebClient(token=slack_token)

    arxiv_papers = fetch_arxiv_papers()
    logger.info(f"Fetched {len(arxiv_papers)} arxiv papers")

    channels = find_channels_with_app(slack_client)
    logger.debug(f"Found {len(channels)} channels where the app is a member")

    paper_posts_ts = {}
    for channel in channels:
        logger.debug(f"Posting to {channel}")

        if not arxiv_papers:
            send_message(
                slack_client,
                channel=channel,
                text=f'There are no papers for {time.strftime("%d-%m-%Y")} :chipi-chipi-chapa-chapa:',
            )

            continue

        thread_ts = send_message(slack_client, channel=channel, text=f'Papers for {time.strftime("%d-%m-%Y")}')
        logger.debug(f"TS: {thread_ts}")

        for arxiv_paper in arxiv_papers:
            paper_post = PaperPost.from_arxiv(arxiv_paper)

            logger.debug(f"Posting: {paper_post.link}")

            paper_post_ts = send_message(
                slack_client,
                channel=channel,
                thread_ts=thread_ts,
                blocks=paper_post.to_blocks(),
                metadata=paper_post.to_slack_metadata(),
                text=f"An error occurred while posting {paper_post.link}",
            )

            paper_posts_ts[paper_post_ts] = paper_post

            time.sleep(1)  # Better to sleep for 1 second to avoid spamming Slack

        logger.info(f"Posting to {channel} completed")

        logger.info(f"Automatic review started in {channel}")
        resolve_papers_using_llm(slack_client, channel, paper_posts_ts)
        logger.info(f"Automatic review completed in {channel}")


if __name__ == "__main__":
    main()
