import OpenAI from "openai";

// OpenAI client - optional for hackathon (only needed for presentation features)
// Set OPENAI_API_KEY in .env.local if you want to use AI presentation generation
export const openai = process.env.OPENAI_API_KEY 
  ? new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
  : null;

// Helper to check if OpenAI is available
export const isOpenAIAvailable = () => !!openai;
