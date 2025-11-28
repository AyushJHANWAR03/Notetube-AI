"""
Prompts for rewriting user notes in different styles.
"""

# Rewrite style prompts - each style has a specific instruction
REWRITE_PROMPTS = {
    "simplify": "Rewrite this in simpler, easier to understand language. Keep the same meaning but use simpler words and shorter sentences:",
    "summarize": "Summarize this in 1-2 concise sentences while keeping the key information:",
    "formal": "Rewrite this in formal, professional language suitable for academic or business contexts:",
    "bullet_points": "Convert this into clear, concise bullet points:",
    "explain": "Explain this concept as if teaching a beginner who has no prior knowledge. Be clear and thorough:"
}

# System prompt for the rewrite assistant
REWRITE_SYSTEM_PROMPT = "You are a helpful assistant that rewrites text according to specific instructions. Keep the core meaning intact. Respond only with the rewritten text, no explanations."
