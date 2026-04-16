const http = require('http');
const https = require('https');

const PORT = 8001;

const server = http.createServer((req, res) => {
    // Add CORS headers instantly
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');

    // Handle preflight specifically
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.method === 'POST') {
        // Forward exactly to HuggingFace
        const options = {
            hostname: 'api-inference.huggingface.co',
            path: '/models/FunAudioLLM/SenseVoiceSmall',
            method: 'POST',
            headers: {
                'Authorization': req.headers['authorization'],
                'Content-Type': req.headers['content-type']
            }
        };

        const proxyReq = https.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, {
                'Content-Type': 'application/json',
                ...proxyRes.headers
            });
            proxyRes.pipe(res);
        });

        proxyReq.on('error', (e) => {
            console.error("Proxy error:", e.message);
            res.writeHead(500);
            res.end(JSON.stringify({ error: e.message }));
        });

        // Pipe audio data smoothly
        req.pipe(proxyReq);
    } else {
        res.writeHead(405);
        res.end("Method Not Allowed");
    }
});

server.listen(PORT, () => {
    console.log(`🚀 Zero-dependency CORS Proxy running on http://localhost:${PORT}`);
    console.log(`Listening for audio blobs and forwarding to Hugging Face...`);
});
