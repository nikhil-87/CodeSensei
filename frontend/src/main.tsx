import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { initTheme } from "./store/themeStore";
import "./index.css";

// Apply the persisted theme before the first paint to avoid a flash.
initTheme();

const container = document.getElementById("root");
if (!container) throw new Error("Root container missing in index.html");

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
