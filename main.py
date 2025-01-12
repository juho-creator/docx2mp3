import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Frame
from tkinter.ttk import Combobox
import docx
import os
import threading
import platform
import subprocess
from gtts import gTTS
from langdetect import detect
import soundfile as sf
from tempfile import NamedTemporaryFile
import time
from tts import *

# 파일 대화 상자를 열어 .docx 파일을 선택하는 함수
def browse_file():
    file_path = filedialog.askopenfilename(filetypes=[("Word Files", "*.docx")])
    file_path_entry.delete(0, tk.END)
    file_path_entry.insert(0, file_path)

# 저장할 디렉토리를 선택하는 함수
def select_directory():
    global save_directory
    save_directory = filedialog.askdirectory()
    if save_directory:
        save_directory_label.config(text=f"{save_directory}")

# 지정된 디렉토리를 엽니다.
def open_directory(directory):
    if platform.system() == "Windows":
        os.startfile(directory)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", directory])
    else:
        subprocess.Popen(["xdg-open", directory])

# .docx 파일의 텍스트 내용을 읽는 함수
def read_docx(file_path):
    return '\n'.join(paragraph.text for paragraph in docx.Document(file_path).paragraphs)

# 텍스트 내용에서 단어 수를 세는 함수
def count_words(content):
    return len(content.split())

# 고유 파일 이름 생성
def generate_unique_filename(base_name, lang, voice, speed, directory, ext=".mp3"):
    counter = 1
    unique_name = f"{base_name}_{lang}_{voice}_{speed}{ext}"
    while os.path.exists(os.path.join(directory, unique_name)):
        unique_name = f"{base_name}_{lang}_{voice}_{speed}_{counter}{ext}"
        counter += 1
    return unique_name

def show_preview():
    file_path = file_path_entry.get()
    if not os.path.isfile(file_path):
        messagebox.showerror("오류", "파일을 찾을 수 없습니다. 유효한 파일 경로를 입력하세요.")
        return
    try:
        content = read_docx(file_path)

        if content.strip():
            text_preview.delete(1.0, tk.END)
            text_preview.insert(tk.END, content)
            convert_button.config(state=tk.NORMAL)

            # 언어 감지 및 음성 선택 콤보박스 업데이트
            lang = detect(content)
            if lang == "en":
                lang = "English"
            elif lang == "ko":
                lang = "Korean"
            else:
                messagebox.showerror("Error", f"No TTS voices available for language: {lang}")
                return

            voices = VOICES.get(lang, [])
            if not voices:
                messagebox.showerror("Error", f"No voices available for detected language: {lang}")
                return

            voice_selection['values'] = voices
            voice_selection.set(voices[0])  # 기본 음성을 첫 번째로 설정

        else:
            messagebox.showwarning("경고", "문서가 비어 있습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"문서를 읽는 중 오류가 발생했습니다: {e}")

# 현재 실행 중인 변환 프로세스를 추적하기 위한 플래그
current_thread = None

def convert_to_mp3_thread(content, output_path, lang, voice, speed):
    global current_thread
    try:
        # Create an event loop for asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(docx_to_mp3(content, output_path, lang, voice, speed))
        loop.close()

        messagebox.showinfo("Success", f"MP3 file saved at: {output_path}")
        open_directory(save_directory)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during conversion: {e}")
    finally:
        current_thread = None
        convert_button.config(state=tk.NORMAL)

async def docx_to_mp3(content, file_path, lang, voice, speed="+0%"):
    """
    Convert text to MP3 using the edge_tts library.
    
    Parameters:
        content (str): The text content to convert.
        file_path (str): Path to save the MP3 file.
        lang (str): Language of the text.
        voice (str): Voice to use for TTS.
        speed (str): Rate of speech adjustment.
    """
    try:
        # Speed is already in the correct format (e.g., "+30%")
        await convert_text_to_speech(content, voice, file_path, rate=speed)
    except Exception as e:
        raise RuntimeError(f"Audio conversion error: {e}")

def generate_mp3():
    global current_thread
    if not save_directory:
        messagebox.showerror("오류", "MP3 파일을 저장할 디렉토리를 선택하세요.")
        return
    if current_thread and current_thread.is_alive():
        messagebox.showwarning("경고", "현재 변환 작업이 진행 중입니다. 완료 후 다시 시도하세요.")
        return

    file_path = file_path_entry.get()
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    content = read_docx(file_path)

    try:
        lang = detect(content)
        if lang == "en":
            lang = "English"
        elif lang == "ko":
            lang = "Korean"
        else:
            messagebox.showerror("Error", f"No TTS voices available for language: {lang}")
            return

        # 음성 선택 콤보박스에 음성을 채우기 (if not already populated)
        voices = VOICES.get(lang, [])
        if not voices:
            messagebox.showerror("Error", f"No voices available for detected language: {lang}")
            return

        if voice_selection.get() not in voices:  # Ensure selected voice is valid
            voice_selection['values'] = voices
            voice_selection.set(voices[0])  # 기본 음성을 첫 번째로 설정

        # 사용자가 선택한 음성 가져오기
        selected_voice = voice_selection.get()
        if not selected_voice:
            messagebox.showerror("Error", "Please select a voice for the conversion.")
            return

        # 속도를 edge_tts에서 지원하는 형식으로 조정 (e.g., "+20%" 또는 "-20%")
        speed_adjustment = speed_scale.get() * 100 - 100
        if speed_adjustment >= 0:
            speed = f"+{speed_adjustment:.0f}%"
        else:
            speed = f"{speed_adjustment:.0f}%"

        file_name_with_lang = generate_unique_filename(file_name, lang, selected_voice, speed, save_directory, ext=".mp3")
        output_path = os.path.join(save_directory, file_name_with_lang)

        # 변환 버튼 비활성화 후 변환 스레드 실행
        convert_button.config(state=tk.DISABLED)
        current_thread = threading.Thread(
            target=convert_to_mp3_thread,
            args=(content, output_path, lang, selected_voice, speed),
        )
        current_thread.start()
    except Exception as e:
        messagebox.showerror("오류", f"언어 감지 중 오류가 발생했습니다: {e}")
        convert_button.config(state=tk.NORMAL)

# 메인 애플리케이션 창 설정
app = tk.Tk()
app.title("DOCX to MP3 변환기")
app.geometry("500x700")

# 저장할 디렉토리를 저장하는 전역 변수
save_directory = ""

# English TLD options for different accents
ENGLISH_TLDS = {
    "United States": "us",
    "United Kingdom": "co.uk",
    "Australia": "com.au",
    "Canada": "ca"
}

# 파일 경로와 저장 디렉토리를 표시하는 영역
file_frame = Frame(app)
file_frame.pack(pady=10)

tk.Label(file_frame, text="워드 파일 경로:").grid(row=0, column=0, padx=5, pady=5)
file_path_entry = tk.Entry(file_frame, width=40)
file_path_entry.grid(row=0, column=1, padx=5, pady=5)

browse_button = tk.Button(file_frame, text="찾아보기", command=browse_file)
browse_button.grid(row=0, column=2, padx=5, pady=5)

tk.Label(file_frame, text="저장 디렉토리:").grid(row=1, column=0, padx=5, pady=5)
save_directory_label = tk.Label(file_frame, text="선택되지 않음", anchor="w", width=40, relief="sunken")
save_directory_label.grid(row=1, column=1, padx=5, pady=5)
select_directory_button = tk.Button(file_frame, text="선택", command=select_directory)
select_directory_button.grid(row=1, column=2, padx=5, pady=5)

# 내용 미리보기 버튼
next_button = tk.Button(app, text="다음", command=show_preview)
next_button.pack(pady=5)

text_preview = scrolledtext.ScrolledText(app, height=10, width=55, wrap=tk.WORD)
text_preview.pack(pady=10)

speed_label = tk.Label(app, text="오디오 속도: (0.5배 ~ 2배)")
speed_label.pack(pady=5)
speed_scale = tk.Scale(app, from_=0.5, to=2.0, resolution=0.1, orient=tk.HORIZONTAL)
speed_scale.set(1.0)
speed_scale.pack(pady=5)

# 음성 선택 레이블 및 콤보박스
voice_label = tk.Label(app, text="음성 선택:")
voice_label.pack(pady=5)
voice_selection = Combobox(app, state="readonly", width=40)
voice_selection.pack(pady=5)

convert_button = tk.Button(app, text="MP3로 변환", command=generate_mp3, state=tk.DISABLED)
convert_button.pack(pady=10)

app.mainloop()
