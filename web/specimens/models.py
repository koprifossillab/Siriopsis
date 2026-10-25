"""슬랩 → 표본, 그리고 더미 → 컷 (P01 1단계, wetherilli 002).

DiaRUGA 의 Slide → Viewpoint(시야) → Frame(초점 면) 자리가 여기서는 Slab → Stack(더미) → Frame(컷)이다.
**더미는 슬랩에 반드시, 표본에는 확실할 때만 붙는다** — 빛 더미 폴더 이름에 표본 글자가 없는 것이 있고
(`SP-2016-494`), 사진 한 장에 표본이 여럿 들 수도 있다. 비어 있는 표본은 사람이 정한다.
"""
import math

from django.db import models


class Slab(models.Model):
    """암석 한 덩이. 이름은 phyloserver 꼴 `SP-2016-0052`."""
    slab_no = models.CharField(max_length=32, unique=True)
    year = models.PositiveSmallIntegerField()
    horizon = models.CharField(max_length=100, blank=True)
    # phyloserver siriuspasset 의 슬랩 id — 상세 화면으로 되돌아가는 링크. 목록에 없으면 null
    catalog_id = models.PositiveIntegerField(null=True, blank=True)
    catalog_synced_at = models.DateTimeField(null=True, blank=True)
    # phyloserver 목록에 있는 이 슬랩의 표본 글자(`A B C`) — 테이블에 없는 표본도. 글자 없는 더미를 A 에 붙일지 가린다(`bare.py`, wetherilli 012)
    catalog_letters = models.CharField(max_length=200, blank=True)
    # phyloserver 표본 상세 화면의 counterpart 를 읽은 때 (`import_catalog --details`, wetherilli 013). 읽은 슬랩은 엑셀의 짝을 안 쓴다
    counterpart_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["slab_no"]

    def __str__(self):
        return self.slab_no


class Specimen(models.Model):
    """슬랩 위의 화석 하나. 이름은 `SP-2016-0052-A`."""
    slab = models.ForeignKey(Slab, on_delete=models.CASCADE, related_name="specimens")
    letter = models.CharField(max_length=8)
    taxon_name = models.CharField(max_length=100, blank=True)
    phylum = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    catalog_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["slab__slab_no", "letter"]
        constraints = [models.UniqueConstraint(fields=["slab", "letter"], name="specimen_slab_letter")]

    @property
    def specimen_no(self):
        return f"{self.slab.slab_no}-{self.letter}"

    def __str__(self):
        return self.specimen_no


class Stack(models.Model):
    """한 대상을 같은 자리에서 한 가지 축만 바꿔 찍은 컷들.

    종류가 둘이다 (사용자 2026-10-25, wetherilli 003):
    - `ptm` — PTM 촬영. 돔 장비로 50 컷, 빛 방향 단위 벡터(`.lp`)와 `.ptm` 이 같이 있다. 삼각대라 픽셀이 맞다
    - `series` — 카탈로그 빛 묶음. `SP-2022-131-1 … -6` 처럼 표본 이름 뒤 번호가 빛을 달리해 찍은 컷이다.
      빛 방향 값은 없고, 구도가 조금씩 어긋날 수 있다(맞춤은 다음 단계)
    - `slab` — 슬랩 전경(`SP-2016-694(dorsal).JPG`). 표본이 아니라 슬랩 자체를 찍은 사진이라 표본에 안 붙는다(wetherilli 009)
    다음 유형(초점 더미 등)도 이 테이블에 `kind` 로 들어온다.
    """
    class Kind(models.TextChoices):
        PTM = "ptm", "PTM"
        SERIES = "series", "빛 묶음"
        SLAB = "slab", "슬랩 전경"

    class Preparation(models.TextChoices):
        NONE = "none", "무처리"
        WHITE_COATED = "white_coated", "흰 코팅"
        MG_COATED = "mg_coated", "마그네슘 코팅"

    class View(models.TextChoices):
        WHOLE = "whole", "전체"
        ZOOM = "zoom", "확대"

    slab = models.ForeignKey(Slab, on_delete=models.CASCADE, related_name="stacks")
    specimen = models.ForeignKey(Specimen, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="stacks")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    preparation = models.CharField(max_length=16, choices=Preparation.choices)
    view = models.CharField(max_length=8, choices=View.choices)
    # 원래 이름. PTM 은 확대 표시 Z 를 뗀 것(`SP-2016-52A`), 빛 묶음은 번호를 뗀 것(`SP-2022-131`)
    label = models.CharField(max_length=64)
    # SOURCE_ROOT 기준 상대경로. 원본은 읽기만 한다. 빛 묶음은 한 폴더에 여럿이 든다 — 열쇠는 (폴더, 종류, 이름)
    source_dir = models.CharField(max_length=500)
    # 같은 이름·처리의 묶음이 다른 폴더에도 있으면 하나를 정본으로 고르고(lightseries.py) 나머지는 사본으로 넣는다.
    # 사본은 정본을 가리킨다(정본은 null). other_copies 는 정본에만 — 사본의 수
    copy_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="copies")
    other_copies = models.PositiveSmallIntegerField(default=0)
    # 사람이 고친 묶음 (wetherilli 008, `regroup.py`). **반입은 손댄 묶음을 다시 만들지 않는다** — 값도 컷도 그대로 두고,
    # 손댄 뒤 폴더에 새로 생긴 컷만 같은 이름의 다른 조각으로 넣는다. 반입으로 다시 만들 수 없는 값이라 백업 대상이다
    edited_at = models.DateTimeField(null=True, blank=True)
    # 지운 묶음. 행을 지우면 다음 반입이 같은 폴더·이름에서 도로 만든다 — 그래서 숨긴다
    hidden = models.BooleanField(default=False)
    # 가르기로 생긴 조각 번호. 반입이 만든 묶음은 0, 가른 조각과 손댄 뒤 새로 찾은 컷은 1, 2, …
    piece = models.PositiveSmallIntegerField(default=0)
    lp_file = models.CharField(max_length=200, blank=True)
    ptm_file = models.CharField(max_length=200, blank=True)
    n_frames = models.PositiveSmallIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    camera = models.CharField(max_length=64, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["slab__slab_no", "label", "kind", "preparation", "view"]
        constraints = [models.UniqueConstraint(fields=["source_dir", "kind", "label", "piece"], name="stack_source")]

    def __str__(self):
        return f"{self.label} · {self.get_preparation_display()} · {self.get_view_display()}"

    @property
    def is_leftover(self):
        """손댄 묶음의 폴더에서 반입이 새로 찾은 컷 — 사람이 아직 안 본 조각."""
        return self.piece > 0 and self.edited_at is None


class Frame(models.Model):
    """더미의 컷 한 장. PTM 은 빛 방향 단위 벡터(`.lp` 의 x y z)를, 빛 묶음은 파일 이름의 컷 번호를 갖는다."""
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name="frames")
    seq = models.PositiveSmallIntegerField()        # 0부터. PTM 은 .lp 줄 순서, 빛 묶음은 컷 번호 순서
    shot_no = models.PositiveIntegerField(null=True, blank=True)   # 빛 묶음 파일 이름의 번호(`-6`)
    captured_at = models.DateTimeField(null=True, blank=True)
    path = models.CharField(max_length=500)          # SOURCE_ROOT 기준 상대경로
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    light_x = models.FloatField(null=True, blank=True)
    light_y = models.FloatField(null=True, blank=True)
    light_z = models.FloatField(null=True, blank=True)
    # 지운 컷 (wetherilli 008). 파일은 NAS 에 그대로 있다 — 행을 남겨야 반입이 「새 컷」으로 도로 넣지 않는다
    hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["stack", "seq"]
        constraints = [models.UniqueConstraint(fields=["stack", "seq"], name="frame_stack_seq")]

    @property
    def azimuth(self):
        """빛 방위각(도, 0~360) — x 축에서 y 축 쪽으로. 그림의 어느 쪽이 x·y 인지는 2단계에서 그림자로 맞춘다."""
        if self.light_x is None:
            return None
        return math.degrees(math.atan2(self.light_y, self.light_x)) % 360

    @property
    def elevation(self):
        """빛 고도(도, 0=옆, 90=바로 위)."""
        if self.light_z is None:
            return None
        return math.degrees(math.asin(max(-1.0, min(1.0, self.light_z))))


class EditLog(models.Model):
    """사람이 묶음을 고친 기록 (wetherilli 008). 무엇을 했고 어느 컷이 어디로 갔는지 — 되짚을 때 쓴다."""
    at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=16)        # split · merge · delete · restore · hide_frame · show_frame
    stack = models.ForeignKey(Stack, on_delete=models.SET_NULL, null=True, related_name="edit_logs")
    detail = models.JSONField(default=dict)

    class Meta:
        ordering = ["-at"]


class Star(models.Model):
    """연구에 쓰기 좋은 표본 — 엑셀 목록 remarks 의 별표(☆) (사용자 2026-10-25, wetherilli 013).

    **원천은 phyloserver remarks 의 ☆**(`Specimen.remarks`)다. 엑셀의 것은 phyloserver 목록에 없는 슬랩만 메운다(`workbook.starred`).
    이 테이블은 엑셀에서 읽은 것만이고 `import_workbooks` 가 통째로 다시 만든다. 사진이 없는 표본도 든다 — 그래서 이름을 글자로 둔다.
    """
    slab_no = models.CharField(max_length=32, db_index=True)
    letter = models.CharField(max_length=8)         # 엑셀의 글자 칸이 비면 A (012)
    stars = models.PositiveSmallIntegerField(default=1)   # ☆ 의 수 — 둘(☆☆)도 있다
    taxon_name = models.CharField(max_length=100, blank=True)   # 엑셀의 값 — 테이블에 표본이 없을 때 보인다
    horizon = models.CharField(max_length=100, blank=True)
    text = models.CharField(max_length=300, blank=True)         # ☆ 가 든 칸의 원문
    source = models.CharField(max_length=200)       # 엑셀 파일 이름
    row = models.PositiveIntegerField()

    class Meta:
        ordering = ["slab_no", "letter"]

    @property
    def specimen_no(self):
        return f"{self.slab_no}-{self.letter}"


class Counterpart(models.Model):
    """두 쪽으로 쪼갠 암석의 마주 보는 면 — 표본의 counterpart 칸에 적힌 짝 (사용자 2026-10-25, wetherilli 013).

    **원천은 phyloserver 표본 상세 화면의 Counterpart 칸**이다(엑셀에서 들어가 사람이 고쳐 간다) — `import_catalog --details` 가 슬랩마다 다시 만든다.
    엑셀(`import_workbooks`, 통째로 다시 만든다)의 것은 phyloserver 에서 읽지 못한 슬랩만 메운다(`workbook.pairs_for`).
    **적힌 그대로 한 방향**이다(`SP-2016-4` 행의 「Counterpart of SP-2016-5」). 화면은 양쪽에서 같은 짝을 보인다.
    글자는 적혀 있을 때만 — 적힌 행의 표본 글자(`letter`), 글에 적힌 글자(`other_letter`). 슬랩이 테이블에 없을 수 있어 이름을 글자로 둔다.
    """
    class Origin(models.TextChoices):
        PHYLOSERVER = "phyloserver", "phyloserver"
        EXCEL = "excel", "엑셀"

    origin = models.CharField(max_length=16, choices=Origin.choices, default=Origin.EXCEL)
    slab_no = models.CharField(max_length=32, db_index=True)
    letter = models.CharField(max_length=8, blank=True)
    other_slab_no = models.CharField(max_length=32, db_index=True)
    other_letter = models.CharField(max_length=8, blank=True)
    uncertain = models.BooleanField(default=False)  # 「?」·maybe·probable·CHECK 가 붙은 것
    text = models.CharField(max_length=300)         # 원문
    source = models.CharField(max_length=200)       # 엑셀 파일 이름, phyloserver 면 표본 번호
    row = models.PositiveIntegerField()             # 엑셀 행 번호, phyloserver 면 표본 상세 id

    class Meta:
        ordering = ["slab_no", "letter", "other_slab_no"]


class Scale(models.Model):
    """더미의 배율 — 빛 묶음 1 번 컷의 자에서 잰 mm/px (wetherilli 010, `pipeline/ruler_scale.py` → `import_scales`).

    **원본 화소 기준이고, 잰 컷과 크기가 같은 컷에만 맞다** — 맞춤 전에는 같은 묶음의 크기가 같은 컷을 같은 배율로 본다
    (사용자). 크기가 다른 컷(확대·딴 카메라)에는 배율이 없다. 잰 컷은 Frame 이 아니라 **경로와 크기로** 적는다 —
    반입은 컷이 바뀐 묶음의 Frame 행을 다시 만든다(`lightseries.save_series`).

    `status` 가 `ok` 일 때만 `mm_per_px` 가 있다. 믿기 어려운 값(`doubt`)·자를 못 찾은 것(`none`)은 비워 두고 까닭을 `note` 에.
    반입으로 다시 만들 수 있는 값이다 — 사람의 손(`edited_at`)으로 치지 않는다.
    """
    class Status(models.TextChoices):
        OK = "ok", "잼"
        DOUBT = "doubt", "믿기 어려움"
        NONE = "none", "자를 못 찾음"

    stack = models.OneToOneField(Stack, on_delete=models.CASCADE, related_name="scale")
    status = models.CharField(max_length=8, choices=Status.choices)
    mm_per_px = models.FloatField(null=True, blank=True)
    frame_path = models.CharField(max_length=500)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    ticks = models.PositiveSmallIntegerField(default=0)     # 맞춘 눈금 수
    note = models.CharField(max_length=300, blank=True)
    measured_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.stack_id} · {self.status} · {self.mm_per_px}"

    def fits(self, width, height):
        """이 크기의 컷에 이 배율을 쓸 수 있나."""
        return self.mm_per_px is not None and (width, height) == (self.width, self.height)


class Outline(models.Model):
    """표본 테두리 — 한 더미에 하나 (사용자 2026-10-25, wetherilli 011).

    **좌표는 그린 컷의 원본 화소다.** 그린 컷은 Frame 이 아니라 경로와 크기로 적는다(`Scale` 과 같은 까닭 — 반입이 Frame 행을
    다시 만든다). 크기가 같은 다른 컷에도 그대로 얹는다 — PTM 은 삼각대라 맞고, 빛 묶음은 맞춤 전이라 어긋날 수 있다(화면이 그렇게 적는다).
    크기가 다른 컷에는 얹지 않는다. 계측값은 **서버가 다시 잰다**(`shape.py`) — 브라우저가 보낸 값을 믿지 않는다.

    사람이 그린 것이라 반입으로 다시 만들 수 없다 — 그리면 더미에 `edited_at` 을 단다(반입이 덮지 않게, 008). 백업 대상이다.
    """
    stack = models.OneToOneField(Stack, on_delete=models.CASCADE, related_name="outline")
    frame_path = models.CharField(max_length=500)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    points = models.JSONField()                       # [[x, y], …] 원본 화소
    area_px = models.FloatField()
    perimeter_px = models.FloatField()
    major_px = models.FloatField(null=True, blank=True)
    minor_px = models.FloatField(null=True, blank=True)
    long_px = models.FloatField(null=True, blank=True)
    short_px = models.FloatField(null=True, blank=True)
    drawn_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.stack_id} · {len(self.points)} 점"

    def fits(self, width, height):
        return (width, height) == (self.width, self.height)
