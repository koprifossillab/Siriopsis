"""EPMA 세션·맵·채널을 phyloserver 에서 읽어 테이블을 맞춘다 (사용자 2026-10-26, wetherilli 018).

구조는 사용자와 paleoadmin 이 정했다(NAS `temp/20261026_proposal_epma_attach.md`):
- **EPMA 를 가져오는 쪽은 phyloserver 그대로**(`import_epma_sessions`·`convert_epma_binary`). 여기는 읽기만 한다
- 메타는 `GET /siriuspasset/epma.json` — `{"generated_at", "file_root", "sessions", "maps", "channels"}`, 세 모델의 모든 칸 값 그대로.
  그것이 서기 전·시험에는 내보낸 `models/SpEpma*.json`(dumpdata 꼴, `--dump`)을 읽는다 — 칸이 같다
- 파일은 `/data3/epma`(`settings.EPMA_ROOT`)를 그 자리에서 `:ro` 로. NAS 의 두 벌(내보내기·미러)은 백업이라 읽지 않는다

반입은 통째로 맞춘다 — 받은 것에 없는 행은 지운다(사람이 여기서 고치는 칸이 없다). 받은 것이 비었으면 지우지 않고 멈춘다.
"""
import json
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import EpmaChannel, EpmaMap, EpmaSession, Slab, Specimen


@dataclass
class EpmaStats:
    sessions: int = 0
    maps: int = 0
    channels: int = 0
    linked: int = 0             # 테이블의 슬랩에 붙은 세션
    no_slab: list = field(default_factory=list)     # phyloserver 슬랩 id 가 테이블에 없다
    removed: int = 0
    errors: list = field(default_factory=list)

    def __str__(self):
        return (f"세션 {self.sessions} (슬랩에 붙음 {self.linked} · 슬랩 없음 {len(self.no_slab)}) · 맵 {self.maps} · 채널 {self.channels}"
                f" · 지움 {self.removed}")


def _rows(items):
    """dumpdata 꼴(`{"pk", "fields"}`)과 epma.json 꼴(칸이 바로, `id`) 둘 다 → [{칸…, "id"}]."""
    out = []
    for it in items or []:
        if "fields" in it:
            out.append({**it["fields"], "id": it["pk"]})
        else:
            out.append(dict(it))
    return out


def _ref(row, name):
    """외래 열쇠 칸 — dumpdata 는 `slab`, JSON 은 `slab_id` 일 수 있다."""
    v = row.get(f"{name}_id", row.get(name))
    return v if isinstance(v, int) else None


def _date(v):
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _s(v):
    return "" if v is None else str(v)


def parse(doc):
    """{"sessions": [...], "maps": [...], "channels": [...]} → 같은 꼴의 정돈한 행들."""
    return {k: _rows(doc.get(k)) for k in ("sessions", "maps", "channels")}


def load_dump(folder):
    """내보낸 폴더(`phyloserver-export/<날>/` 또는 그 `models/`)의 `SpEpma*.json`."""
    folder = Path(folder)
    if (folder / "models").is_dir():
        folder = folder / "models"
    doc = {}
    for key, name in (("sessions", "SpEpmaSession"), ("maps", "SpEpmaMap"), ("channels", "SpEpmaChannel")):
        doc[key] = json.loads((folder / f"{name}.json").read_text(encoding="utf-8"))
    return parse(doc)


def fetch(base=None, timeout=120):
    """`GET <base>epma.json`. 없으면(404)·연결이 안 되면 OSError, 꼴이 틀리면 ValueError."""
    base = (base or settings.CATALOG_URL).rstrip("/") + "/"
    with urllib.request.urlopen(base + "epma.json", timeout=timeout) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    if not isinstance(doc, dict) or "sessions" not in doc:
        raise ValueError("epma.json 의 꼴이 아니다")
    return parse(doc)


@transaction.atomic
def sync(data):
    st = EpmaStats()
    if not data["sessions"]:
        st.errors.append("세션이 하나도 없다 — 지우지 않고 멈춘다")
        return st
    slabs = dict(Slab.objects.filter(catalog_id__isnull=False).values_list("catalog_id", "id"))
    specs = dict(Specimen.objects.filter(catalog_id__isnull=False).values_list("catalog_id", "id"))

    sess = {}
    for r in data["sessions"]:
        slab_cid, spec_cid = _ref(r, "slab"), _ref(r, "specimen")
        obj, _ = EpmaSession.objects.update_or_create(catalog_id=r["id"], defaults={
            "slab_id": slabs.get(slab_cid), "specimen_id": specs.get(spec_cid),
            "slab_catalog_id": slab_cid, "specimen_catalog_id": spec_cid,
            "session_number": r.get("session_number") or 0, "label": _s(r.get("session_label")),
            "source_directory": _s(r.get("source_directory")), "data_format": _s(r.get("data_format")),
            "instrument": _s(r.get("instrument")), "accel_voltage": _num(r.get("accel_voltage")),
            "probe_current": _num(r.get("probe_current")), "acquisition_date": _date(r.get("acquisition_date")),
            "analyst": _s(r.get("analyst")), "description": _s(r.get("description")),
            "representative_catalog_id": _ref(r, "representative_channel"),
        })
        sess[r["id"]] = obj.id
        st.sessions += 1
        if obj.slab_id:
            st.linked += 1
        else:
            st.no_slab.append(f"{obj.label} (phyloserver 슬랩 {slab_cid})")

    maps = {}
    for r in data["maps"]:
        sid = sess.get(_ref(r, "session"))
        if sid is None:
            st.errors.append(f"맵 {r['id']}: 세션 {_ref(r, 'session')} 이 없다")
            continue
        obj, _ = EpmaMap.objects.update_or_create(catalog_id=r["id"], defaults={
            "session_id": sid, "map_number": r.get("map_number") or 0, "label": _s(r.get("map_label")),
            "source_directory": _s(r.get("source_directory")), "region_description": _s(r.get("region_description")),
            "pixel_width": r.get("pixel_width"), "pixel_height": r.get("pixel_height"),
        })
        maps[r["id"]] = obj.id
        st.maps += 1

    keep_ch = set()
    for r in data["channels"]:
        mid = maps.get(_ref(r, "epma_map"))
        if mid is None:
            st.errors.append(f"채널 {r['id']}: 맵 {_ref(r, 'epma_map')} 이 없다")
            continue
        EpmaChannel.objects.update_or_create(catalog_id=r["id"], defaults={
            "map_id": mid, "element": _s(r.get("element")), "line": _s(r.get("line")), "method": _s(r.get("method")),
            "channel_number": r.get("channel_number") or 0,
            "image_file": _s(r.get("image_file")), "data_file": _s(r.get("data_file")),
            "binary_data_file": _s(r.get("binary_data_file")), "condition_file": _s(r.get("condition_file")),
            "original_path": _s(r.get("original_path")), "is_special": bool(r.get("is_special")),
        })
        keep_ch.add(r["id"])
        st.channels += 1

    # 받은 것에 없는 행 — phyloserver 에서 지운 것
    for model, keep in ((EpmaChannel, keep_ch), (EpmaMap, set(maps)), (EpmaSession, set(sess))):
        gone = model.objects.exclude(catalog_id__in=keep)
        st.removed += gone.count()
        gone.delete()
    return st


def relink():
    """슬랩·표본을 phyloserver id 로 다시 잇는다 — `import_catalog` 가 새 슬랩을 넣은 뒤에 부른다."""
    slabs = dict(Slab.objects.filter(catalog_id__isnull=False).values_list("catalog_id", "id"))
    specs = dict(Specimen.objects.filter(catalog_id__isnull=False).values_list("catalog_id", "id"))
    n = 0
    for s in EpmaSession.objects.all():
        new = (slabs.get(s.slab_catalog_id), specs.get(s.specimen_catalog_id))
        if (s.slab_id, s.specimen_id) != new:
            s.slab_id, s.specimen_id = new
            s.save(update_fields=["slab", "specimen"])
            n += 1
    return n


def file_path(rel):
    """`EPMA_ROOT` 아래의 파일 — 뿌리 밖을 가리키거나 없으면 None."""
    if not rel:
        return None
    root = Path(settings.EPMA_ROOT).resolve()
    p = (root / rel).resolve()
    if root not in p.parents or not p.is_file():
        return None
    return p


def thumb_path(rel):
    """이미지 옆 `.thumbnails/<같은 이름>` — phyloserver 가 만들어 둔 것. 없으면 이미지 그대로."""
    p = file_path(rel)
    if p is None:
        return None
    t = p.parent / ".thumbnails" / p.name
    return t if t.is_file() else p


def representative(sessions):
    """세션마다 대표 채널 — phyloserver 의 대표가 있으면 그것, 없으면 첫 맵의 첫 이미지 채널(특수 채널 SEI·COMPO 먼저)."""
    ids = [s.id for s in sessions]
    chans = list(EpmaChannel.objects.filter(map__session_id__in=ids).exclude(image_file="")
                 .select_related("map").order_by("map__session_id", "map__map_number", "-is_special", "element"))
    by_cid = {c.catalog_id: c for c in chans}
    first = {}
    for c in chans:
        first.setdefault(c.map.session_id, c)
    for s in sessions:
        s.rep = by_cid.get(s.representative_catalog_id) or first.get(s.id)
