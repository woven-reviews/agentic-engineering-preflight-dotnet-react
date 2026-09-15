import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

type Status = "checking" | "ok" | "error";

export function App() {
  const [status, setStatus] = useState<Status>("checking");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/preflight/db-check`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        setStatus("ok");
        setDetail(`database: ${data.database}`);
      })
      .catch((error) => {
        setStatus("error");
        setDetail(String(error));
      });
  }, []);

  const color = status === "ok" ? "#16a34a" : status === "error" ? "#dc2626" : "#666666";

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "3rem", maxWidth: 640 }}>
      <h1>Environment Preflight</h1>
      <p>
        If you can read this and see a green check below, your machine can build and run the
        full stack — frontend, backend, and database all came up and can talk to each other.
      </p>
      <p style={{ fontSize: "1.5rem", color }}>
        {status === "ok"
          ? "✅ Stack is up"
          : status === "error"
            ? "❌ Stack check failed"
            : "⏳ Checking…"}
      </p>
      <pre style={{ color }}>{detail}</pre>
    </main>
  );
}
