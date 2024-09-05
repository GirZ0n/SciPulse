import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import ngrok
from slack_sdk import WebClient

logging.basicConfig(level=logging.DEBUG)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.protocol_version = "HTTP/1.1"
        self.send_response(200)

        content_len = int(self.headers.get('Content-Length'))
        raw_body = self.rfile.read(content_len).decode('utf-8')

        body = parse_qs(raw_body)

        slack_token = os.environ["SLACK_BOT_TOKEN"]
        client = WebClient(token=slack_token)

        self.end_headers()


logging.basicConfig(level=logging.INFO)
server = HTTPServer(("localhost", 0), Handler)
ngrok.listen(server)
server.serve_forever()
