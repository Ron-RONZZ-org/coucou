# Préférence utilisateur : Toujours utiliser les méthodes non-bloquantes (show/open) pour les dialogues et fenêtres quand c'est possible.

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QMessageBox,
    QDialog,
    QDateEdit,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QTextEdit,  # Pour PlainPasteTextEdit
    QProgressBar,  # Pour ProgressBarHelper
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
import os
import csv
import json
import unicodedata
import logging

# Initialisation du logger ffmpeg (au début du fichier)
ffmpeg_logger = logging.getLogger("ffmpeg")
if not ffmpeg_logger.hasHandlers():
    handler = logging.FileHandler("ffmpeg_errors.log", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    ffmpeg_logger.addHandler(handler)
    ffmpeg_logger.setLevel(logging.ERROR)


class PlainPasteTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        # Coller uniquement le texte brut, ignorer le formatage
        if source.hasText():
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)


class ProgressBarHelper:
    """
    Classe utilitaire pour gérer une QProgressBar de façon centralisée.
    Usage :
        pb = ProgressBarHelper(parent_layout)
        pb.show(max_value)
        pb.set_value(val)
        pb.hide()
    """

    def __init__(self, parent_layout=None, parent_widget=None):
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        if parent_layout is not None:
            parent_layout.addWidget(self.progress_bar)
        elif parent_widget is not None:
            parent_widget.layout().addWidget(self.progress_bar)

    def show(self, maximum):
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

    def set_value(self, value):
        self.progress_bar.setValue(value)

    def hide(self):
        self.progress_bar.setVisible(False)

    def widget(self):
        return self.progress_bar


class TimeUtils:
    @staticmethod
    def parse_time_to_ms(val):
        """Convertit une chaîne hh:mm:ss, mm:ss ou ss en millisecondes."""
        if not val or not str(val).strip():
            return None
        val = str(val).strip()
        try:
            parts = val.split(":")
            parts = [int(float(p)) for p in parts]
            if len(parts) == 3:
                h, m, s = parts
            elif len(parts) == 2:
                h = 0
                m, s = parts
            elif len(parts) == 1:
                h = 0
                m = 0
                s = parts[0]
            else:
                return None
            return (h * 3600 + m * 60 + s) * 1000
        except Exception:
            return None

    @staticmethod
    def ms_to_str(ms):
        """Convertit des millisecondes en chaîne hh:mm:ss, mm:ss ou ss."""
        if ms is None:
            return ""
        s = int(ms // 1000)
        h = s // 3600
        m = (s % 3600) // 60
        s = s % 60
        if h > 0:
            return f"{h:02}:{m:02}:{s:02}"
        elif m > 0:
            return f"{m:02}:{s:02}"
        else:
            return f"{s:02}"


class MediaUtils:
    @staticmethod
    def play_media_file_qt(
        parent, media_path, media_player=None, video_dialog_ref=None
    ):
        """
        Lecture centralisée d'un fichier média (audio ou vidéo) dans une app Qt.
        - parent : QWidget parent (pour QMessageBox et pop-up vidéo)
        - media_path : chemin du fichier média
        - media_player : instance QMediaPlayer pour l'audio (optionnel, sinon créé temporairement)
        - video_dialog_ref : dict ou objet avec attribut 'dialog' pour gérer la fermeture de la vidéo précédente
        """
        if (
            not media_path
            or not isinstance(media_path, str)
            or not os.path.exists(media_path)
        ):
            QMessageBox.warning(parent, "Erreur", "Fichier média introuvable.")
            return
        ext = os.path.splitext(media_path)[1].lower()
        if ext in [".mp3", ".wav", ".ogg"]:
            if media_player is None:
                media_player = QMediaPlayer(parent)
                audio_output = QAudioOutput(parent)
                media_player.setAudioOutput(audio_output)
            media_player.setSource(media_path)
            media_player.play()
        elif ext in [".mp4", ".avi", ".mov", ".mkv"]:
            # Fermer la vidéo précédente si elle existe
            if video_dialog_ref and getattr(video_dialog_ref, "dialog", None):
                old_dialog = video_dialog_ref.dialog
                if old_dialog.isVisible():
                    old_dialog.close()
                video_dialog_ref.dialog = None
            video_dialog = QDialog(parent)
            video_dialog.setWindowTitle("Lecture vidéo")
            layout = QVBoxLayout()
            video_widget = QVideoWidget(video_dialog)
            layout.addWidget(video_widget)
            video_player = QMediaPlayer(video_dialog)
            video_player.setVideoOutput(video_widget)
            audio_output = QAudioOutput(video_dialog)
            video_player.setAudioOutput(audio_output)
            video_player.setSource(media_path)
            video_player.play()
            video_dialog.setLayout(layout)
            video_dialog.setMinimumSize(640, 360)

            def stop_video():
                video_player.stop()

            video_dialog.finished.connect(stop_video)
            if video_dialog_ref is not None:
                video_dialog_ref.dialog = video_dialog
            video_dialog.show()  # Non-bloquant

    class MediaFileProcessing:
        @staticmethod
        def process_media_file(
            src_path: str,
            dest_dir: str,
            start_time_ms: int = None,
            end_time_ms: int = None,
        ) -> str:
            """
            Copie ou découpe un fichier média (audio ou vidéo) dans dest_dir.
            Retourne le chemin du fichier copié/découpé.
            """
            import shutil
            from common_methods import TextUtils
            import os
            from pydub import AudioSegment

            ext = os.path.splitext(src_path)[1].lower()
            # Correction : générer un nom unique et propre une seule fois
            if ext in [".mp4", ".avi", ".mov", ".mkv"] and (
                start_time_ms is not None or end_time_ms is not None
            ):
                base, _ = os.path.splitext(os.path.basename(src_path))
                base = TextUtils.clean_filename(base)
                file_name = (
                    f"{base}_clip_{start_time_ms or 0}_{end_time_ms or 'end'}.mp4"
                )
            else:
                file_name = TextUtils.clean_filename(os.path.basename(src_path))
            dest_path = os.path.join(dest_dir, file_name)

            # Découpage audio
            if ext in [".mp3", ".wav", ".ogg"]:
                if start_time_ms is not None and end_time_ms is not None:
                    audio = AudioSegment.from_file(src_path)
                    segment = audio[start_time_ms:end_time_ms]
                    segment.export(dest_path, format="mp3")
                else:
                    shutil.copy2(src_path, dest_path)
            # Découpage vidéo (remplacement MoviePy par ffmpeg)
            elif ext in [".mp4", ".avi", ".mov", ".mkv"]:
                import subprocess

                if start_time_ms is not None and end_time_ms is not None:
                    start_sec = start_time_ms / 1000.0
                    end_sec = end_time_ms / 1000.0
                    duration = end_sec - start_sec
                    ffmpeg_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        src_path,
                        "-ss",
                        str(start_sec),
                        "-t",
                        str(duration),
                        "-c:v",
                        "libx264",
                        "-c:a",
                        "aac",
                        dest_path,
                    ]
                    try:
                        result = subprocess.run(
                            ffmpeg_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True,
                        )
                    except Exception as e:
                        error_msg = f"Erreur ffmpeg sur {src_path}: {e}\n" + getattr(
                            e, "stderr", b""
                        ).decode(errors="ignore")
                        ffmpeg_logger.error(error_msg)
                        raise Exception(
                            f"Erreur lors du découpage vidéo (ffmpeg) : {e}\n{getattr(e, 'stderr', b'').decode(errors='ignore')}"
                        )
                else:
                    shutil.copy2(src_path, dest_path)
            else:
                raise Exception("Format de média non supporté.")
            return dest_path


class FavoritesManager:
    @staticmethod
    def get_favorites_filename(db_manager):
        db_path = getattr(db_manager, "db_path", None)
        if db_path:
            db_name = os.path.splitext(os.path.basename(db_path))[0]
            return f"favourites-{db_name}.csv"
        return "favourites.csv"

    @staticmethod
    def mark_as_favorite(db_manager, entry_uuid, parent=None, logger=None):
        fav_file = FavoritesManager.get_favorites_filename(db_manager)
        # Vérifier si l'UUID existe déjà
        uuids = set()
        if os.path.exists(fav_file):
            try:
                with open(fav_file, "r", encoding="utf-8") as file:
                    reader = csv.reader(file)
                    for row in reader:
                        if row:
                            uuids.add(row[0])
            except Exception as e:
                if logger:
                    logger.error(f"Erreur lors de la lecture de {fav_file}: {e}")
                if parent:
                    QMessageBox.critical(
                        parent, "Erreur", "Impossible de vérifier les favoris!"
                    )
                return False
        if entry_uuid in uuids:
            if parent:
                QMessageBox.information(
                    parent, "Info", "Cette entrée est déjà dans les favoris."
                )
            return False
        try:
            with open(fav_file, "a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([entry_uuid])
            if logger:
                logger.info(
                    f"Entrée marquée comme favorite: {entry_uuid} dans {fav_file}"
                )
            if parent:
                QMessageBox.information(parent, "Succès", "Entrée ajoutée aux favoris!")
            return True
        except Exception as e:
            if logger:
                logger.error(f"Erreur lors de l'ajout aux favoris: {e}")
            if parent:
                QMessageBox.critical(
                    parent, "Erreur", "Impossible d'ajouter aux favoris!"
                )
            return False

    @staticmethod
    def load_favorite_records(db_manager, parent=None, logger=None):
        fav_file = FavoritesManager.get_favorites_filename(db_manager)
        if not os.path.exists(fav_file):
            if parent:
                QMessageBox.information(parent, "Info", "Aucun favori trouvé.")
            return []
        uuids = set()
        try:
            with open(fav_file, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if row:
                        uuids.add(row[0])
        except Exception as e:
            if logger:
                logger.error(f"Erreur lors de la lecture de {fav_file}: {e}")
            if parent:
                QMessageBox.critical(
                    parent, "Erreur", "Impossible de charger les favoris!"
                )
            return []
        if not uuids:
            if parent:
                QMessageBox.information(parent, "Info", "Aucun favori trouvé.")
            return []
        records = []
        for uuid in uuids:
            record = db_manager.fetch_record_by_uuid(uuid)
            if record:
                records.append(record)
        if not records and parent:
            QMessageBox.information(
                parent,
                "Info",
                "Aucun enregistrement favori trouvé dans la base de données.",
            )
        return records


class DialogUtils:
    @staticmethod
    def select_date_range(parent=None):
        """Ouvre un dialogue pour sélectionner une plage de dates et retourne (start_date, end_date) en objets date Python, ou None si annulé."""
        dialog = QDialog(parent)
        dialog.setWindowTitle("Sélectionner une plage de dates")
        layout = QVBoxLayout(dialog)
        label = QLabel("Sélectionnez la plage de dates à filtrer :")
        layout.addWidget(label)
        start_date_edit = QDateEdit()
        start_date_edit.setCalendarPopup(True)
        start_date_edit.setDate(QDate.currentDate().addDays(-1))
        layout.addWidget(start_date_edit)
        end_date_edit = QDateEdit()
        end_date_edit.setCalendarPopup(True)
        end_date_edit.setDate(QDate.currentDate())
        layout.addWidget(end_date_edit)
        confirm_button = QPushButton("Confirmer")
        confirm_button.clicked.connect(dialog.accept)
        layout.addWidget(confirm_button)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            start = start_date_edit.date().toPython()
            end = end_date_edit.date().toPython()
            return start, end
        return None

    @staticmethod
    def open_or_resume_missing_responses_dialog(
        parent, prompt_on_load=True, on_finished=None, db_manager=None
    ):
        """
        Ouvre la boîte de dialogue MissingResponsesDialog à partir du progrès sauvegardé (si existe),
        ou en mode normal si prompt_on_load=True. Permet de passer un callback on_finished.
        Retourne l'instance du dialog ou None si rien à faire.
        """

        # Import local pour éviter l'import circulaire
        from missing_responses_dialog import MissingResponsesDialog

        progress_file = MissingResponsesDialog.PROGRESS_FILE
        if os.path.exists(progress_file):
            with open(progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                entries = data["entries"]
            dlg = MissingResponsesDialog(
                parent, entries, prompt_on_load=prompt_on_load, db_manager=db_manager
            )
            if on_finished:
                dlg.finished.connect(on_finished)
            dlg.show()
            return dlg
        return None


# --- Utilitaires de texte ---
class TextUtils:
    @staticmethod
    def normalize_special_characters(text):
        if not isinstance(text, str):
            return text
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("oe", "œ")
        return text.translate(str.maketrans({"’": "'"}))

    @staticmethod
    def clean_filename(s: str):
        import unicodedata
        import re

        s = unicodedata.normalize("NFKD", s)
        s = "".join(c if not unicodedata.combining(c) else "" for c in s)
        s = s.replace("æ", "ae").replace("Æ", "AE")
        s = s.replace("œ", "oe").replace("Œ", "OE")
        s = re.sub(r"[^\w\s\.-]", "", s)
        s = re.sub(r"\s+", "_", s)
        return s
