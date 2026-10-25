import tempfile
from pathlib import Path

from core.tests.base import SafeTestCase
from specimens.lightstacks import scan
from specimens.models import Frame, Slab, Stack

from .fixtures import VECTORS, make_stack

PTM = "SP-2016 샘플별/6D 외/PTM"
COATED = "SP-2016 샘플별/6D 외/PTM white coated"


class ScanLightStacksTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_reads_stacks_and_is_idempotent(self):
        make_stack(self.root, f"{PTM}/SP-2016-52", "SP-2016-52A")
        make_stack(self.root, f"{COATED}/SP-2016-52Z", "SP-2016-52Z", first=20000)
        st = scan(root=self.root)
        self.assertEqual((st.found, st.created, st.errors), (2, 2, []))

        plain = Stack.objects.get(source_dir=f"{PTM}/SP-2016-52")
        self.assertEqual(plain.slab.slab_no, "SP-2016-0052")
        self.assertEqual(plain.specimen.specimen_no, "SP-2016-0052-A")
        self.assertEqual((plain.preparation, plain.view, plain.label), ("none", "whole", "SP-2016-52A"))
        self.assertEqual((plain.n_frames, plain.width, plain.height, plain.camera), (3, 40, 30, "Canon EOS 60D"))

        coated = Stack.objects.get(source_dir=f"{COATED}/SP-2016-52Z")
        self.assertEqual((coated.preparation, coated.view), ("white_coated", "zoom"))
        self.assertIsNone(coated.specimen)          # 글자가 없으면 표본을 짐작하지 않는다
        self.assertEqual(coated.slab_id, plain.slab_id)

        f = plain.frames.get(seq=1)
        self.assertEqual(f.path, f"{PTM}/SP-2016-52/IMG_10096.JPG")   # .lp 는 .jpg, 파일은 .JPG
        self.assertAlmostEqual(f.light_z, VECTORS[1][2])
        self.assertTrue(0 < f.elevation < 90)

        st = scan(root=self.root)
        self.assertEqual((st.created, st.updated, st.unchanged), (0, 0, 2))
        self.assertEqual(Frame.objects.count(), 6)
        self.assertEqual(Slab.objects.count(), 1)

    def test_changed_lp_replaces_frames(self):
        make_stack(self.root, f"{PTM}/SP-2016-601", "SP-2016-601")
        scan(root=self.root)
        make_stack(self.root, f"{PTM}/SP-2016-601", "SP-2016-601",
                   vectors=[(0.0, 0.0, 1.0)] + VECTORS[1:])
        st = scan(root=self.root)
        self.assertEqual(st.updated, 1)
        self.assertEqual(Frame.objects.get(seq=0).light_z, 1.0)
        self.assertEqual(Frame.objects.count(), 3)

    def test_missing_frame_skips_whole_stack(self):
        make_stack(self.root, f"{PTM}/SP-2016-494", "SP-2016-494", skip={2})
        st = scan(root=self.root)
        self.assertEqual(st.created, 0)
        self.assertEqual(len(st.errors), 1)
        self.assertIn("없다", st.errors[0])
        self.assertFalse(Stack.objects.exists())

    def test_nas_metadata_dirs_are_skipped(self):
        make_stack(self.root, f"{PTM}/@eaDir/SP-2016-52", "SP-2016-52A")
        self.assertEqual(scan(root=self.root).found, 0)

    def test_specimen_attached_later_is_kept(self):
        # 사람이 붙인 표본은 다시 훑어도 떨어지지 않는다
        make_stack(self.root, f"{PTM}/SP-2016-494", "SP-2016-494")
        scan(root=self.root)
        s = Stack.objects.get()
        sp = s.slab.specimens.create(letter="A")
        s.specimen = sp
        s.save()
        scan(root=self.root)
        s.refresh_from_db()
        self.assertEqual(s.specimen_id, sp.id)
