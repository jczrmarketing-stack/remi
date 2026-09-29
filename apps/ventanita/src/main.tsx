import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { LimiteDeError } from "./componentes/LimiteDeError";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <LimiteDeError>
      <App />
    </LimiteDeError>
  </StrictMode>,
);
