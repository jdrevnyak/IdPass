// Firebase Configuration
const firebaseConfig = {
  apiKey: "AIzaSyCz9BJgYJlYCkRCo2aaNRXgkiOwHqFhP4o",
  authDomain: "hallpass-c7e9b.firebaseapp.com",
  projectId: "hallpass-c7e9b",
  storageBucket: "hallpass-c7e9b.firebasestorage.app",
  messagingSenderId: "185225886951",
  appId: "1:185225886951:web:4521679f931070309bf642"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Initialize Firebase services
const auth = firebase.auth();
const db = firebase.firestore();

// Check authentication state
function checkAuthState(callback) {
  auth.onAuthStateChanged((user) => {
    if (callback) {
      callback(user);
    }
  });
}

// Require authentication - redirect to login if not authenticated
function requireAuth(redirectUrl = '/index.html') {
  checkAuthState((user) => {
    if (!user && window.location.pathname !== redirectUrl) {
      window.location.href = redirectUrl;
    }
  });
}

// Sign out function
async function signOut() {
  try {
    await auth.signOut();
    window.location.href = '/index.html';
  } catch (error) {
    console.error('Error signing out:', error);
  }
}

