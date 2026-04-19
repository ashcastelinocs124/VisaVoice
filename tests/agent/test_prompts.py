from visavoice.agent.prompts import SYSTEM_PROMPT, CONFIRMATION_TEMPLATES


def test_system_prompt_requires_readback_before_verify():
    assert "read back" in SYSTEM_PROMPT.lower()
    assert "verify_identity" in SYSTEM_PROMPT


def test_system_prompt_rejects_instruction_overrides():
    assert "ignore" in SYSTEM_PROMPT.lower() or "override" in SYSTEM_PROMPT.lower()
    assert "system prompt" in SYSTEM_PROMPT.lower() or "instructions" in SYSTEM_PROMPT.lower()


def test_system_prompt_names_the_four_tools():
    for t in ("lookup_faq", "verify_identity", "book_appointment", "escalate_to_human"):
        assert t in SYSTEM_PROMPT


def test_confirmation_template_for_uin_is_digit_by_digit():
    tmpl = CONFIRMATION_TEMPLATES["uin_dob"]
    assert "{uin_digits}" in tmpl
    assert "{dob}" in tmpl
