import json

import pytest

from qqr import registers
from qqr.data.markdown import json2md
from qqr.data.text import get_cjk_chars, is_cjk, to_bool, truncate_text


def test_prompt_registry():
    assert {"qwen3", "qwen3.5"} <= set(registers.prompt.keys)


def test_qwen3_parses_think_and_tool_calls():
    parser = registers.prompt["qwen3"]()
    text = (
        "<think>need weather</think>Checking."
        '<tool_call>{"name": "get_weather", "arguments": {"city": "杭州"}}</tool_call>'
        '<tool_call>{"name": "noop", "arguments": "raw"}</tool_call><|im_end|>'
    )
    msg = parser.parse_assistant_content(text)
    assert msg["reasoning_content"] == "need weather"
    assert msg["content"] == "Checking."
    assert [c["function"]["name"] for c in msg["tool_calls"]] == ["get_weather", "noop"]
    assert json.loads(msg["tool_calls"][0]["function"]["arguments"]) == {"city": "杭州"}
    assert msg["tool_calls"][1]["function"]["arguments"] == "raw"


def test_qwen3_skips_malformed_tool_call_json():
    parser = registers.prompt["qwen3"]()
    msg = parser.parse_assistant_content("<tool_call>{not json}</tool_call>ok")
    assert msg["tool_calls"] == []
    assert msg["content"] == "ok"


def test_qwen3_adds_missing_think_open_tag():
    parser = registers.prompt["qwen3"]()
    msg = parser.parse_assistant_content("plan first</think>answer")
    assert msg["reasoning_content"] == "plan first"
    assert msg["content"] == "answer"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "k": {"type": "integer"},
                    "score": {"type": "number"},
                    "exact": {"type": "boolean"},
                    "filters": {"type": "object"},
                },
            },
        },
    }
]


def test_qwen35_xml_tool_call_type_conversion():
    parser = registers.prompt["qwen3.5"]()
    text = (
        "<think>r</think>Let me search.\n<tool_call>\n<function=search>\n"
        "<parameter=q>\nwest lake\n</parameter>\n<parameter=k>\n5\n</parameter>\n"
        "<parameter=score>\n0.5\n</parameter>\n<parameter=exact>\nTrue\n</parameter>\n"
        '<parameter=filters>\n{"city": "hz"}\n</parameter>\n</function>\n</tool_call>'
    )
    msg = parser.parse_assistant_content(text, tools=TOOLS)
    assert msg["content"] == "Let me search."
    args = json.loads(msg["tool_calls"][0]["function"]["arguments"])
    assert args == {"q": "west lake", "k": 5, "score": 0.5, "exact": True, "filters": {"city": "hz"}}


def test_qwen35_infinite_number_does_not_drop_tool_calls():
    """Regression: float('inf') -> int() raised OverflowError, which the outer
    handler swallowed, silently discarding every tool call in the message."""
    parser = registers.prompt["qwen3.5"]()
    text = "<tool_call><function=search><parameter=score>inf</parameter></function></tool_call>"
    msg = parser.parse_assistant_content(text, tools=TOOLS)
    assert len(msg["tool_calls"]) == 1
    assert json.loads(msg["tool_calls"][0]["function"]["arguments"]) == {"score": "inf"}


@pytest.mark.parametrize("value,expected", [("true", True), ("YES", True), ("1", True), ("no", False), (0, False), (1, True)])
def test_to_bool(value, expected):
    assert to_bool(value) is expected


def test_truncate_text_keeps_head_and_tail():
    text = " ".join(f"w{i}" for i in range(2000))
    out = truncate_text(text, max_len=200)
    assert len(out) < len(text)
    assert out.startswith("w0 ") and out.endswith("w1999")
    assert "省略" in out
    assert truncate_text("short", 100) == "short"


def test_cjk_helpers():
    assert is_cjk("hello 世界")
    assert not is_cjk("hello")
    assert get_cjk_chars("a西b湖") == "西湖"


def test_json2md_list_values_use_their_own_index():
    """Regression: duplicate list values were all labelled with the index of
    their first occurrence (``list.index``)."""
    md = json2md({"tags": ["a", "a", "b"]})
    assert "0: a" in md and "1: a" in md and "2: b" in md


def test_json2md_nested():
    md = json2md({"city": "Hangzhou", "days": [{"poi": "West Lake"}]})
    assert "city: Hangzhou" in md
    assert "## Days" in md and "poi: West Lake" in md
