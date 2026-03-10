import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { GoogleGenAI } from '@google/genai';

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.post('/api/chat', async (req, res) => {
    try {
        const { message, context } = req.body;

        console.log(`Received message: ${message}`);

        // Check if Gemini API key exists
        if (process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY !== 'your_gemini_api_key_here') {
            const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
            const prompt = `System Context: You are ARIA, an AI Resource Intelligence Advisor for cloud optimization.\nCurrent Cloud Fleet Context:\n${context}\n\nUser Question: ${message}`;

            const response = await ai.models.generateContent({
                model: 'gemini-2.5-flash',
                contents: prompt,
            });

            res.json({ reply: response.text });
        } else {
            res.json({ reply: `(Mock mode) I am ARIA. I received your message: "${message}". Please set a valid GEMINI_API_KEY in backend/.env for real AI responses.` });
        }
    } catch (error) {
        console.error('Chat error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.listen(port, () => {
    console.log(`Server listening on port ${port}`);
});
