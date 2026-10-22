"""A card deleted in Firebase must not still count as a student.

Teacher enrollment asks whether the tapped card belongs to a student.
The reader keeps a local copy for offline use. Deleting the student online
used to leave that copy in place, and the lookup treated the copy as a match.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "main"))

from online_first_db import OnlineFirstDatabase
from student_db import StudentDatabase


CARD = "AABBCCDD"
OTHER = "11223344"


class FakeStudents:
    def __init__(self, docs):
        self._docs = docs

    def get(self):
        return self._docs


class FakeFirestore:
    def __init__(self, docs):
        self._docs = docs

    def collection(self, name):
        if name != "students":
            raise AssertionError(name)
        return FakeStudents(self._docs)


class FakeDoc:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    def to_dict(self):
        return self._data


class FakeFirebase:
    def __init__(self, found=None, error=None, docs=None):
        self.found = found
        self.error = error
        self.db = FakeFirestore(docs or [])

    def get_student_by_uid(self, nfc_uid):
        if self.error:
            raise self.error
        return self.found


def reader_db(path, firebase, mode="online"):
    db = OnlineFirstDatabase.__new__(OnlineFirstDatabase)
    db.mode = mode
    db.firebase_db = firebase
    db.local_db = StudentDatabase(path)
    return db


class DeletedStudentCardTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "students.db")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_online_miss_ignores_stale_local_student(self):
        firebase = FakeFirebase(found=None)
        db = reader_db(self.db_path, firebase)
        db.local_db.add_student(CARD, "999999", "Test Student")

        self.assertIsNone(db.get_student_by_uid(CARD))

    def test_online_lookup_failure_still_uses_local_copy(self):
        firebase = FakeFirebase(error=RuntimeError("firestore down"))
        db = reader_db(self.db_path, firebase)
        db.local_db.add_student(CARD, "999999", "Test Student")

        self.assertEqual(db.get_student_by_uid(CARD), ("999999", "Test Student"))

    def test_offline_still_uses_local_copy(self):
        firebase = FakeFirebase(found=None)
        db = reader_db(self.db_path, firebase, mode="offline")
        db.local_db.add_student(CARD, "999999", "Test Student")

        self.assertEqual(db.get_student_by_uid(CARD), ("999999", "Test Student"))

    def test_sync_drops_students_removed_online(self):
        firebase = FakeFirebase(
            docs=[
                FakeDoc(
                    OTHER,
                    {"nfc_uid": OTHER, "student_id": "111111", "name": "Kept Student"},
                )
            ]
        )
        db = reader_db(self.db_path, firebase)
        db.local_db.add_student(CARD, "999999", "Test Student")
        db.local_db.add_student(OTHER, "111111", "Kept Student")

        db._sync_students_to_local()

        self.assertIsNone(db.local_db.get_student_by_uid(CARD))
        self.assertEqual(
            db.local_db.get_student_by_uid(OTHER), ("111111", "Kept Student")
        )


if __name__ == "__main__":
    unittest.main()
