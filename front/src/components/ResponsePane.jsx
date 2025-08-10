export default function ResponsePane({ text }) {
    return (
        <div style={{
            marginTop: 16, whiteSpace: "pre-wrap", padding: 12,
            border: "1px solid #ddd", borderRadius: 8, minHeight: 120
        }}>
            <strong>Response:</strong>
            <div style={{ marginTop: 8 }}>{text}</div>
        </div>
    );
}
