# Firebase Setup Guide

This guide will help you set up Firebase for your Hall Pass System, including both the Python desktop application and the web dashboard.

## Prerequisites

- Firebase account (free tier is sufficient)
- Python 3.7+ installed
- Node.js and npm installed (for Firebase CLI)

## Part 1: Firebase Project Setup

### 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Enter project name (e.g., "hallpass-c7e9b" - or use the existing one)
4. Disable Google Analytics (optional)
5. Click "Create project"

### 2. Enable Firestore Database

1. In your Firebase project, go to "Firestore Database" in the left sidebar
2. Click "Create database"
3. Choose "Start in production mode" (we'll set up security rules later)
4. Select a Cloud Firestore location closest to you
5. Click "Enable"

### 3. Enable Authentication

1. Go to "Authentication" in the left sidebar
2. Click "Get started"
3. Click on "Email/Password" under Sign-in providers
4. Enable "Email/Password"
5. Click "Save"

### 4. Create Your First Admin User

1. In Authentication, go to the "Users" tab
2. Click "Add user"
3. Enter an email and password (you'll use this to log into the web dashboard)
4. Click "Add user"

## Part 2: Python Desktop App Configuration

### 1. Generate Service Account Key

1. In Firebase Console, click the gear icon ⚙️ next to "Project Overview"
2. Select "Project settings"
3. Go to the "Service accounts" tab
4. Click "Generate new private key"
5. Click "Generate key" - a JSON file will be downloaded

### 2. Configure the Desktop App

1. Rename the downloaded JSON file to `firebase-service-account.json`
2. Move it to your IdPass project root directory:
   ```
   /Users/jackdrevnyak/IdPass/firebase-service-account.json
   ```
3. **IMPORTANT**: Add this to your `.gitignore` file:
   ```
   firebase-service-account.json
   ```

### 3. Install Python Dependencies

```bash
cd /Users/jackdrevnyak/IdPass
pip install -r requirements.txt
```

### 4. Test the Connection

Run the Firebase database test:
```bash
python firebase_db.py
```

You should see: `✅ Successfully connected to Firebase!`

## Part 3: Web Dashboard Deployment

### 1. Install Firebase CLI

```bash
npm install -g firebase-tools
```

### 2. Login to Firebase

```bash
firebase login
```

This will open a browser window for you to authenticate with Google.

### 3. Initialize Firebase in Your Project

```bash
cd /Users/jackdrevnyak/IdPass/webapp
firebase init
```

When prompted:
- Select "Firestore" and "Hosting" (use spacebar to select, enter to continue)
- Use an existing project: select your project (e.g., "hallpass-c7e9b")
- Firestore Rules: Use the existing file `firestore.rules`
- Firestore Indexes: Use the existing file `firestore.indexes.json`
- Public directory: Enter `public`
- Configure as single-page app: Yes
- Set up automatic builds: No
- Overwrite files: No (keep existing files)

### 4. Deploy Security Rules and Indexes

```bash
firebase deploy --only firestore:rules,firestore:indexes
```

### 5. Deploy the Web App

```bash
firebase deploy --only hosting
```

After deployment, you'll receive a hosting URL like:
`https://hallpass-c7e9b.web.app`

### 6. Access the Web Dashboard

1. Open the hosting URL in your browser
2. Login with the email/password you created in Authentication setup
3. You should now see the dashboard!

## Part 4: Firebase Configuration (Web App)

The web app configuration is already set in `/Users/jackdrevnyak/IdPass/webapp/public/js/firebase-config.js`:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyCz9BJgYJlYCkRCo2aaNRXgkiOwHqFhP4o",
  authDomain: "hallpass-c7e9b.firebaseapp.com",
  projectId: "hallpass-c7e9b",
  storageBucket: "hallpass-c7e9b.firebasestorage.app",
  messagingSenderId: "185225886951",
  appId: "1:185225886951:web:4521679f931070309bf642"
};
```

If you created a new Firebase project, update these values:
1. Go to Firebase Console
2. Click the gear icon ⚙️ > Project settings
3. Scroll down to "Your apps"
4. Click the Web app icon `</>`
5. Copy the config values
6. Update `firebase-config.js` with your values

## Part 5: Security Rules

The Firestore security rules are configured in `/Users/jackdrevnyak/IdPass/webapp/firestore.rules`. They require authentication for all operations:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

To update security rules:
```bash
cd /Users/jackdrevnyak/IdPass/webapp
firebase deploy --only firestore:rules
```

## Part 6: Running the Desktop App

1. Make sure your Raspberry Pi or desktop has the `firebase-service-account.json` file
2. Run the app:
   ```bash
   python nfc_reader_gui.py
   ```

The app will:
- Connect to Firebase Firestore
- Sync students from Firestore to local SQLite
- Push all attendance/break/nurse data to Firestore
- Run bidirectional sync every 10 minutes

## Troubleshooting

### Desktop App Issues

**Error: "Could not connect to Firebase"**
- Check that `firebase-service-account.json` exists in the project root
- Verify the file has valid JSON
- Check internet connection

**Error: "Permission denied"**
- Verify Firestore rules allow read/write for authenticated requests
- Check service account has proper permissions

### Web App Issues

**Cannot login**
- Verify you created a user in Firebase Authentication
- Check that Authentication is enabled for Email/Password
- Open browser console for error messages

**Data not loading**
- Check Firestore security rules are deployed
- Verify authentication is working (check if user email shows in nav)
- Open browser console for error messages
- Check Firebase Console > Firestore to see if data exists

**Deployment fails**
- Run `firebase login` again
- Check you're in the correct directory (`/webapp`)
- Verify `firebase.json` exists

## Data Migration / Importing Students from CSV

### Option 1: Using the Web Dashboard (Recommended)

1. Log into the web dashboard
2. Go to the "Students" page
3. Click "📥 Import CSV" button
4. Select your CSV file
5. Click "Import"
6. Review the import results

### Option 2: Using Python Script

If you have a CSV file with your students (like your Google Sheets export):

```bash
cd /Users/jackdrevnyak/IdPass
python import_students_csv.py path/to/your/students.csv
```

For example, with your file:
```bash
python import_students_csv.py ~/Downloads/"Student Attendance Tracking - Students.csv"
```

### CSV Format

Your CSV should have these columns (in order):
1. **NFC_UID** - Optional, can be empty
2. **Student_ID** - Required (6-digit school ID)
3. **Name** - Required (student full name)
4. **Created_At** - Optional, can be empty (will use current time)

Example CSV:
```csv
NFC_UID,Student_ID,Name,Created_At
805B78C9,123456,Jack Drevnyak,2025-06-16 00:19:42
,225192,Kenneth Duenas,
,225325,Melanie Rosales,
```

The script will:
- Skip the header row automatically
- Import all students to Firebase Firestore
- Show success/failure counts
- Display any errors encountered

## Adding More Admin Users

To add more users who can access the web dashboard:

1. Go to Firebase Console > Authentication > Users
2. Click "Add user"
3. Enter email and password
4. Share the web dashboard URL and credentials

## Backup and Export

To backup your Firestore data:

1. Use the web dashboard's export features (CSV exports)
2. Use Firebase Console > Firestore > Export/Import
3. Use `gcloud` CLI for automated backups

## Cost Considerations

Firebase free tier (Spark plan) includes:
- 50,000 reads/day
- 20,000 writes/day
- 20,000 deletes/day
- 1GB storage

This should be sufficient for a typical classroom. Monitor usage in Firebase Console.

## Support

For issues or questions:
- Check Firebase documentation: https://firebase.google.com/docs
- Firebase Console: https://console.firebase.google.com/
- Check application logs for error messages

## Next Steps

1. ✅ Complete Firebase setup
2. ✅ Test desktop app connection
3. ✅ Deploy web dashboard
4. ✅ Add admin users
5. ✅ Import or add students
6. 🎉 Start tracking attendance!

