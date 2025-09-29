import re

from mem.vector_stores.prompts import FACT_RETRIEVAL_PROMPT, PROFILE_RETRIEVAL_PROMPT


def get_fact_retrieval_messages(message, history=None):
    if history:
        return FACT_RETRIEVAL_PROMPT, f"History:{history}\n\nInput:{message}\nOutput:"
    else:
        return FACT_RETRIEVAL_PROMPT, f"Input:{message}\nOutput:"


def get_profile_retrieval_messages(message, history=None):
    if history:
        return PROFILE_RETRIEVAL_PROMPT, f"History:{history}\n\nInput:{message}\nOutput:"
    else:
        return PROFILE_RETRIEVAL_PROMPT, f"Input:{message}\nOutput:"



def parse_messages(messages):
    response = ""
    for msg in messages:
        if msg["role"] == "system":
            response = response + (
                f"[{msg['time']}] system: {msg['content']}\n" if 'time' in msg else f"system: {msg['content']}\n")
        if msg["role"] == "user":
            response = response + (
                f"[{msg['time']}] user: {msg['content']}\n" if 'time' in msg else f"user: {msg['content']}\n")
        if msg["role"] == "assistant":
            response = response + (
                f"[{msg['time']}] assistant: {msg['content']}\n" if 'time' in msg else f"assistant: {msg['content']}\n")
    return response.strip()


def remove_code_blocks(content: str) -> str:
    """
    Removes enclosing code block markers ```[language] and ``` from a given string.

    Remarks:
    - The function uses a regex pattern to match code blocks that may start with ``` followed by an optional language tag (letters or numbers) and end with ```.
    - If a code block is detected, it returns only the inner content, stripping out the markers.
    - If no code block markers are found, the original content is returned as-is.
    """
    pattern = r"^```[a-zA-Z0-9]*\n([\s\S]*?)\n```$"
    match = re.match(pattern, content.strip())
    return match.group(1).strip() if match else content.strip()


def get_image_description(image_obj, llm, vision_details):
    """
    Get the description of the image
    """

    if isinstance(image_obj, str):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "A user is providing an image. Provide a high level description of the image and do not include any additional text.",
                    },
                    {"type": "image_url", "image_url": {"url": image_obj, "detail": vision_details}},
                ],
            },
        ]
    else:
        messages = [image_obj]

    response = llm.generate_response(messages=messages)
    return response


def parse_vision_messages(messages, llm=None, vision_details="auto"):
    """
    Parse the vision messages from the messages
    """
    returned_messages = []
    for msg in messages:
        if msg["role"] == "system":
            returned_messages.append(msg)
            continue

        # Handle message content
        if isinstance(msg["content"], list):
            # Multiple image URLs in content
            description = get_image_description(msg, llm, vision_details)
            returned_messages.append({"role": msg["role"], "content": description})
        elif isinstance(msg["content"], dict) and msg["content"].get("type") == "image_url":
            # Single image content
            image_url = msg["content"]["image_url"]["url"]
            try:
                description = get_image_description(image_url, llm, vision_details)
                returned_messages.append({"role": msg["role"], "content": description})
            except Exception:
                raise Exception(f"Error while downloading {image_url}.")
        else:
            # Regular text content
            returned_messages.append(msg)

    return returned_messages
