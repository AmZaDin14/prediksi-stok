require('dotenv').config({ path: require('path').resolve(__dirname, '..', '.env') });

const { Client } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');

// --- Paths relative to project root ----------------------------------------
const PROJECT_ROOT = path.resolve(__dirname, '..');
const DATA_DIR = path.join(PROJECT_ROOT, 'data');
const CONNECTION_STATUS_PATH = path.join(DATA_DIR, 'connection_status.json');
const QR_PATH = path.join(DATA_DIR, 'qr.png');
const WEBHOOK_URL = 'http://localhost:8765/webhook';

// --- Ensure data directory exists ------------------------------------------
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// --- Connection status file helpers ----------------------------------------
function writeConnectionStatus(status, phoneNumber = null) {
    const now = new Date().toISOString();
    const statusData = {
        status: status,
        phone_number: phoneNumber,
        last_connected: status === 'connected' ? now : null,
        qr_generated_at: status === 'connecting' ? now : null,
    };
    fs.writeFileSync(CONNECTION_STATUS_PATH, JSON.stringify(statusData, null, 2));
}

// --- Initial status --------------------------------------------------------
writeConnectionStatus('disconnected');

// --- Chrome path (pick the best available) ----------------------------------
const CHROME_PATHS = [
    '/home/amri/.cache/puppeteer/chrome/linux-146.0.7680.153/chrome-linux64/chrome',
    '/home/amri/.cache/puppeteer/chrome/linux-149.0.7827.22/chrome-linux64/chrome',
];
const CHROME_PATH = CHROME_PATHS.find(p => fs.existsSync(p)) || undefined;

// --- WhatsApp client -------------------------------------------------------
const CLIENT = new Client({
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        executablePath: CHROME_PATH,
        userDataDir: path.join(DATA_DIR, 'wwebjs_profile'),
    },
});

// --- QR event --------------------------------------------------------------
CLIENT.on('qr', async (qr) => {
    console.log('QR Code received. Scan with WhatsApp:');

    // ASCII QR to console
    try {
        const ascii = await qrcode.toString(qr, { type: 'terminal' });
        console.log(ascii);
    } catch (err) {
        console.error('Failed to render ASCII QR:', err.message);
    }

    // PNG QR to file
    try {
        await qrcode.toFile(QR_PATH, qr, { type: 'png' });
        console.log('QR code saved to', QR_PATH);
    } catch (err) {
        console.error('Failed to save QR image:', err.message);
    }

    writeConnectionStatus('connecting');
});

// --- Ready event -----------------------------------------------------------
CLIENT.on('ready', () => {
    const phoneNumber = CLIENT.info.wid.user;
    const displayPhone = `+${phoneNumber}`;
    console.log('WhatsApp bot connected:', displayPhone);
    writeConnectionStatus('connected', displayPhone);

    // Start polling outgoing queue every 30 seconds
    setInterval(pollOutgoing, 30000);
});

// --- Disconnected event (auto-reconnect) -----------------------------------
CLIENT.on('disconnected', async (reason) => {
    console.log('WhatsApp bot disconnected:', reason);
    writeConnectionStatus('disconnected');
    console.log('Attempting reconnection in 5 seconds...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    CLIENT.initialize();
});

// --- Message event ---------------------------------------------------------
CLIENT.on('message', async (msg) => {
    if (!msg.body || msg.body.trim() === '') {
        return;
    }

    try {
        const response = await fetch(WEBHOOK_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_number: msg.from,
                body: msg.body,
            }),
        });

        if (response.ok) {
            const data = await response.json();
            const replyText = data.response || 'No response';
            await msg.reply(replyText);
        } else {
            console.error('Webhook returned HTTP', response.status);
            await msg.reply('Maaf, terjadi kesalahan pada server.');
        }
    } catch (err) {
        console.error('Error forwarding message to webhook:', err.message);
        await msg.reply('Maaf, tidak dapat terhubung ke server.');
    }
});

// --- Poll outgoing queue ---------------------------------------------------
async function pollOutgoing() {
    try {
        const ownerNumber = process.env.OWNER_NUMBER;
        if (!ownerNumber) {
            return; // No owner number configured, skip polling
        }

        const response = await fetch(`http://localhost:8765/outgoing?recipient=${encodeURIComponent(ownerNumber)}`);
        if (!response.ok) return;

        const messages = await response.json();
        for (const msg of messages) {
            try {
                await CLIENT.sendMessage(msg.recipient, msg.body);
                console.log(`Sent outgoing message to ${msg.recipient}: ${msg.body.substring(0, 50)}...`);
            } catch (err) {
                console.error('Failed to send outgoing message:', err.message);
            }
        }
    } catch (err) {
        console.error('Error polling outgoing queue:', err.message);
    }
}

// --- Start client ----------------------------------------------------------
CLIENT.initialize();
