import json

from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def frame_url(frame_id, width=None):
    """컷 주소. 폭을 주면 축소본(thumbs.WIDTHS 로 올린다), 안 주면 원본."""
    if not frame_id:
        return ""
    url = reverse("frame_image", args=[frame_id])
    return f"{url}?w={int(width)}" if width else url


@register.filter
def json_dumps(value):
    """<script type="application/json"> 안에 넣을 JSON (DiaRUGA `viewer_extras.json_dumps`).
    `</script>` 로 태그가 일찍 닫히지 않게 `<` 를 바꾼다."""
    text = json.dumps(value, ensure_ascii=False)
    return mark_safe(text.replace("<", "\\u003c").replace("\u2028", "\\u2028"))
