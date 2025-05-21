import sys
from PySide6.QtWidgets import QApplication
from missing_responses_dialog import MissingResponsesDialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    entries = [
        {
            "question": "Quelle est la capitale de la France?",
            "response": "",
            "audio_path": "/media/ron/Ronzz_Core/nextCloudSync/mindiverse-life/scripts/python/src/ronzz_tool/tatoeba_fr_audio/Sens_ça__.mp3",
        },
        {
            "question": "Combien font 2+2?",
            "response": "",
            "audio_path": "/media/ron/Ronzz_Core/nextCloudSync/mindiverse-life/scripts/python/src/ronzz_tool/tatoeba_fr_audio/Selon_toutes_les_app.mp3",
        },
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    if dialog.exec():
        print("Résultats après édition :")
        for i, entry in enumerate(entries, 1):
            print(f"{i}. Q: {entry['question']} | R: {entry['response']}")
    else:
        print("Dialog annulé.")
