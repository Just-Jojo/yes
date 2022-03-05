# Copyright (c) 2021 - Jojo#7791
# Licensed under MIT

import logging


log = logging.getLogger("pagify")
__all__ = ["pagify", "box"]


def box(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text}```"


def pagify(text: str, page_length: int = 300) -> list:
    in_text = text
    ret = []
    while len(in_text) > page_length:
        p_len = page_length
        delim = in_text.rfind("\n", 0, page_length)
        delim = delim if delim != -1 else p_len
        to_send = in_text[:delim]
        if len(to_send.strip()) > 0:
            ret.append(to_send)
        in_text = in_text[delim:]
    if len(in_text.strip()) > 0:
        ret.append(in_text)
    return ret
