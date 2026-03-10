import { fileURLToPath } from 'url';
import { dirname } from 'path';
import fs from 'fs';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const originalImagePath = path.join(__dirname, '..', '.gemini', 'antigravity', 'brain', 'd755602b-b4e2-44ec-a1c4-64d8f9be80af', '.system_generated', 'click_feedback', 'click_feedback_1772816365487.png');
const targetImagePath = path.join(__dirname, '..', '.gemini', 'antigravity', 'brain', 'd755602b-b4e2-44ec-a1c4-64d8f9be80af', 'success_screenshot.png');

try {
    fs.copyFileSync(originalImagePath, targetImagePath);
    console.log('Copied successfully');
} catch (e) {
    console.error(e);
}
