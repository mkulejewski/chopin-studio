import { useEffect, useState } from "react";
import { api, json } from "./api";
import { TouchButton as Button } from "./TouchButton";
export function AiConfig({ onError }: { onError: (e: unknown) => void }) {
  const [status, setStatus] = useState<any>(null),
    [key, setKey] = useState("");
  useEffect(() => {
    void api("/ai/config").then(setStatus).catch(onError);
  }, []);
  return (
    <div>
      <p>
        {status?.configured
          ? "An OpenAI key is configured locally."
          : "No OpenAI key configured. Local reports work without one."}
        {status?.environment ? " The environment key takes priority." : ""}
      </p>
      <label>
        Optional OpenAI API key
        <input
          type="password"
          autoComplete="new-password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="Enter using your system on-screen keyboard"
        />
      </label>
      <Button
        className="secondary"
        disabled={key.length < 10}
        onClick={() =>
          void api("/ai/config", json("PUT", { api_key: key }))
            .then(() => {
              setKey("");
              setStatus({ configured: true });
            })
            .catch(onError)
        }
      >
        Save key on this computer
      </Button>
      <p className="muted">
        Stored in a private local file with owner-only permissions; never
        returned by the API or included in exports. Saving does not contact
        OpenAI. Sending analysis still requires the explicit action below.
      </p>
    </div>
  );
}
