from fixtures import PERSONAS, FORMATS, PROMPT_FOR


def test_personas_cover_design_doc():
    assert set(PERSONAS) == {
        "Sports Fan", "News Junkie", "Entertainment Binge Watcher",
        "Casual Viewer", "Cord Cutter",
    }


def test_formats_cover_campaign_needs():
    assert {f["name"] for f in FORMATS} == {"social_square", "vertical_story", "display_banner", "email_header"}
    assert all(f["size"] in {"1024x1024", "1024x1792", "1792x1024"} for f in FORMATS)


def test_prompt_for_embeds_persona_and_format():
    p = PROMPT_FOR("Sports Fan", FORMATS[0])
    assert "Sports Fan" in p
    assert "no text" in p.lower()
