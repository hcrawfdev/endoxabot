import base64
import os
import json
from operator import itemgetter
from typing import Union
import httpx
from bs4 import BeautifulSoup
from slack_bolt import App
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from conf_ingest import conf_ingest
from qa import ask_question
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))



@app.event("app_mention")
async def handle_app_mention_events(body, logger, say):
    threadTs = ''
    print(body["event"])
    if 'thread_ts' in body['event']:
     threadTs = body['event']['thread_ts']
    else:
        threadTs= body['event']['ts']
    await say("Thinking...", thread_ts=threadTs)
    for i in body["event"]["blocks"]:
        if i["type"] == "rich_text":
            for j in i["elements"]:
                if j["type"] == "rich_text_section":
                    for k in j["elements"]:
                        if k["type"] == "text":
                            question = k["text"]
                            print(question)
                            result = await ask_question(question)
                            await say(f"Answer: {result['answer']}",thread_ts=threadTs)
                            await say(f"Sources: {result['sources']}",thread_ts=threadTs)
    logger.info(body)


async def ingest_confluence(confluence_url, confluence_uname, confluence_key):
    

    async with httpx.AsyncClient() as client:
        auth = f'{confluence_uname}:{confluence_key}'
        byte_str = auth.encode('ascii')
        base64_bytes = base64.b64encode(byte_str)
        base64_str = base64_bytes.decode("ascii")
        
        auth_header  = {'Authorization': 'Basic' + ' ' + base64_str}
      

        sources_to_ingest = []
        data_to_ingest = []
        print("ingesting loop: ", confluence_url)
        last_result_length = 25
        confluence_index = 0

        while(last_result_length != 0):
            print("current index: ", confluence_index)
            incrementing_url = f'{confluence_url}/wiki/rest/api/content?expand=body.view&start={confluence_index}'
            print("ingesting loop: ", incrementing_url)
            response = await client.get(incrementing_url, headers=auth_header)
            print(response.status_code)
            r_json = response.json()
            content_list = r_json
            for(i, content) in enumerate(content_list['results']):
                soup = BeautifulSoup(content['body']['view']['value'], 'lxml')
                data_to_ingest.append(soup.get_text())
                sources_to_ingest.append(content['title'])
            confluence_index = confluence_index + 25
            last_result_length = content_list['size']

        conf_ingest(data_to_ingest, sources_to_ingest)
        return "hi"

@app.view("ingest_confluence")
async def initiate_ingest_confluence(ack, body, logger):
    #print('body: ', body)
    await ack()
    json_object = json.dumps(body['view']['state']['values'], indent = 4) 
    print(json_object)
    confluence_url, confluence_email, confluence_key = itemgetter('confluence_url', 'confluence_email', 'confluence_key')(body['view']['state']['values'])
    
    confluence_url = confluence_url['confluence_url']['value']
    confluence_email = confluence_email['confluence_email']['value']
    confluence_key = confluence_key['confluence_key']['value']
    
    await ingest_confluence(confluence_url, confluence_email, confluence_key)


@app.command("/ingest-confluence")
async def open_modal(ack, body, client):
    await ack()
    await client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            # View identifier
            "callback_id": "ingest_confluence",
            "title": {"type": "plain_text", "text": "Import your Confluence"},
            "submit": {"type": "plain_text", "text": "Start Import"},
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "This information is used for the import process only and is never stored."},
                },
                 {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "Please ensure the user that created this API key has read access to all the Confluence spaces you want to import."},
                },
                {
                    "type": "input",
                    "block_id": "confluence_url",
                    "label": {"type": "plain_text", "text": "Atlassian URL"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "confluence_url",
                        "multiline": False,
                        "placeholder": {"type": "plain_text", "text": "https://your-domain.atlassian.net"}
                    }
                },
                {
                    "type": "input",
                    "block_id": "confluence_email",
                    "label": {"type": "plain_text", "text": "Confluence Email"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "confluence_email",
                        "multiline": False
                    }
                },
                {
                    "type": "input",
                    "block_id": "confluence_key",
                    "label": {"type": "plain_text", "text": "Confluence API Key"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "confluence_key",
                        "multiline": False
                    }
                }
            ]
        }
    )



async def main():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
  