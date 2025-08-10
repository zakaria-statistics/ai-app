const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Non-streaming
export async function ask(prompt) {
    const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
    });
    if (!res.ok) {
        let detail = "Unknown error";
        try { detail = (await res.json()).detail || detail; } catch { }
        throw new Error(detail);
    }
    const data = await res.json();
    return data.response ?? "";
}

// Streaming over POST (ReadableStream + SSE frames)
export async function askStream(question, onToken, signal) {
    const res = await fetch(`${API_BASE}/ask_sse_post`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
        signal,
    });

    if (!res.ok || !res.body) {
        throw new Error(await res.text().catch(() => "Stream failed"));
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    let buffer = ""; // hold partial frame across chunks
    for (; ;) {
        const { value, done } = await reader.read();
        if (done) break;
        if (!value) continue;

        buffer += decoder.decode(value, { stream: true });

        // frames are separated by \n\n (Server-Sent Events)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? ""; // keep tail

        for (const raw of parts) {
            const frame = raw.trim();
            if (!frame || frame.startsWith(":")) continue; // heartbeat
            const line = frame.startsWith("data: ") ? frame.slice(6) : frame;

            if (line === "[DONE]") return;
            if (line.startsWith("[STREAM ERROR]")) {
                throw new Error(line.replace("[STREAM ERROR]", "").trim());
            }
            onToken(line);
        }
    }
}
