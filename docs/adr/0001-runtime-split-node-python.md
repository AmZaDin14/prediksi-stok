# 0001 - Runtime split: Node microservice + Python core

Context: WhatsApp Business API costs ~$15/mo, and pure-Python WhatsApp Web libraries are community-maintained and unreliable. `whatsapp-web.js` (Node) is the most reliable free option for WhatsApp Web automation. However, Python is preferred for ML (prophet) and data processing.

Decision: WhatsApp connectivity runs as a thin Node.js microservice (`whatsapp-web.js`). All business logic, prediction, and persistence lives in Python (FastAPI + APScheduler). Communication is bidirectional HTTP on localhost: Node POSTs incoming messages to FastAPI `/webhook`, FastAPI calls Node `/send` for outgoing messages.

Rejected options: pure Python + `webwhatsapp-py` (unreliable, breaks often), Twilio API (paid, ~$15/mo), custom Selenium-based driver (fragile, maintenance burden).

This operates with two runtimes and two package managers. That's accepted as the cost of free+reliable WhatsApp connectivity.
