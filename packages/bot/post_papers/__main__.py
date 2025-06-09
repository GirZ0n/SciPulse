import logging
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

from paper_post import PaperPost
from paper_post import PaperReviewState
from wrappers import find_channels_with_app, send_message, update_message

TAG_WHITELIST = ("cs.HC", "cs.AI", "cs.CY", "cs.SE", "cs.LG", "cs.CL", "cs.IR", "cs.PL")


def _fetch_papers_from_arxiv_tag(subject: str) -> List[FeedParserDict]:
    parsed_feed = feedparser.parse(f"https://rss.arxiv.org/rss/{subject}")
    return [item for item in parsed_feed["items"] if item["arxiv_announce_type"] not in ("replace", "replace-cross")]


def fetch_arxiv_papers() -> List[FeedParserDict]:
    cs_cy_papers = _fetch_papers_from_arxiv_tag("cs.CY")
    logging.debug(f"Fetched {len(cs_cy_papers)} CS.CY papers")

    cs_hc_papers = _fetch_papers_from_arxiv_tag("cs.HC")
    logging.debug(f"Fetched {len(cs_hc_papers)} CS.HC papers")

    unfiltered_arxiv_papers = cs_cy_papers + cs_hc_papers
    logging.debug(f"Fetched {len(unfiltered_arxiv_papers)} unfiltered papers")

    unique_arxiv_papers = list({paper["link"]: paper for paper in unfiltered_arxiv_papers}.values())
    logging.debug(f"Fetched {len(unique_arxiv_papers)} unique papers")

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
        auth_type=AuthType.APPLICATION,
        grazie_agent=GrazieAgent(name="openai-gpt-4o", version="dev"),
    )

    for paper_post_ts, paper_post in paper_posts_ts.items():
        prompt = ChatPrompt()

        prompt.add_system(
            """
            You are a scientific paper reviewer.
            
            You will be given a paper title and abstract.
            Your task is to decide whether the paper aligns with your research fields.
            
            Your research fields are:
            * Metaphors and analogies in education  
            * Research design  
            * Applying LLMs in education  
            * Test generation  
            * Using subgoals in programming education  
            * Personalized help  
            * Low/no-code tools in education  
            * Tracking student data  
            * Debugging  
            * Learning and teaching practices  
            * Gamified learning  
            
            If the paper aligns with **any** of your research fields, respond with "accept". 
            Otherwise, respond with "reject".
            
            You MUST respond with only one word: either "accept" or "reject".
            No additional text is allowed.
            """
        )

        prompt.add_user(f"Title: {paper_post.title}\n\nAbstract: {paper_post.abstract}")

        try:
            response = grazie_client.chat(prompt, Profile.OPENAI_GPT_4_O)
        except Exception as e:
            logging.error("Error occurred while waiting for response from Grazie API Gateway:", e)
            continue

        if response.content.lower() == "accept":
            paper_post.update_state(PaperReviewState.ACCEPT.value, bot_id)
        elif response.content.lower() == "reject":
            paper_post.update_state(PaperReviewState.REJECT.value, bot_id)
        else:
            logging.error(f"Unexpected response: {response.content}")
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
    logging.info(f"Fetched {arxiv_papers} arxiv papers")

    channels = find_channels_with_app(slack_client)
    logging.debug(f"Found {len(channels)} channels where the app is a member")

    paper_posts_ts = {}
    for channel in channels:
        logging.debug(f"Posting to {channel}")

        if not arxiv_papers:
            send_message(
                slack_client,
                channel=channel,
                text=f'There are no papers for {time.strftime("%d-%m-%Y")} :chipi-chipi-chapa-chapa:',
            )

            continue

        thread_ts = send_message(slack_client, channel=channel, text=f'Papers for {time.strftime("%d-%m-%Y")}')
        logging.debug(f"TS: {thread_ts}")

        for arxiv_paper in arxiv_papers:
            paper_post = PaperPost.from_arxiv(arxiv_paper)

            logging.debug(f"Posting: {paper_post.link}")

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

        logging.info(f"Posting to {channel} completed")

        logging.info(f"Automatic review started in {channel}")
        resolve_papers_using_llm(slack_client, channel, paper_posts_ts)
        logging.info(f"Automatic review completed in {channel}")


if __name__ == "__main__":
    main()
