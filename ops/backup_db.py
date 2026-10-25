#!/usr/bin/env python3
"""DB 사본을 뜬다 — 시간별·손으로·배포 전, 그리고 하루 한 번 NAS 로 (wetherilli 008).

DiaRUGA `ops/backup_db.py`(v0.37.1)에서 왔다. 깃발 모듈(`db_sentinel`)과 NAS 동기화(`sync_backup_nas.py`)는
이 파일 하나로 줄였다 — Siriopsis 는 DB 가 작고(수십 MB) 원천이 하나다.

    python ops/backup_db.py --keep 24                  # 시간별 (cron :50)
    python ops/backup_db.py --note before-merge        # 손으로 — manual/ 에, 순환이 안 건드린다
    python ops/backup_db.py --offsite /nfs/temp-share/Siriopsis/backup --keep-offsite 60   # 하루 한 번

**왜 이제부터인가** — 묶음 고치기(008)가 들어오기 전에는 DB 를 반입 세 명령으로 다시 만들 수 있었다. 이제 사람이
가르고 합치고 지운 것(`Stack.edited_at`·`hidden`·`piece`, `Frame.hidden`, `EditLog`)은 반입으로 되살아나지 않는다.

**`cp Siriopsis.db` 로는 안 된다**(WAL — 최근 쓰기가 `-wal` 에 있다). SQLite backup API 로 뜬다.
**운영 DB 를 호스트에서 열지 않는다**(.guides/web/data-safety.md §14) — 운영에서는 compose 의 `backup` 문으로 컨테이너 안에서 돈다.
Django 를 부르지 않는다 — 다른 것이 다 망가졌을 때 쓰는 안전망이라 혼자 돌아야 한다.

## 실패했을 때 (data-safety §2) — 셋을 다 한다
1. **정리를 건너뛴다** — 깨진 사본을 채택하고 순환을 돌리면 지난 정상 사본이 밀려난다
2. **증거를 남긴다** — `.corrupt`(정리 glob `Siriopsis_*.db` 에 안 걸린다)
3. **깃발을 세운다** — 사본 자리에 `BACKUP_FAIL.<갈래>`. `/healthz` 가 읽어 `degraded` 를 낸다. 성공하면 그 갈래의 깃발만 내린다

사본은 `journal_mode=DELETE`(파일 하나, §5). 세션·비밀이 DB 에 없어(로그인이 없다) NAS 로 그대로 보낸다(§7) —
로그인이 생기면 오프사이트 사본에서 `django_session` 을 비운다.
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 자동(시간별) 사본의 이름. `?` 가 자리를 박아 `--note` 꼬리말이 붙은 것은 안 걸린다
AUTO_GLOB = "Siriopsis_????????_??????.db"
TABLES = ("specimens_slab", "specimens_stack", "specimens_frame", "specimens_editlog")


def _env(key, default):
    """환경변수 → 저장소의 `.env` → 기본값 (settings.py 와 같은 이름을 본다 — 갈리면 /healthz 가 딴 자리를 본다)."""
    if key in os.environ:
        return os.environ[key]
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#") and k.strip() == key:
                return v.strip()
    except OSError:
        pass
    return default


DB = Path(_env("SIRIOPSIS_DB", str(ROOT / "Siriopsis.db")))
OUT = Path(_env("SIRIOPSIS_BACKUP_DIR", "") or ROOT / "backup")


def flag_path(out, source):
    return out / f"BACKUP_FAIL.{source}"


def raise_flag(out, source, reason):
    out.mkdir(parents=True, exist_ok=True)
    flag_path(out, source).write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {reason}\n", encoding="utf-8")
    print(f"  깃발을 세웠다: {flag_path(out, source)} (/healthz 가 degraded 를 낸다)", file=sys.stderr)
    print("  정리는 건너뛴다 — 지난 사본을 남긴다", file=sys.stderr)
    return 1


def clear_flag(out, source):
    p = flag_path(out, source)
    if p.exists():
        p.unlink()
        print("  지난 실패 깃발을 내렸다")


def _sweep(path):
    for ext in ("-wal", "-shm", "-journal"):
        stray = path.with_name(path.name + ext)
        if stray.exists():
            stray.unlink()


def check(path):
    """사본을 읽기 전용으로 열어 검사한다. → (integrity, {테이블: 행 수})"""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {}
        for t in TABLES:
            try:
                counts[t] = con.execute(f"select count(*) from {t}").fetchone()[0]
            except sqlite3.Error:
                counts[t] = None
        return ok, counts
    finally:
        con.close()


def snapshot(db, out, note="", keep=0, flat=False):
    """살아 있는 DB → 검증된 사본 하나. 실패하면 1."""
    if not db.exists():
        return raise_flag(out, "backup", f"DB 가 없다: {db}")
    dest = out / "manual" if (note and not flat) else out
    dest.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    final = dest / f"Siriopsis_{stamp}{'_' + note if note else ''}.db"
    # 제 이름은 검증을 통과한 뒤에 준다 — 반쯤 쓴 파일이 정리 glob 에 걸려 살아남지 않게
    part = final.with_name(final.name + ".part")
    try:
        src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        dst = sqlite3.connect(part)
        try:
            with dst:
                src.backup(dst)
            dst.execute("PRAGMA journal_mode=DELETE")
        finally:
            src.close()
            dst.close()
        _sweep(part)
        ok, counts = check(part)
    except (sqlite3.Error, OSError) as e:
        print(f"사본을 뜨지 못했다: {e}", file=sys.stderr)
        if part.exists():
            _sweep(part)
            part.replace(final.with_name(final.name + ".corrupt"))
        return raise_flag(out, "backup", f"사본을 뜨지 못했다 — {e}")
    if ok != "ok":
        evidence = final.with_name(final.name + ".corrupt")
        part.replace(evidence)
        return raise_flag(out, "backup", f"integrity_check={ok} ({evidence.name})")
    part.replace(final)
    print(f"{final}  {final.stat().st_size / 1e6:.1f} MB  integrity=ok")
    print("  " + " · ".join(f"{t.removeprefix('specimens_')} {n}" for t, n in counts.items() if n is not None))
    if note and not flat:
        print("  (손으로 뜬 사본 — manual/ 에 둔다. 순환이 안 건드리고 NAS 로 안 간다. 일이 끝나면 사람이 지운다)")
    clear_flag(out, "backup")
    if keep:
        # 자동만 굴린다. --flat(배포 전 사본 자리처럼 그 종류 전용 디렉터리)이면 꼬리말 붙은 것도
        old = sorted(dest.glob("Siriopsis_*.db" if flat else AUTO_GLOB))[:-keep]
        for p in old:
            p.unlink()
        if old:
            print(f"  오래된 사본 {len(old)}개 지웠다 (최근 {keep}개 유지)")
    return 0


def offsite(out, target, keep=0):
    """가장 새 **검증된 시간별 사본**을 NAS 로 (data-safety §4 — 살아 있는 DB 를 옮기지 않는다). 하루에 하나."""
    snaps = sorted(out.glob(AUTO_GLOB))
    if not snaps:
        return raise_flag(out, "offsite", f"보낼 시간별 사본이 없다: {out}")
    newest = snaps[-1]
    age_h = (time.time() - newest.stat().st_mtime) / 3600
    if age_h > 2:
        # 시간별이 멈췄거나 깃발이 막고 있다 — 묵은 것을 오늘 것처럼 보내지 않는다
        return raise_flag(out, "offsite", f"가장 새 시간별 사본이 {age_h:.1f} 시간 전이다: {newest.name}")
    day = time.strftime("%Y%m%d")
    final = target / f"Siriopsis_{day}.db"
    n = 2
    while final.exists():                     # 같은 날 두 번이면 덮지 않고 잇는다 (§16)
        final = target / f"Siriopsis_{day}.{n}.db"
        n += 1
    part = final.with_name(final.name + ".part")
    try:
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(newest, part)
        ok, _ = check(part)
    except (sqlite3.Error, OSError) as e:
        if part.exists():
            part.replace(final.with_name(final.name + ".corrupt"))
        return raise_flag(out, "offsite", f"NAS 로 못 보냈다 — {e}")
    if ok != "ok":
        part.replace(final.with_name(final.name + ".corrupt"))
        return raise_flag(out, "offsite", f"NAS 사본 integrity_check={ok}")
    part.replace(final)
    # /healthz 가 이 나이를 본다 — 웹 컨테이너는 NAS 의 백업 자리를 붙이지 않는다
    (out / "offsite_status.json").write_text(json.dumps(
        {"at": time.time(), "path": str(final), "from": newest.name}, ensure_ascii=False), encoding="utf-8")
    print(f"{newest.name} → {final}  integrity=ok")
    clear_flag(out, "offsite")
    if keep:
        old = sorted(target.glob("Siriopsis_????????*.db"))[:-keep]
        for p in old:
            p.unlink()
        if old:
            print(f"  NAS 의 오래된 사본 {len(old)}개 지웠다 (최근 {keep}개 유지)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--out", default=str(OUT), help="사본 자리 (SIRIOPSIS_BACKUP_DIR)")
    ap.add_argument("--note", default="", help="파일 이름 꼬리말 — manual/ 로 간다")
    # 보관 개수 × 주기 ≥ 오프사이트 간격 (data-safety §6): 시간별 24 × 1시간 = 하루 한 번 NAS
    ap.add_argument("--keep", type=int, default=0, help="자동 사본을 최근 N 개만 (0 이면 안 지운다)")
    ap.add_argument("--flat", action="store_true", help="꼬리말이 있어도 manual/ 로 가르지 않는다 (배포 전 사본)")
    ap.add_argument("--offsite", help="사본을 뜨는 대신, 가장 새 시간별 사본을 이 자리(NAS)로 보낸다")
    ap.add_argument("--keep-offsite", type=int, default=0, help="NAS 에 최근 N 개만 (0 이면 안 지운다)")
    a = ap.parse_args(argv)
    os.umask(0o027)
    out = Path(a.out)
    if a.offsite:
        return offsite(out, Path(a.offsite), keep=a.keep_offsite)
    return snapshot(Path(a.db), out, note=a.note, keep=a.keep, flat=a.flat)


if __name__ == "__main__":
    sys.exit(main())
