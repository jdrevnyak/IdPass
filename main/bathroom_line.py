"""The bathroom line for one classroom reader.

A place in line is not an outing. The line is stored on this reader and kept
only while the classroom id stays the same.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta

TURN_SECONDS = 120

LINE_FILENAME = "bathroom_line.json"
LINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), LINE_FILENAME)


def ordinal(n):
    """1st, 2nd, 3rd, 4th."""
    n = int(n)
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _norm_uid(uid):
    if not uid:
        return ""
    s = str(uid).strip().upper().replace(":", "").replace("-", "").replace(" ", "")
    if s.lower().startswith("0x"):
        s = s[2:].upper()
    return s


def _norm_id(student_id):
    if student_id is None:
        return ""
    return str(student_id).strip()


def _same(a, b):
    a_id, b_id = _norm_id(a.get("student_id")), _norm_id(b.get("student_id"))
    if a_id and b_id and a_id == b_id:
        return True
    a_uid, b_uid = _norm_uid(a.get("nfc_uid")), _norm_uid(b.get("nfc_uid"))
    return bool(a_uid and b_uid and a_uid == b_uid)


class BathroomLine:
    def __init__(self, classroom_id="", students=None, turn_elapsed_s=0.0, turn_running_since=None):
        self.classroom_id = (classroom_id or "").strip()
        self.students = list(students or [])
        self.turn_elapsed_s = float(turn_elapsed_s or 0)
        self.turn_running_since = turn_running_since

    def count(self):
        return len(self.students)

    def _index(self, entry):
        for i, student in enumerate(self.students):
            if _same(student, entry):
                return i
        return None

    def contains(self, entry):
        return self._index(entry) is not None

    def is_front(self, entry):
        return bool(self.students) and _same(self.students[0], entry)

    def place(self, entry):
        idx = self._index(entry)
        if idx is None:
            return None
        return idx + 1

    def join(self, entry):
        """Append the student, or return the place they already have."""
        existing = self.place(entry)
        if existing:
            return existing
        self.students.append({
            "student_id": _norm_id(entry.get("student_id")),
            "nfc_uid": _norm_uid(entry.get("nfc_uid")),
            "name": (entry.get("name") or "Student").strip() or "Student",
        })
        return len(self.students)

    def remove_index(self, index):
        if index < 0 or index >= len(self.students):
            return None
        removed = self.students.pop(index)
        if index == 0:
            self._reset_turn()
        return removed

    def remove_matching(self, entry):
        idx = self._index(entry)
        if idx is None:
            return False
        self.remove_index(idx)
        return True

    def clear(self):
        self.students = []
        self._reset_turn()

    def adopt(self, classroom_id):
        """Keep the line only when the reader stays on the same classroom."""
        classroom_id = (classroom_id or "").strip()
        if classroom_id == self.classroom_id:
            return False
        self.classroom_id = classroom_id
        self.clear()
        self.save()
        return True

    def _reset_turn(self):
        self.turn_elapsed_s = 0.0
        self.turn_running_since = None

    def tick(self, now, bathroom_free, restricted):
        """Advance the front student's turn.

        Returns (expired_students, changed). The clock runs only while the
        bathroom is free and the restricted window is not in effect. One
        missed turn removes only the student at the front.
        """
        changed = False
        expired = []
        if not self.students or not bathroom_free:
            if self.turn_elapsed_s or self.turn_running_since is not None:
                self._reset_turn()
                changed = True
            return expired, changed

        if restricted:
            if self.turn_running_since is not None:
                self.turn_elapsed_s += (now - self.turn_running_since).total_seconds()
                self.turn_running_since = None
                changed = True
            return expired, changed

        if self.turn_running_since is None:
            self.turn_running_since = now
            changed = True
        elapsed = self.turn_elapsed_s + (now - self.turn_running_since).total_seconds()
        if elapsed >= TURN_SECONDS:
            expired.append(self.students.pop(0))
            self._reset_turn()
            if self.students:
                self.turn_running_since = now
            changed = True
        return expired, changed

    def remaining_seconds(self, now, bathroom_free):
        """Seconds left in the front student's turn, or None when nobody is up."""
        if not self.students or not bathroom_free:
            return None
        elapsed = self.turn_elapsed_s
        if self.turn_running_since is not None:
            elapsed += (now - self.turn_running_since).total_seconds()
        return max(0.0, TURN_SECONDS - elapsed)

    def front_name(self):
        if not self.students:
            return ""
        return self.students[0].get("name") or "Student"

    def to_dict(self):
        since = self.turn_running_since.isoformat() if self.turn_running_since else None
        return {
            "classroom_id": self.classroom_id,
            "students": self.students,
            "turn_elapsed_s": self.turn_elapsed_s,
            "turn_running_since": since,
        }

    def save(self, path=None):
        path = path or LINE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)

    @classmethod
    def load(cls, classroom_id, path=None):
        path = path or LINE_PATH
        classroom_id = (classroom_id or "").strip()
        if not os.path.exists(path):
            return cls(classroom_id)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return cls(classroom_id)
        if not isinstance(data, dict) or (data.get("classroom_id") or "").strip() != classroom_id:
            return cls(classroom_id)
        since = data.get("turn_running_since")
        parsed = datetime.fromisoformat(since) if since else None
        return cls(
            classroom_id,
            students=data.get("students") or [],
            turn_elapsed_s=data.get("turn_elapsed_s") or 0,
            turn_running_since=parsed,
        )


def _check():
    global LINE_PATH
    original_path = LINE_PATH
    LINE_PATH = os.path.join(tempfile.mkdtemp(), LINE_FILENAME)
    try:
        _check_line()
    finally:
        try:
            os.remove(LINE_PATH)
        except OSError:
            pass
        LINE_PATH = original_path


def _check_line():
    now = datetime(2026, 10, 22, 9, 0, 0)
    line = BathroomLine("201")
    alex = {"student_id": "1", "nfc_uid": "AA", "name": "Alex"}
    blake = {"student_id": "2", "nfc_uid": "BB", "name": "Blake"}
    assert line.join(alex) == 1
    assert line.join(alex) == 1
    assert line.join(blake) == 2
    assert ordinal(line.place(blake)) == "2nd"

    expired, changed = line.tick(now, bathroom_free=False, restricted=False)
    assert expired == [] and changed is False
    assert line.remaining_seconds(now, False) is None

    expired, changed = line.tick(now, bathroom_free=True, restricted=False)
    assert changed and line.remaining_seconds(now, True) == TURN_SECONDS

    later = now + timedelta(seconds=30)
    line.tick(later, bathroom_free=True, restricted=True)
    assert line.remaining_seconds(later, True) == TURN_SECONDS - 30
    held = later + timedelta(minutes=10)
    line.tick(held, bathroom_free=True, restricted=True)
    assert abs(line.remaining_seconds(held, True) - (TURN_SECONDS - 30)) < 0.01

    resume = held + timedelta(seconds=1)
    line.tick(resume, bathroom_free=True, restricted=False)
    almost = resume + timedelta(seconds=90)
    expired, _ = line.tick(almost, bathroom_free=True, restricted=False)
    assert [s["name"] for s in expired] == ["Alex"]
    assert line.front_name() == "Blake"
    assert line.remaining_seconds(almost, True) == TURN_SECONDS

    line.remove_index(0)
    assert line.count() == 0
    line.join(alex)
    line.tick(almost, True, False)
    assert line.adopt("202") is True
    assert line.count() == 0 and line.classroom_id == "202"
    assert line.adopt("202") is False
    print("bathroom line checks passed")


if __name__ == "__main__":
    _check()
