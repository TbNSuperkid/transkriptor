import customtkinter as ctk
from tkinter import filedialog
import whisper
import os
from datetime import datetime
import sys
import subprocess
from resemblyzer import VoiceEncoder, preprocess_wav
from resemblyzer import VoiceEncoder
import numpy as np
import scipy.io.wavfile as wav


encoder = VoiceEncoder()
sample_rate = 16000  # Standard Sample Rate für Whisper und Resemblyzer


# ---------------------- MODEL SETUP ----------------------
model_dict = {
    "Sehr schnell (niedrige Genauigkeit)": "tiny",
    "Schnell (mittlere Genauigkeit)": "base",
    "Ausgewogen (gute Genauigkeit/empfohlen)": "small",
    "Langsam (hohe Genauigkeit/Starker PC benötigt)": "medium"
}
current_model_name = "base"
model = whisper.load_model(current_model_name)
encoder = VoiceEncoder()  # Resemblyzer Speaker Encoder laden

# ---------------------- UTILITY FUNKTIONEN ----------------------
def create_output_folder():
    base_path = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
    output_path = os.path.join(base_path, "output")
    os.makedirs(output_path, exist_ok=True)
    return output_path

def maximize_window():
    app.state('zoomed')

def format_text_with_linebreaks_commas_points(text, target=200, radius=20):
    result = []
    start = 0
    length = len(text)

    while start < length:
        remaining = text[start:].strip()

        # Wenn der Rest kürzer ist als target, einfach anhängen
        if len(remaining) <= target:
            result.append(remaining)
            break

        end = start + target
        search_start = max(start, end - radius)
        search_end = min(length, end + radius)

        split_pos = -1

        # Suche Komma oder Punkt nach 'end' zuerst
        for i in range(end, search_end):
            if text[i] in {',', '.'}:
                split_pos = i
                break

        # Wenn nichts nach 'end' gefunden, dann vor 'end'
        if split_pos == -1:
            for i in range(search_start, end):
                if text[i] in {',', '.'}:
                    split_pos = i
                    break

        if split_pos != -1:
            line_end = split_pos + 1
        else:
            # An nächstem Leerzeichen umbrechen
            space_pos = text.find(' ', end)
            line_end = length if space_pos == -1 else space_pos + 1

        line = text[start:line_end].strip()
        result.append(line)
        start = line_end

    return '\n'.join(result)


def convert_to_wav(filepath):
    wav_path = os.path.splitext(filepath)[0] + ".converted.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", filepath, "-ar", str(sample_rate), wav_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path

def diarize_speakers(wav_path, segments):
    wav_preprocessed = preprocess_wav(wav_path)
    _, cont_embeds, _ = encoder.embed_utterance(wav_preprocessed, return_partials=True)

    speaker_ids = []
    threshold = 0.75
    known_speakers = []

    for emb in cont_embeds:
        assigned = False
        for i, ref in enumerate(known_speakers):
            similarity = np.inner(emb, ref)
            if similarity > threshold:
                speaker_ids.append(i)
                known_speakers[i] = (ref + emb) / 2  # Update reference
                assigned = True
                break
        if not assigned:
            speaker_ids.append(len(known_speakers))
            known_speakers.append(emb)

    segment_speakers = []
    ratio = len(cont_embeds) / len(segments)
    for idx, seg in enumerate(segments):
        speaker_idx = int(round(idx * ratio))
        speaker = speaker_ids[speaker_idx] if speaker_idx < len(speaker_ids) else 0
        segment_speakers.append((f"Sprecher {speaker + 1}", seg['text'].strip()))

    return segment_speakers

def group_speaker_blocks(speaker_segments):
    """
    Kombiniert aufeinanderfolgende Sprechersegmente mit demselben Sprecher zu einem Block.
    """
    if not speaker_segments:
        return []

    grouped = []
    current_speaker, current_text = speaker_segments[0]

    for speaker, text in speaker_segments[1:]:
        if speaker == current_speaker:
            current_text += " " + text.strip()
        else:
            grouped.append((current_speaker, current_text.strip()))
            current_speaker, current_text = speaker, text.strip()

    # letzten Block anhängen
    grouped.append((current_speaker, current_text.strip()))
    return grouped

def format_grouped_blocks(grouped):
    formatted = []
    for speaker, text in grouped:
        formatted.append(f"[{speaker}]: {text}")
    return "\n\n".join(formatted)

# ---------------------- GUI CALLBACKS ----------------------
def on_model_select(choice):
    global model
    whisper_model_name = model_dict[choice]
    text_box.delete("1.0", "end")
    text_box.insert("1.0", f"Lade Modell: {choice} ...")
    app.update()
    model = whisper.load_model(whisper_model_name)
    text_box.delete("1.0", "end")
    text_box.insert("1.0", f"Modell gewechselt zu: {choice}\nWähle eine Audiodatei zum Transkribieren")

def open_output_folder():
    os.startfile(create_output_folder())

def transkribieren():
    filepath = filedialog.askopenfilename(filetypes=[("Audio Dateien", "*.mp3 *.wav *.m4a")])
    if not filepath:
        return

    text_box.delete("1.0", "end")
    text_box.insert("1.0", "Transkribiere... Bitte warten.")
    app.update()

    original_name = os.path.splitext(os.path.basename(filepath))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = create_output_folder()

    # Konvertieren, falls nötig
    if not filepath.endswith(".wav"):
        filepath = convert_to_wav(filepath)

    # Whisper mit Segmenten
    result = model.transcribe(filepath, verbose=False, word_timestamps=False)
    segments = result["segments"]

    # Sprecher zuordnen
    speaker_segments = diarize_speakers(filepath, segments)

    # Formatieren für Ausgabe
    #formatted_lines = [f"[{speaker}]: {text}" for speaker, text in speaker_segments]
    #final_text = "\n\n".join(formatted_lines)
    final_text = format_grouped_blocks(group_speaker_blocks(speaker_segments))   

    # Anzeigen und Speichern
    text_box.delete("1.0", "end")
    text_box.insert("1.0", final_text)

    text_filename = f"transkript_{original_name}_{timestamp}.txt"
    with open(os.path.join(output_path, text_filename), "w", encoding="utf-8") as f:
        f.write(final_text)

    status_label.configure(text=f"Fertig! Gespeichert als: {text_filename}")

# ---------------------- GUI SETUP ----------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
app = ctk.CTk()
app.title("Transkriptor mit Sprechererkennung")
app.grid_rowconfigure(2, weight=1)
app.grid_columnconfigure(0, weight=1)

# Titel
title = ctk.CTkLabel(app, text="🎙️Audio → Text + Sprecher", font=ctk.CTkFont(size=22, weight="bold"))
title.grid(row=0, column=0, pady=(20,10), sticky="n")

# Button-Frame
button_frame = ctk.CTkFrame(app, fg_color="transparent")
button_frame.grid(row=1, column=0, sticky="ew", pady=(10, 10))
button_frame.grid_columnconfigure(0, weight=1)
button_frame.grid_columnconfigure(1, weight=1)

model_dropdown = ctk.CTkOptionMenu(button_frame, values=list(model_dict.keys()), command=on_model_select)
model_dropdown.set("Ausgewogen (gute Genauigkeit/empfohlen)")
model_dropdown.grid(row=0, column=0, sticky="w", padx=(20,0))

upload_btn = ctk.CTkButton(button_frame, text="🎧 Audiodatei auswählen", command=transkribieren)
upload_btn.grid(row=0, column=1, sticky="e", padx=(0,20))

# Textbox
text_box = ctk.CTkTextbox(app, font=("Arial", 14))
text_box.insert("1.0", "Wähle die Genauigkeit der Transkription und eine Audiodatei aus")
text_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

# Status + Datei anzeigen
status_label = ctk.CTkLabel(app, text="", font=("Arial", 12))
status_label.grid(row=3, column=0, sticky="ew", padx=20)

show_files_btn = ctk.CTkButton(app, text="Datei anzeigen", command=open_output_folder)
show_files_btn.grid(row=4, column=0, pady=10)

app.after(1, maximize_window)
app.mainloop()
