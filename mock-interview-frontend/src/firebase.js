// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import {getAuth} from "firebase/auth"
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyB5Jf39Jj7hNe2jXvhSp4vCJ3s_0mQjXfs",
  authDomain: "mockinterview-97bae.firebaseapp.com",
  projectId: "mockinterview-97bae",
  storageBucket: "mockinterview-97bae.firebasestorage.app",
  messagingSenderId: "157169077790",
  appId: "1:157169077790:web:b2c1d2e1e3e8202411a80f",
  measurementId: "G-D1TWL9PSHS"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
export const auth = getAuth(app);