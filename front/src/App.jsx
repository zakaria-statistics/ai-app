import { useState } from "react";
import { useAgent } from "./hooks/useAgent";
import "./styles.css";

export default function App() {
    const [prompt, setPrompt] = useState("");
    const { state, actions } = useAgent();
    const { response, error, loading, streaming } = state;
    const busy = loading || streaming;

    return (
        <div className="container">
            <h2>🧠 Local AI Agent</h2>

            <textarea
                rows={5}
                className="input"
                value={prompt}
                placeholder="Ask me anything…"
                onChange={(e) => setPrompt(e.target.value)}
            />

            <div className="buttons">
                <button onClick={() => actions.askOnce(prompt)} disabled={busy || !prompt.trim()}>
                    {loading ? "Loading…" : "Ask (/ask)"}
                </button>

                {!streaming ? (
                    <button onClick={() => actions.askSSE(prompt)} disabled={busy || !prompt.trim()}>
                        Ask (stream /ask_sse_post)
                    </button>
                ) : (
                    <button onClick={actions.stop} className="btn-stop">
                        ⏹ Stop
                    </button>
                )}
            </div>

            {(loading || streaming) && (
                <div className="status">
                    ⏳ {streaming ? "Streaming…" : "Waiting for response…"}
                </div>
            )}
            {error && <div className="error">Error: {error}</div>}

            <div className="response">
                <strong>Response:</strong>
                <div className="response-body">{response}</div>
            </div>
        </div>
    );
}
