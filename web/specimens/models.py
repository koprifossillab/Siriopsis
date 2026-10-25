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
    """한 대상을 같은 자리에서 한 가지 축만 바꿔 찍은, 서로 맞아 있는 컷들.

    지금 종류는 빛 더미 하나다. 다음 유형(초점 더미·맞춘 카탈로그 묶음)도 이 테이블에 `kind` 로 들어온다.
    """
    class Kind(models.TextChoices):
        LIGHT = "light", "빛 더미"

    class Preparation(models.TextChoices):
        NONE = "none", "무처리"
        WHITE_COATED = "white_coated", "흰 코팅"

    class View(models.TextChoices):
        WHOLE = "whole", "전체"
        ZOOM = "zoom", "확대"

    slab = models.ForeignKey(Slab, on_delete=models.CASCADE, related_name="stacks")
    specimen = models.ForeignKey(Specimen, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="stacks")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    preparation = models.CharField(max_length=16, choices=Preparation.choices)
    view = models.CharField(max_length=8, choices=View.choices)
    # 확대 표시 Z 를 뗀 원래 이름(`SP-2016-52A`, `SP-2011-0577a`) — 같은 대상의 더미끼리 같다
    label = models.CharField(max_length=64)
    # SOURCE_ROOT 기준 상대경로. 원본은 읽기만 한다
    source_dir = models.CharField(max_length=500, unique=True)
    lp_file = models.CharField(max_length=200)
    ptm_file = models.CharField(max_length=200, blank=True)
    n_frames = models.PositiveSmallIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    camera = models.CharField(max_length=64, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["slab__slab_no", "label", "preparation", "view"]

    def __str__(self):
        return f"{self.label} · {self.get_preparation_display()} · {self.get_view_display()}"


class Frame(models.Model):
    """더미의 컷 한 장. 빛 더미에서는 빛 방향 단위 벡터(`.lp` 의 x y z)를 갖는다."""
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name="frames")
    seq = models.PositiveSmallIntegerField()        # .lp 의 줄 순서(0부터)
    path = models.CharField(max_length=500)          # SOURCE_ROOT 기준 상대경로
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    light_x = models.FloatField(null=True, blank=True)
    light_y = models.FloatField(null=True, blank=True)
    light_z = models.FloatField(null=True, blank=True)

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
