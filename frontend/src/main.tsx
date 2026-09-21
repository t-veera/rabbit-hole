import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { applyReadingFont, applyReadingFontSize, getStoredReadingFont, getStoredReadingFontSize } from "./readingPrefs";
import "./styles/global.css";
import { applyTheme, getStoredTheme } from "./theme";

applyTheme(getStoredTheme());
applyReadingFont(getStoredReadingFont());
applyReadingFontSize(getStoredReadingFontSize());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
