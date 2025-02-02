import asyncio
import json
from math import ceil
from typing import List, Dict, Any, Optional
from config import app, ALLOWED_CHANNEL_ID


def create_field(text: str, value: str) -> Dict[str, str]:
    return {"type": "mrkdwn", "text": f"*{text}*\n{value}"}


def create_fields(
    index: int,
    source: Dict[str, Any],
    fields_list: List[tuple],
    include_index: bool = True,
) -> List[Dict[str, str]]:
    return [
        create_field(
            f"{index}. {label}" if i == 0 and include_index else label,
            source.get(key, "N/A"),
        )
        for i, (label, key) in enumerate(fields_list)
    ]


def format_slack_message(
    data: List[Dict[str, Any]],
    total: int,
    page: int,
    size: int = 10,
    header_message: str = "",
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_type: str = "standard_search",
) -> List[Dict[str, Any]]:
    blocks = []

    search_details = []
    if user_id:
        search_details.append(f"User: <@{user_id}>")
    if ip_address:
        search_details.append(f"IP: {ip_address}")
    if start_date and end_date:
        search_details.append(f"Date Range: {start_date} to {end_date}")
    
    search_type_display = {
        "standard_search": "Standard Search",
        "unique_user_for_ip": "Unique Users for IP",
        "unique_ip_for_user": "Unique IPs for User",
        "date_range": "Date Range Search"
    }.get(search_type, search_type)
    
    header_text = f"*{search_type_display}*"
    if search_details:
        header_text += f"\n{' | '.join(search_details)}"

    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text}
        }
    )

    if isinstance(data, dict) and "error" in data:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"⚠️ {data['error']}"},
            }
        )
        return blocks

    if not data:
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

    total_pages = ceil(total / size)
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"Page {page}/{total_pages}"},
        }
    )

    field_mappings = {
        "standard_search": [
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
        "unique_user_for_ip": [
            ("User ID:", "user_id"),
            ("First Login:", "date_first"),
            ("Last Login:", "date_last"),
            ("Total Logins:", "count")
        ],
        "unique_ip_for_user": [
            ("IP Address:", "ip"),
            ("First Login:", "date_first"),
            ("Last Login:", "date_last"),
            ("Total Logins:", "count")
        ],
        "date_range": [
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

    start_index = (page - 1) * size + 1
    for index, doc in enumerate(data, start=start_index):
        source = doc.get("_source", doc)
        fields_list = field_mappings.get(search_type, field_mappings["standard_search"])
        fields = create_fields(index, source, fields_list)
        blocks.extend([{"type": "section", "fields": fields}, {"type": "divider"}])

    buttons = []
    if page > 1:
        buttons.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Prev Page"},
                "action_id": "prev_page",
                "value": json.dumps(
                    {
                        "page": page - 1,
                        "user_id": user_id,
                        "ip_address": ip_address,
                        "search_type": search_type,
                        "start_date": start_date,
                        "end_date": end_date,
                    }
                ),
            }
        )
    if total > page * size:
        buttons.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Next Page"},
                "action_id": "load_more",
                "value": json.dumps(
                    {
                        "page": page + 1,
                        "user_id": user_id,
                        "ip_address": ip_address,
                        "search_type": search_type,
                        "start_date": start_date,
                        "end_date": end_date,
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

    return blocks


async def check_bot_channel():
    try:
        channels = await fetch_all_channels()
        bot_channels = [
            channel
            for channel in channels
            if channel.get("is_member") and channel["id"] != ALLOWED_CHANNEL_ID
        ]

        for channel in bot_channels:
            await remove_bot_from_channel(channel)

    except Exception as e:
        print(f"⚠️ Error checking bot channels: {e}")


async def fetch_all_channels():
    channels = []
    cursor = None
    while True:
        response = await app.client.conversations_list(
            types="public_channel,private_channel", limit=1000, cursor=cursor
        )
        channels.extend(response.get("channels", []))
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
        await asyncio.sleep(2)
    return channels


async def remove_bot_from_channel(channel):
    try:
        await app.client.conversations_leave(channel=channel["id"])
        await app.client.chat_postMessage(
            channel=ALLOWED_CHANNEL_ID,
            text=f"🚨 The bot has been removed from a non-allowed channel (ID: {channel['id']}, Name: {channel.get('name')}, Creator: {channel.get('creator')}).",
        )
    except Exception as e:
        print(f"⚠️ Error leaving channel {channel['id']}: {e}")


async def is_user_authorized(user_id: str) -> bool:
    try:
        user_info = await app.client.users_info(user=user_id)
        return user_info["user"].get("is_admin", False) or user_info["user"].get(
            "is_owner", False
        )
    except Exception as e:
        print(f"⚠️ Error checking user authorization: {e}")
        return False


# TODO: Fix this function
# async def report_bot_added(user_id: str, channel_id: str):
#     try:
#         await app.client.chat_postMessage(
#             channel=ALLOWED_CHANNEL_ID,
#             text=f"🚨 The bot was added to an unauthorized channel (ID: {channel_id}) by <@{user_id}>."
#         )
#     except Exception as e:
#         print(f"⚠️ Error reporting bot addition: {e}")
