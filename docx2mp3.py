import docx
from gtts import gTTS
from playsound import playsound

def read_docx(file_path):
    # Load the document and extract paragraphs as a single string
    return '\n'.join(paragraph.text for paragraph in docx.Document(file_path).paragraphs)

def docx_to_mp3(content):
    # Convert text to speech, save, and play
    tts = gTTS(content, lang='en')
    tts.save("output.mp3")
    playsound("output.mp3")



# Example usage
file_path = r'C:\Users\me\Documents\카카오톡 받은 파일\20241003_한국 고속도로(문구)_PM(김기송) - 영어.docx'  # Replace with your .docx file path
content = read_docx(file_path)
docx_to_mp3(content)
