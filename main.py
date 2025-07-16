import customtkinter as ctk
from tkinter import filedialog
import whisper
import os
from datetime import datetime
import sys


#Zu Git hinzufügen
#Output ornder erstellen, falls nicht vorhanden
#formattierung nochmal checken
#tests mit interviews machen

# Modell-Mapping: Anzeige-Name → Whisper-Modellname
model_dict = {
    "Sehr schnell (niedrige Genauigkeit)": "tiny",
    "Schnell (mittlere Genauigkeit)": "base",
    "Ausgewogen (gute Genauigkeit/empfohlen)": "small",
    "Langsam (hohe Genauigkeit/Starker PC benötigt)": "medium",
    #"Sehr langsam (beste Genauigkeit/Kompletter Overkill)": "large"
}

# Aktuelles Modell initial laden
current_model_name = "base"
model = whisper.load_model(current_model_name)


def create_output_folder():
    # Pfad zur aktuellen .exe oder .py Datei ermitteln
    if getattr(sys, 'frozen', False):
        # Läuft als .exe (kompiliert)
        base_path = os.path.dirname(sys.executable)
    else:
        # Läuft als .py (Development)
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Output-Ordner Pfad erstellen
    output_path = os.path.join(base_path, "output")
    
    # Ordner erstellen, falls er nicht existiert
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Output-Ordner erstellt: {output_path}")
    else:
        print(f"Output-Ordner existiert bereits: {output_path}")
    
    return output_path


def maximize_window():
    app.state('zoomed')
    

# Dynamische Größe für Textbox berechnen
def resize_textbox(event):
    width = int(event.width * 0.7)
    height = int(event.height * 0.6)
    text_box.configure(width=width, height=height)

#Output Ordner öffnen
def open_output_folder():
    output_path = create_output_folder()  # Erstellt den Ordner falls nötig
    if os.path.exists(output_path):
        os.startfile(output_path)
    else:
        status_label.configure(text="Ordner 'output' konnte nicht erstellt werden.")

# Funktion zum Formatieren des Textes mit Zeilenumbrüchen, Kommas und Punkten
def format_text_with_linebreaks_commas_points(text, target=200, radius=20):
    result = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + target, length)

        search_start = max(start, end - radius)
        search_end = min(length, end + radius)

        # Suche Komma oder Punkt nach 'end' zuerst
        split_pos = -1
        for i in range(end, search_end):
            if text[i] in {',', '.'}:
                split_pos = i
                break
        # Falls nicht gefunden, suche Komma oder Punkt vor 'end'
        if split_pos == -1:
            for i in range(search_start, end):
                if text[i] in {',', '.'}:
                    split_pos = i
                    break

        if split_pos != -1:
            line_end = split_pos + 1  # Komma oder Punkt mitnehmen
        else:
            # Sonst am nächsten Leerzeichen nach 'end' umbrechen
            space_pos = text.find(' ', end)
            if space_pos == -1:
                line_end = length
            else:
                line_end = space_pos + 1

        line = text[start:line_end].strip()
        result.append(line)
        start = line_end

    return '\n'.join(result)


# Callback-Funktion für das Dropdown-Menü
def on_model_select(choice):
    status_label.configure(text="")
    global model
    # Modellname aus dict holen
    whisper_model_name = model_dict[choice]
    text_box.delete("1.0", "end")
    text_box.insert("1.0", f"Lade Modell: {choice} ...")
    #status_label.configure(text=f"Lade Modell: {choice} ...")
    app.update()
    model = whisper.load_model(whisper_model_name)
    text_box.delete("1.0", "end")
    text_box.insert("1.0", f"Modell gewechselt zu: {choice}\nWähle eine Audiodatei zum Transkribieren")
    #status_label.configure(text=f"Modell gewechselt zu: {choice}")

#Funktion zum Transkribieren der Audiodatei
def transkribieren():
    filepath = filedialog.askopenfilename(filetypes=[("Audio Dateien", "*.mp3 *.wav *.m4a")])
    if not filepath:
        return
    
    original_name = os.path.splitext(os.path.basename(filepath))[0]
    text_box.delete("1.0", "end")
    text_box.insert("1.0", "Transkribiere... Bitte warten.")
    #status_label.configure(text="Transkribiere... Bitte warten.")
    app.update()

    result = model.transcribe(filepath)
    text = result["text"]

    text_box.delete("1.0", "end")
    text_box.insert("1.0", text)
    
    formatted_text = format_text_with_linebreaks_commas_points(text)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = create_output_folder()
    text_filename = f"transkript_{original_name}_{timestamp}.txt"
    full_path = os.path.join(output_path, text_filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(formatted_text)

    
    text_box.delete("1.0", "end")
    text_box.insert("1.0", formatted_text)

    status_label.configure(text=f"Fertig! Gespeichert als:\n{text_filename}")

# GUI Setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Transkriptor")


# Grid-Setup für dynamische Größenanpassung
app.grid_rowconfigure(2, weight=1)   # Textbox soll wachsen (Reihe 2)
app.grid_columnconfigure(0, weight=1)

title = ctk.CTkLabel(app, text="🎙️Audio → Text", font=ctk.CTkFont(size=22, weight="bold"))
title.grid(row=0, column=0, pady=(20,10), sticky="n")

# Frame für die Buttons oben (zweispaltig)
button_frame = ctk.CTkFrame(app, fg_color="transparent")
button_frame.grid(row=0, column=0, sticky="ew", pady=(100, 10))

button_frame.grid_columnconfigure(0, weight=1)
button_frame.grid_columnconfigure(1, weight=1)

# Linker Button: Modell Dropdown
model_dropdown = ctk.CTkOptionMenu(button_frame, values=list(model_dict.keys()), command=on_model_select)
model_dropdown.set("Ausgewogen (gute Genauigkeit/völlig ausreichend)")
model_dropdown.grid(row=0, column=0, sticky="w", padx=(20,0))  # links bündig mit Textbox

# Rechter Button: Upload
upload_btn = ctk.CTkButton(button_frame, text="🎧 Audiodatei auswählen", command=transkribieren)
upload_btn.grid(row=0, column=1, sticky="e", padx=(0,20))  # rechts bündig mit Textbox

# Textbox (mit gleichen horizontalen Rändern wie Buttons)
text_box = ctk.CTkTextbox(app, font=("Arial", 14))
text_box.insert("1.0", "Wähle die Genauigkeit der Transkription und eine Audiodatei aus")
text_box.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

# Status Label darunter
status_label = ctk.CTkLabel(app, text="", font=("Arial", 12))
status_label.grid(row=3, column=0, sticky="ew", padx=20)

# Button "Datei anzeigen" unten
show_files_btn = ctk.CTkButton(app, text="Datei anzeigen", command=open_output_folder)
show_files_btn.grid(row=4, column=0, pady=10)



app.after(1, maximize_window)
app.mainloop()
