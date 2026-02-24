export const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? "http://127.0.0.1:5000"
  : "https://your-backend-url.onrender.com"; // User will need to replace this after deployment
