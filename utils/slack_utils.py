import asyncio
import json
from math import ceil
from config import appBot, ALLOWED_CHANNEL_ID


def create_field(text, value):
    return {"type": "mrkdwn", "text": f"*{text}*\n{value}"}


def create_fields(index, source, fields_list):
    fields = [
        create_field(f"#{index}. {label}", source.get(key, "N/A"))
        for label, key in fields_list
    ]
    return fields


def format_slack_message(
    data, total, page, size=10, header_message="", user_id=None, ip_address=None
):
    blocks = []

    if header_message:
        blocks.append(
            {"type": "header", "text": {"type": "plain_text", "text": header_message}}
        )

    if "error" in data:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"⚠️ {data['error']}"},
            }
        )
    elif data:
        total_pages = ceil(total / size)
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Page {page}/{total_pages}"},
            }
        )

        start_ondex = (page - 1) * size + 1
        field_mappings = {
            "🔍 Standard Search Results": [
                ("User ID:", "user_id"),
                ("Username:", "username"),
                ("First Login:", "date_first"),
                ("Last Login:", "date_last"),
                ("IP Address:", "ip"),
                ("User Agent:", "user_agent"),
                ("ISP:", "isp"),
                ("Country:", "country"),
                ("Region:", "region"),
            ],
            "👤 Unique User IDs for IP": [("User ID:", "user_id")],
            "🌐 Unique IPs for User ID": [("IP Address:", "ip")],
            "🗓️ Date Range Search Results": [
                ("User ID:", "user_id"),
                ("Username:", "username"),
                ("First Login:", "date_first"),
                ("Last Login:", "date_last"),
                ("IP Address:", "ip"),
                ("User Agent:", "user_agent"),
                ("ISP:", "isp"),
                ("Country:", "country"),
                ("Region:", "region"),
            ],
        }

        for index, doc in enumerate(data, start=start_ondex):
            source = doc["_source"] if "_source" in doc else doc
            fields_list = field_mappings.get(header_message, [])
            fields = create_fields(index, source, fields_list)

            blocks.append({"type": "section", "fields": fields})
            blocks.append({"type": "divider"})

        buttons = []
        if page > 1:
            buttons.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":arrow_backward:"},
                    "action_id": "prev_page",
                    "value": json.dumps(
                        {
                            "page": page - 1,
                            "user_id": user_id,
                            "ip_address": ip_address,
                            "header_message": header_message,
                        }
                    ),
                }
            )
        if total > page * size:
            buttons.append(
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":arrow_forward:"},
                    "action_id": "load_more",
                    "value": json.dumps(
                        {
                            "page": page + 1,
                            "user_id": user_id,
                            "ip_address": ip_address,
                            "header_message": header_message,
                        }
                    ),
                }
            )

        if buttons:
            blocks.append({"type": "actions", "elements": buttons})

        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Total Entries: {total}"}],
            }
        )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*No data found for the provided parameters.*",
                },
            }
        )

    return blocks


# Security Related functions. Have to implment these :(


async def check_bot_channel():
    try:
        channels = []
        cursor = None
        while True:
            response = await appBot.client.conversations_list(
                types="public_channel,private_channel", limit=1000, cursor=cursor
            )
            channels.extend(response["channels"])
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
            await asyncio.sleep(2)

        # print(f"Total channels fetched: {len(channels)}")

        bot_channels = []
        for channel in channels:
            if channel.get("is_member"):
                bot_channels.append(
                    {
                        "id": channel["id"],
                        "name": channel.get("name"),
                        "creator": channel.get("creator"),
                    }
                )

        # print(f"🚨Bot is in channels: {bot_channels}")

        for channel in bot_channels:
            if channel["id"] != ALLOWED_CHANNEL_ID:
                await appBot.client.conversations_leave(channel=channel["id"])
                await appBot.client.chat_postMessage(
                    channel=ALLOWED_CHANNEL_ID,
                    text=f"🚨 The bot has been removed from a non-allowed channel (ID: {channel['id']}, Name: {channel['name']}, Creator: {channel['creator']}).",
                )

    except Exception as e:
        print(f"⚠️ Error checking bot channels: {e}")


async def is_user_authorized(user_id):
    try:
        user_info = await appBot.client.users_info(user=user_id)
        is_admin = user_info["user"].get("is_admin", False)
        is_owner = user_info["user"].get("is_owner", False)
        return is_owner or is_admin
    except Exception as e:
        print(f"⚠️ Error checking user authorization: {e}")
        return False


# async def report_bot_added(user_id, channelID):
#     try:
#         await appBot.client.chat_postMessage(
#             channel=ALLOWED_CHANNEL_`ID,
#             text=f"🚨 The bot was added to an unauthorized channel (ID: {channelID}) by <@{user_id}>."
#         )
#     except Exception as e:
#         print(f"⚠️ Error reporting bot addition: {e.response['error']}")
