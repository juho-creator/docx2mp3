import asyncio
import edge_tts

VOICES = {
    "English": [
        'en-US-JennyNeural','en-AU-NatashaNeural', 'en-AU-WilliamNeural', 'en-CA-ClaraNeural', 'en-CA-LiamNeural', 
        'en-GB-LibbyNeural', 'en-GB-MaisieNeural'
    ],
    "Korean": [
        'ko-KR-InJoonNeural', 'ko-KR-SunHiNeural'
    ]
}

async def convert_text_to_speech(text: str, voice: str, output_file: str, rate: str = "+0%") -> None:
    """
    Converts text to speech and saves it as an MP3 file using edge_tts.

    Parameters:
        text (str): The text to be converted to speech.
        voice (str): The voice to use for the conversion.
        output_file (str): The output MP3 file path.
        rate (str): The speed adjustment for the voice (e.g., '+20%' for 20% faster).
    """
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_file)
        print(f"Conversion successful! File saved as: {output_file}")
    except Exception as e:
        print(f"An error occurred during conversion: {e}")
