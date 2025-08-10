import { useRef, useState, useCallback } from "react";
import { ask, askStream } from "../lib/api";

export function useAgent() {
    const [response, setResponse] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const abortRef = useRef(null);

    const askOnce = useCallback(async (prompt) => {
        setLoading(true); setStreaming(false); setError(""); setResponse("");
        try {
            const out = await ask(prompt);
            setResponse(out);
        } catch (e) {
            setError(e.message || String(e));
        } finally {
            setLoading(false);
        }
    }, []);

    const askSSE = useCallback(async (prompt) => {
        setLoading(false); setStreaming(true); setError(""); setResponse("");
        const controller = new AbortController();
        abortRef.current = controller;

        try {
            await askStream(
                prompt,
                (token) => setResponse((prev) => prev + token),
                controller.signal
            );
        } catch (e) {
            if (e.name === "AbortError") setError("Stream aborted by user.");
            else setError(e.message || String(e));
        } finally {
            setStreaming(false);
            abortRef.current = null;
        }
    }, []);

    const stop = useCallback(() => {
        abortRef.current?.abort();
    }, []);

    return {
        state: { response, error, loading, streaming },
        actions: { askOnce, askSSE, stop },
    };
}
