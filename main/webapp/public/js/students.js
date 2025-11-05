// Students Management Logic

// Require authentication
requireAuth();

// Display user email
checkAuthState((user) => {
  if (user) {
    document.getElementById('userEmail').textContent = user.email;
  }
});

let allStudents = [];

// Load all students
function loadStudents() {
  db.collection('students')
    .onSnapshot((snapshot) => {
      allStudents = [];
      snapshot.forEach((doc) => {
        const data = doc.data();
        allStudents.push({
          docId: doc.id,
          ...data
        });
      });

      // Sort by name
      allStudents.sort((a, b) => a.name.localeCompare(b.name));
      
      displayStudents(allStudents);
    }, (error) => {
      console.error('Error loading students:', error);
      const tbody = document.getElementById('studentsTableBody');
      if (error.code === 'permission-denied') {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Permission denied. Please make sure you are logged in and Firestore rules are deployed.</td></tr>';
      } else {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">Error loading students: ${error.message}</td></tr>`;
      }
    });
}

// Display students in table
function displayStudents(students) {
  const tbody = document.getElementById('studentsTableBody');
  
  if (students.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state"><h3>No students found</h3><p>Click "📥 Import CSV" or "+ Add Student" to get started</p></td></tr>';
    return;
  }

  tbody.innerHTML = students.map(student => `
    <tr>
      <td>${student.student_id}</td>
      <td>${student.name}</td>
      <td>${student.nfc_uid || '<em>Not assigned</em>'}</td>
      <td>${student.created_at ? new Date(student.created_at).toLocaleDateString() : '-'}</td>
      <td class="action-buttons">
        <button class="btn btn-small btn-secondary" onclick='editStudent(${JSON.stringify(student)})'>Edit</button>
        <button class="btn btn-small btn-danger" onclick="deleteStudent('${student.docId}', '${student.name}')">Delete</button>
      </td>
    </tr>
  `).join('');
}

// Filter students - make globally accessible
window.filterStudents = function() {
  const searchTerm = document.getElementById('searchInput').value.toLowerCase();
  const filtered = allStudents.filter(student => 
    student.name.toLowerCase().includes(searchTerm) ||
    student.student_id.toString().includes(searchTerm) ||
    (student.nfc_uid && student.nfc_uid.toLowerCase().includes(searchTerm))
  );
  displayStudents(filtered);
}

// Show add student modal - make globally accessible
window.showAddStudentModal = function() {
  document.getElementById('modalTitle').textContent = 'Add Student';
  document.getElementById('studentForm').reset();
  document.getElementById('studentDocId').value = '';
  document.getElementById('formError').style.display = 'none';
  document.getElementById('studentModal').classList.add('active');
}

// Edit student - make globally accessible
window.editStudent = function(student) {
  document.getElementById('modalTitle').textContent = 'Edit Student';
  document.getElementById('studentDocId').value = student.docId;
  document.getElementById('studentId').value = student.student_id;
  document.getElementById('studentName').value = student.name;
  document.getElementById('nfcUid').value = student.nfc_uid || '';
  document.getElementById('formError').style.display = 'none';
  document.getElementById('studentModal').classList.add('active');
}

// Close modal - make globally accessible
window.closeStudentModal = function() {
  document.getElementById('studentModal').classList.remove('active');
}

// Handle form submission
document.getElementById('studentForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const docId = document.getElementById('studentDocId').value;
  const studentId = document.getElementById('studentId').value.trim();
  const studentName = document.getElementById('studentName').value.trim();
  const nfcUid = document.getElementById('nfcUid').value.trim();
  const formError = document.getElementById('formError');

  try {
    // Prepare student data
    const studentData = {
      student_id: studentId,
      name: studentName,
      nfc_uid: nfcUid
    };

    if (docId) {
      // Update existing student
      await db.collection('students').doc(docId).update(studentData);
    } else {
      // Add new student
      // Use NFC UID as document ID if available, otherwise use student ID
      const documentId = nfcUid || studentId;
      studentData.created_at = new Date().toISOString();
      await db.collection('students').doc(documentId).set(studentData);
    }

    closeStudentModal();
    
  } catch (error) {
    console.error('Error saving student:', error);
    formError.textContent = 'Failed to save student: ' + error.message;
    formError.style.display = 'block';
  }
});

// Delete student - make globally accessible
window.deleteStudent = async function(docId, name) {
  if (!confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`)) {
    return;
  }

  try {
    await db.collection('students').doc(docId).delete();
  } catch (error) {
    console.error('Error deleting student:', error);
    alert('Failed to delete student: ' + error.message);
  }
}

// Load students only after authentication is confirmed
checkAuthState((user) => {
  if (user) {
    loadStudents();
  }
});

// Close modal when clicking outside
document.getElementById('studentModal').addEventListener('click', (e) => {
  if (e.target === document.getElementById('studentModal')) {
    closeStudentModal();
  }
});

// Import CSV functions - make them globally accessible
window.showImportModal = function() {
  document.getElementById('csvFile').value = '';
  document.getElementById('importProgress').style.display = 'none';
  document.getElementById('importResults').style.display = 'none';
  document.getElementById('importModal').classList.add('active');
}

window.closeImportModal = function() {
  document.getElementById('importModal').classList.remove('active');
}

window.importCSV = async function() {
  const fileInput = document.getElementById('csvFile');
  const file = fileInput.files[0];
  
  if (!file) {
    alert('Please select a CSV file');
    return;
  }

  const progressDiv = document.getElementById('importProgress');
  const resultsDiv = document.getElementById('importResults');
  
  progressDiv.style.display = 'block';
  resultsDiv.style.display = 'none';

  try {
    const text = await file.text();
    const lines = text.split('\n');
    
    let success = 0;
    let failed = 0;
    const errors = [];

    // Check if first line is a header
    const firstLine = lines[0].toLowerCase();
    const hasHeader = firstLine.includes('student_id') || firstLine.includes('name');
    const startIndex = hasHeader ? 1 : 0;

    // Process each line
    for (let i = startIndex; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue; // Skip empty lines

      const parts = line.split(',');
      if (parts.length < 3) {
        failed++;
        errors.push(`Line ${i + 1}: Not enough columns`);
        continue;
      }

      try {
        const nfcUid = parts[0].trim();
        const studentId = parts[1].trim();
        const name = parts[2].trim();
        const createdAt = parts.length > 3 && parts[3].trim() ? parts[3].trim() : new Date().toISOString();

        if (!studentId || !name) {
          failed++;
          errors.push(`Line ${i + 1}: Missing student ID or name`);
          continue;
        }

        // Use NFC UID as document ID if available, otherwise use student_id
        const docId = nfcUid || studentId;

        const studentData = {
          nfc_uid: nfcUid,
          student_id: studentId,
          name: name,
          created_at: createdAt
        };

        await db.collection('students').doc(docId).set(studentData);
        success++;

      } catch (error) {
        failed++;
        errors.push(`Line ${i + 1}: ${error.message}`);
      }
    }

    // Show results
    progressDiv.style.display = 'none';
    resultsDiv.style.display = 'block';
    
    let resultHTML = `<div class="alert alert-success">
      <strong>Import Complete!</strong><br>
      Successfully imported: ${success} students<br>
      Failed: ${failed} students
    </div>`;

    if (errors.length > 0) {
      resultHTML += `<div class="alert alert-error" style="margin-top: 1rem; max-height: 200px; overflow-y: auto;">
        <strong>Errors:</strong><br>
        ${errors.slice(0, 10).join('<br>')}
        ${errors.length > 10 ? `<br>... and ${errors.length - 10} more errors` : ''}
      </div>`;
    }

    resultsDiv.innerHTML = resultHTML;

  } catch (error) {
    progressDiv.style.display = 'none';
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `<div class="alert alert-error">
      <strong>Import Failed:</strong> ${error.message}
    </div>`;
  }
}

// Close import modal when clicking outside
document.getElementById('importModal').addEventListener('click', (e) => {
  if (e.target === document.getElementById('importModal')) {
    closeImportModal();
  }
});

