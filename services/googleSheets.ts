import axios from "axios";

const GOOGLE_SHEET_ID = "1Kb-Vu3I1DIRUix-8swzzwJcqiEAkBGkW8JaDrD7r4bo";
const API_KEY = "AIzaSyCmk7MTOgYTN0eTikYsEwpt8myCaFo8-os";
const SHEET_NAME = "Sheet1";

export const fetchGoogleSheetsData = async () => {
  try {
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${GOOGLE_SHEET_ID}/values/${SHEET_NAME}?key=${API_KEY}`;
    const response = await axios.get(url);
    return response.data.values; 
  } catch (error: any) {
    console.error("Error fetching Google Sheets data:", error.response?.data || error.message);
    return null;
  }
};
