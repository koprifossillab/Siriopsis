"""묶음 고치기와, 반입이 사람의 손을 덮지 않는 것 (wetherilli 008)."""
import shutil
import tempfile
from pathlib import Path

from django.test import Client
from django.urls import reverse

from core.tests.base import SafeTestCase
from specimens import regroup
from specimens.lightseries import scan
from specimens.models import EditLog, Frame, Stack

from .test_lightseries import MAIN, shots


def nos(stack):
    return list(stack.frames.filter(hidden=False).order_by("seq").values_list("shot_no", flat=True))


class RegroupTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        shots(self.root, MAIN, "SP-2016-47K", [1, 2, 3, 4, 5])
        shots(self.root, MAIN, "SP-2016-47A", [1, 2])
        scan(root=self.root)
        self.k = Stack.objects.get(label="SP-2016-47K")
        self.a = Stack.objects.get(label="SP-2016-47A")

    def tearDown(self):
        self._tmp.cleanup()

    def fid(self, stack, no):
        return stack.frames.get(shot_no=no).id

    def test_split_survives_rescan(self):
        pre = regroup.split_preview(self.k, [self.fid(self.k, 2)])
        self.assertEqual([[r["no"] for r in p] for p in pre["pieces"]], [[1, 2], [3, 4, 5]])
        self.assertEqual(nos(self.k), [1, 2, 3, 4, 5])            # 미리보기는 테이블을 건드리지 않는다
        (new_id,) = regroup.apply_split(self.k, [self.fid(self.k, 2)])
        self.k.refresh_from_db()
        new = Stack.objects.get(id=new_id)
        self.assertEqual((nos(self.k), self.k.n_frames, nos(new), new.piece), ([1, 2], 2, [3, 4, 5], 1))
        self.assertIsNotNone(self.k.edited_at)
        self.assertEqual(new.specimen, self.k.specimen)

        st = scan(root=self.root)
        self.assertEqual(st.kept, 1)
        self.assertEqual((nos(Stack.objects.get(id=self.k.id)), nos(Stack.objects.get(id=new_id))),
                         ([1, 2], [3, 4, 5]))
        self.assertEqual(Stack.objects.filter(label="SP-2016-47K").count(), 2)

    def test_split_refuses_bad_cuts(self):
        last = self.fid(self.k, 5)
        for after in ([], [last], [self.fid(self.a, 1)], ["x"]):
            self.assertFalse(regroup.split_preview(self.k, after)["ok"], after)
            with self.assertRaises(ValueError):
                regroup.apply_split(self.k, after)
        self.assertEqual(Stack.objects.count(), 2)

    def test_merge_hides_other_and_rescan_does_not_bring_it_back(self):
        regroup.apply_merge(self.k, self.a.id)
        self.k.refresh_from_db()
        self.a.refresh_from_db()
        self.assertEqual((nos(self.k), self.k.n_frames), ([1, 2, 3, 4, 5, 1, 2], 7))
        self.assertEqual((self.a.hidden, self.a.frames.count()), (True, 0))
        scan(root=self.root)
        self.assertEqual(Stack.objects.filter(hidden=False).count(), 1)
        self.assertEqual(Stack.objects.get(id=self.k.id).n_frames, 7)
        self.assertEqual(Frame.objects.count(), 7)                 # 합쳐 온 컷이 도로 생기지 않는다

    def test_merge_and_delete_take_copies_along(self):
        shots(self.root, f"{MAIN}/알씨원본", "SP-2016-47A", [1, 2])
        scan(root=self.root)
        copy = Stack.objects.get(copy_of=self.a)
        self.assertEqual(len(regroup.merge_preview(self.k, self.a.id)["copies"]), 1)
        regroup.apply_merge(self.k, self.a.id)
        copy.refresh_from_db()
        self.assertTrue(copy.hidden)
        scan(root=self.root)
        self.assertTrue(Stack.objects.get(id=copy.id).hidden)

    def test_merge_refuses_other_slab_and_self(self):
        shots(self.root, MAIN, "SP-2016-48A", [1, 2])
        scan(root=self.root)
        other = Stack.objects.get(label="SP-2016-48A")
        for target in (other.id, self.k.id, 999999, "x"):
            self.assertFalse(regroup.merge_preview(self.k, target)["ok"], target)

    def test_delete_is_hiding_and_restorable(self):
        regroup.apply_delete(self.a)
        scan(root=self.root)
        self.a.refresh_from_db()
        self.assertTrue(self.a.hidden)
        self.assertEqual(Stack.objects.filter(label="SP-2016-47A").count(), 1)
        regroup.restore(self.a)
        self.assertFalse(Stack.objects.get(id=self.a.id).hidden)

    def test_hidden_frame_stays_hidden_and_returns_to_its_place(self):
        f3 = self.k.frames.get(shot_no=3)
        regroup.hide_frame(f3)
        self.k.refresh_from_db()
        self.assertEqual((nos(self.k), self.k.n_frames), ([1, 2, 4, 5], 4))
        scan(root=self.root)
        self.assertEqual(nos(Stack.objects.get(id=self.k.id)), [1, 2, 4, 5])
        self.assertEqual(Stack.objects.filter(label="SP-2016-47K").count(), 1)   # 숨긴 컷이 「새 컷」이 되지 않는다
        regroup.show_frame(Frame.objects.get(id=f3.id))
        self.assertEqual(nos(self.k), [1, 2, 3, 4, 5])

    def test_cannot_hide_last_frame(self):
        regroup.hide_frame(self.a.frames.get(shot_no=1))
        with self.assertRaises(ValueError):
            regroup.hide_frame(self.a.frames.get(shot_no=2))

    def test_new_shot_after_edit_goes_to_leftover_piece(self):
        regroup.apply_split(self.k, [self.fid(self.k, 2)])
        shots(self.root, MAIN, "SP-2016-47K", [6])
        st = scan(root=self.root)
        left = Stack.objects.get(label="SP-2016-47K", edited_at__isnull=True)
        self.assertTrue(left.is_leftover)
        self.assertEqual((nos(left), left.piece, st.created), ([6], 2, 1))
        scan(root=self.root)                                          # 몇 번을 돌려도 같다
        self.assertEqual(Stack.objects.filter(label="SP-2016-47K").count(), 3)
        # 사람이 합치면 조각은 숨고, 반입은 그 컷을 다시 「새 컷」으로 내지 않는다
        regroup.apply_merge(self.k, left.id)
        scan(root=self.root)
        self.assertEqual(Stack.objects.filter(label="SP-2016-47K", hidden=False).count(), 2)
        self.assertEqual(nos(Stack.objects.get(id=self.k.id)), [1, 2, 6])

    def test_edited_stack_kept_when_folder_vanishes(self):
        regroup.hide_frame(self.k.frames.get(shot_no=5))
        for f in (self.root / MAIN).glob("SP-2016-47K-*"):
            f.unlink()
        st = scan(root=self.root)
        self.assertEqual((st.orphaned, st.removed), (1, 0))
        self.assertTrue(Stack.objects.filter(id=self.k.id).exists())

    def test_ptm_is_not_editable(self):
        ptm = Stack.objects.create(slab=self.k.slab, kind=Stack.Kind.PTM, preparation="none", view="whole",
                                   label="SP-2016-47", source_dir="PTM/x")
        for pre in (regroup.delete_preview(ptm), regroup.merge_preview(self.k, ptm.id)):
            self.assertFalse(pre["ok"])

    def test_log(self):
        regroup.apply_split(self.k, [self.fid(self.k, 2)])
        log = EditLog.objects.get()
        self.assertEqual((log.action, log.stack_id, len(log.detail["pieces"])), ("split", self.k.id, 2))


class RegroupViewTest(SafeTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        shots(root, MAIN, "SP-2016-47K", [1, 2, 3])
        shots(root, MAIN, "SP-2016-47A", [1, 2])
        scan(root=root)
        self.k = Stack.objects.get(label="SP-2016-47K")
        self.a = Stack.objects.get(label="SP-2016-47A")
        self.c = Client()

    def tearDown(self):
        self._tmp.cleanup()

    def test_two_steps(self):
        url = reverse("delete_stack", args=[self.a.id])
        self.assertEqual(self.c.get(url).status_code, 405)
        r = self.c.post(url)
        self.assertContains(r, "지운다")
        self.assertFalse(Stack.objects.get(id=self.a.id).hidden)     # 미리보기만
        r = self.c.post(url, {"confirm": "1"})
        self.assertRedirects(r, reverse("slab", args=[self.a.slab.slab_no]))
        self.assertTrue(Stack.objects.get(id=self.a.id).hidden)
        r = self.c.get(reverse("slab", args=[self.a.slab.slab_no]))
        self.assertContains(r, "지운 묶음 1")
        self.assertContains(r, reverse("restore_stack", args=[self.a.id]))

    def test_split_and_merge(self):
        after = self.k.frames.get(shot_no=1).id
        r = self.c.post(reverse("split_stack", args=[self.k.id]), {"after": after})
        self.assertContains(r, "→ 2 묶음")
        self.c.post(reverse("split_stack", args=[self.k.id]), {"after": after, "confirm": "1"})
        self.assertEqual(Stack.objects.get(id=self.k.id).n_frames, 1)
        r = self.c.post(reverse("merge_stack", args=[self.k.id]), {"with": self.a.id, "confirm": "1"})
        self.assertRedirects(r, reverse("stack", args=[self.k.id]))
        self.assertEqual(Stack.objects.get(id=self.k.id).n_frames, 3)

    def test_bad_request_changes_nothing(self):
        r = self.c.post(reverse("split_stack", args=[self.k.id]), {"confirm": "1"})
        self.assertEqual(r.status_code, 400)
        self.assertIsNone(Stack.objects.get(id=self.k.id).edited_at)

    def test_hide_frame_and_page(self):
        f = self.k.frames.get(shot_no=2)
        self.c.post(reverse("frame_visibility", args=[f.id]), {"hide": "1"})
        r = self.c.get(reverse("stack", args=[self.k.id]))
        self.assertContains(r, "숨긴 컷")
        self.assertEqual([x["no"] for x in r.context["payload"]], [1, 3])
        self.c.post(reverse("frame_visibility", args=[f.id]), {"hide": "0"})
        self.assertEqual(nos(self.k), [1, 2, 3])

    def test_csrf(self):
        r = Client(enforce_csrf_checks=True).post(reverse("delete_stack", args=[self.a.id]), {"confirm": "1"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Stack.objects.get(id=self.a.id).hidden)
