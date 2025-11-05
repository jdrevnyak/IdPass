// Authentication Logic

// Check if user is already logged in
checkAuthState((user) => {
  if (user && window.location.pathname === '/index.html') {
    // Redirect to dashboard if already logged in
    window.location.href = '/dashboard.html';
  }
});

// Handle login form submission
const loginForm = document.getElementById('loginForm');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('errorMessage');
    
    try {
      // Sign in with email and password
      await auth.signInWithEmailAndPassword(email, password);
      
      // Redirect to dashboard on successful login
      window.location.href = '/dashboard.html';
      
    } catch (error) {
      console.error('Login error:', error);
      
      // Display user-friendly error message
      let message = 'Failed to sign in. Please check your credentials.';
      if (error.code === 'auth/user-not-found') {
        message = 'No account found with this email.';
      } else if (error.code === 'auth/wrong-password') {
        message = 'Incorrect password.';
      } else if (error.code === 'auth/invalid-email') {
        message = 'Invalid email format.';
      } else if (error.code === 'auth/user-disabled') {
        message = 'This account has been disabled.';
      }
      
      errorMessage.textContent = message;
      errorMessage.style.display = 'block';
    }
  });
}

