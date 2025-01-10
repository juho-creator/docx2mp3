import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Frame
from tkinter.ttk import Progressbar, Combobox
import docx
import os
import threading
import platform
import subprocess
from gtts import gTTS
from langdetect import detect
import soundfile as sf
import sounddevice as sd
from tempfile import NamedTemporaryFile
import time

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

# 단어 수를 기반으로 예상 시간을 추정하는 함수
def estimate_conversion_time(word_count):
    estimated_seconds = (17/12) * word_count * 0.2 + (5/12)
    return int(estimated_seconds)

# "다음" 버튼 클릭 시 실행되는 함수 수정
def show_preview():
    file_path = file_path_entry.get()
    if not os.path.isfile(file_path):
        messagebox.showerror("오류", "파일을 찾을 수 없습니다. 유효한 파일 경로를 입력하세요.")
        return
    try:
        content = read_docx(file_path)
        word_count = count_words(content)
        estimated_time = estimate_conversion_time(word_count)
        estimated_time_label.config(text=f"예상 변환 시간: {estimated_time}초")

        if content.strip():  # 미리보기 영역에 내용 표시
            text_preview.delete(1.0, tk.END)
            text_preview.insert(tk.END, content)
            convert_button.config(state=tk.NORMAL)  # 변환 버튼 활성화

            # 억양 선택 메뉴를 미리보기 아래로 이동
            label.pack_forget()
            accent_selection.pack_forget()
            label.pack(after=text_preview, pady=5)
            accent_selection.pack(after=label, pady=5)
        else:
            messagebox.showwarning("경고", "문서가 비어 있습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"문서를 읽는 중 오류가 발생했습니다: {e}")

# 현재 실행 중인 변환 프로세스를 추적하기 위한 플래그
current_thread = None

# MP3 변환을 별도 스레드에서 실행하는 함수
def convert_to_mp3_thread(content, output_path, lang, tld, speed):
    global current_thread
    try:
        progress_bar["value"] = 0  # 로딩바 초기화
        estimated_time = estimate_conversion_time(count_words(content))
        progress_bar["maximum"] = estimated_time

        for i in range(estimated_time):
            time.sleep(1)  # 1초 단위로 진행
            progress_bar["value"] += 1
            app.update_idletasks()

        docx_to_mp3(content, output_path, lang, tld, speed)
        messagebox.showinfo("성공", f"MP3 파일이 다음 위치에 저장되었습니다: {output_path}")
        open_directory(save_directory)
    except Exception as e:
        messagebox.showerror("오류", f"변환 중 오류가 발생했습니다: {e}")
    finally:
        current_thread = None  # 변환 완료 후 플래그 초기화

# 텍스트 내용을 MP3 파일로 변환하는 함수
def docx_to_mp3(content, file_path, lang, tld="com", speed=1.0):
    try:
        with NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav_file:
            tts = gTTS(text=content, lang=lang, tld=tld)
            tts.save(temp_wav_file.name)
            temp_file_path = temp_wav_file.name  # 파일 경로 저장

        # 로드하여 속도 조정
        data, samplerate = sf.read(temp_file_path)
        new_samplerate = int(samplerate * speed)
        sf.write(file_path, data, new_samplerate)

        # 임시 파일 삭제
        os.remove(temp_file_path)
    except Exception as e:
        raise RuntimeError(f"오디오 변환 중 오류가 발생했습니다: {e}")

# MP3 변환 버튼 클릭 시 실행되는 함수
def generate_mp3():
    global current_thread
    if not save_directory:
        messagebox.showerror("오류", "MP3 파일을 저장할 디렉토리를 선택하세요.")
        return
    if current_thread and current_thread.is_alive():
        messagebox.showwarning("경고", "현재 변환 작업이 진행 중입니다. 다시 시도하기 위해 기존 작업을 중단합니다.")
        current_thread = None  # 현재 스레드 초기화
        progress_bar["value"] = 0  # 진행 바 초기화

    file_path = file_path_entry.get()
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    content = read_docx(file_path)

    try:
        lang = detect(content)  # 언어 자동 감지
        tld = ""

        if lang == "en":  # 영어일 경우 억양 선택 메뉴 활성화
            accent = accent_selection.get()
            tld = ENGLISH_TLDS.get(accent, "com")
            file_name_with_lang = f"{file_name}_en_{tld.replace('.', '_')}.wav"
        else:
            file_name_with_lang = f"{file_name}_{lang}.wav"

        output_path = os.path.join(save_directory, file_name_with_lang)
        speed = speed_scale.get()  # 사용자 입력 속도 가져오기

        current_thread = threading.Thread(target=convert_to_mp3_thread, args=(content, output_path, lang, tld, speed))
        current_thread.start()
    except Exception as e:
        messagebox.showerror("오류", f"언어 감지 중 오류가 발생했습니다: {e}")

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

# 파일 경로 라벨과 입력 창
tk.Label(file_frame, text="워드 파일 경로:").grid(row=0, column=0, padx=5, pady=5)
file_path_entry = tk.Entry(file_frame, width=40)
file_path_entry.grid(row=0, column=1, padx=5, pady=5)

# 파일 선택 버튼
browse_button = tk.Button(file_frame, text="찾아보기", command=browse_file)
browse_button.grid(row=0, column=2, padx=5, pady=5)

# 저장 디렉토리 라벨과 선택 버튼
tk.Label(file_frame, text="저장 디렉토리:").grid(row=1, column=0, padx=5, pady=5)
save_directory_label = tk.Label(file_frame, text="선택되지 않음", anchor="w", width=40, relief="sunken")
save_directory_label.grid(row=1, column=1, padx=5, pady=5)
select_directory_button = tk.Button(file_frame, text="선택", command=select_directory)
select_directory_button.grid(row=1, column=2, padx=5, pady=5)

# 내용 미리보기 버튼
next_button = tk.Button(app, text="다음", command=show_preview)
next_button.pack(pady=5)

# 내용 미리보기 영역
text_preview = scrolledtext.ScrolledText(app, height=10, width=55, wrap=tk.WORD)
text_preview.pack(pady=10)

# 속도 선택 슬라이더 추가
speed_label = tk.Label(app, text="오디오 속도: (0.5배 ~ 2배)")
speed_label.pack(pady=5)
speed_scale = tk.Scale(app, from_=0.5, to=2.0, resolution=0.1, orient=tk.HORIZONTAL)
speed_scale.set(1.0)  # 기본값 1.0배속
speed_scale.pack(pady=5)

# 억양 선택 Combobox (기본적으로 숨김)
label = tk.Label(app, text="억양 선택:")
label.pack(pady=5)
label.pack_forget()  # 기본적으로 숨김
accent_selection = Combobox(app, values=list(ENGLISH_TLDS.keys()), state="readonly")
accent_selection.set("United States")  # 기본값: 미국
accent_selection.pack(pady=5)
accent_selection.pack_forget()  # 기본적으로 숨김

# 예상 시간 라벨
estimated_time_label = tk.Label(app, text="예상 변환 시간: ")
estimated_time_label.pack(pady=5)

# 진행 막대
progress_bar = Progressbar(app, mode="determinate")
progress_bar.pack(pady=10, fill=tk.X)

# MP3로 변환 버튼
convert_button = tk.Button(app, text="MP3로 변환", command=generate_mp3, state=tk.DISABLED)
convert_button.pack(pady=10)

# 애플리케이션 실행
app.mainloop()
