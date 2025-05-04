import os
import unicodedata
import string
import logging  # Importer le module logging
import json  # Importer le module JSON pour la sauvegarde et la restauration
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QDialog,
    QDateEdit,
    QFileDialog,  # Importer QFileDialog pour sélectionner un fichier
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import (
    QDate,
    Qt,
)  # Importer QDate pour gérer les dates Qt et Qt pour les options de fenêtre

# Configurer le logger
logging.basicConfig(
    filename="retrieval_app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class RetrievalApp(QWidget):
    def __init__(self, db_manager, font_size=12):  # Ajout de font_size
        super().__init__()
        self.setWindowTitle("Afficher les éléments")
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowSystemMenuHint
        )  # Permettre la minimisation
        self.db_manager = db_manager  # Utiliser l'instance partagée de DatabaseManager
        self.font_size = font_size  # Taille de police par défaut
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.records = []
        self.current_record_index = 0
        self.setStyleSheet(
            f"* {{ font-size: {self.font_size}px; }}"
        )  # Appliquer la taille de police

        # Appeler le dialogue de sélection de date ou tout afficher
        self.show_date_range_dialog()

    def save_records_to_file(self, file_path="saved_records.json"):
        """Sauvegarde les enregistrements actuels dans un fichier JSON."""
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(self.records, file, ensure_ascii=False, indent=4)
            logging.info(f"Enregistrements sauvegardés dans {file_path}")
        except Exception as e:
            logging.error(f"Erreur lors de la sauvegarde des enregistrements: {e}")
            QMessageBox.critical(
                self, "Erreur", "Impossible de sauvegarder les enregistrements!"
            )

    def load_records_from_file(self, file_path="saved_records.json"):
        """Charge les enregistrements depuis un fichier JSON."""
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    self.records = json.load(file)
                logging.info(f"Enregistrements chargés depuis {file_path}")
                return True
            else:
                logging.warning(f"Fichier {file_path} introuvable.")
                return False
        except Exception as e:
            logging.error(f"Erreur lors du chargement des enregistrements: {e}")
            QMessageBox.critical(
                self, "Erreur", "Impossible de charger les enregistrements!"
            )
            return False

    def save_records_to_custom_file(self):
        """Sauvegarde les enregistrements dans un fichier personnalisé."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder les enregistrements", "", "JSON Files (*.json)"
        )
        if file_path:
            self.save_records_to_file(file_path)

    def load_records_from_custom_file(self):
        """Charge les enregistrements depuis un fichier personnalisé."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Charger les enregistrements", "", "JSON Files (*.json)"
        )
        if file_path:
            return self.load_records_from_file(file_path)
        return False

    def show_date_range_dialog(self):
        """Affiche un dialogue pour sélectionner une gamme de dates ou tout afficher."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Sélectionner une option")
        layout = QVBoxLayout(dialog)

        label = QLabel(
            "Voulez-vous afficher tous les enregistrements, une gamme de dates spécifique ou restaurer une session précédente ?"
        )
        layout.addWidget(label)

        date_range_button = QPushButton("Afficher une gamme de dates")
        date_range_button.clicked.connect(
            lambda: self.handle_date_range_selection(dialog)
        )
        layout.addWidget(date_range_button)

        all_records_button = QPushButton("Afficher tous les enregistrements")
        all_records_button.clicked.connect(
            lambda: self.handle_all_records_selection(dialog)
        )
        layout.addWidget(all_records_button)

        restore_session_button = QPushButton("Restaurer la session précédente")
        restore_session_button.clicked.connect(
            lambda: self.handle_restore_session(dialog)
        )
        layout.addWidget(restore_session_button)

        dialog.exec()

    def handle_date_range_selection(self, dialog):
        """Gère la sélection d'une gamme de dates."""
        dialog.accept()

        date_dialog = QDialog(self)
        date_dialog.setWindowTitle("Sélectionner une gamme de dates")
        layout = QVBoxLayout(date_dialog)

        start_date_label = QLabel("Date de début:")
        layout.addWidget(start_date_label)
        start_date_edit = QDateEdit()
        start_date_edit.setCalendarPopup(True)
        start_date_edit.setDate(
            QDate.currentDate().addDays(-1)
        )  # Utiliser QDate au lieu de date
        layout.addWidget(start_date_edit)

        end_date_label = QLabel("Date de fin:")
        layout.addWidget(end_date_label)
        end_date_edit = QDateEdit()
        end_date_edit.setCalendarPopup(True)
        end_date_edit.setDate(
            QDate.currentDate()
        )  # Utiliser QDate pour la date actuelle
        layout.addWidget(end_date_edit)

        confirm_button = QPushButton("Confirmer")
        confirm_button.clicked.connect(
            lambda: self.fetch_records_by_date_range(
                start_date_edit.date(), end_date_edit.date(), date_dialog
            )
        )
        layout.addWidget(confirm_button)

        date_dialog.exec()

    def handle_all_records_selection(self, dialog):
        """Gère la sélection pour afficher tous les enregistrements."""
        dialog.accept()
        self.records = self.db_manager.fetch_all_records()
        if self.records:
            self.initialize_ui()
        else:
            QMessageBox.information(
                self,
                "Info",
                "Aucun entrée trouvé. Veuillez ajouter les entrées d'abord",
            )
            self.close()

    def handle_restore_session(self, dialog):
        """Gère la restauration de la session précédente."""
        dialog.accept()
        use_custom_file = QMessageBox.question(
            self,
            "Restaurer",
            "Voulez-vous charger depuis un fichier personnalisé ?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if use_custom_file == QMessageBox.Yes:
            success = self.load_records_from_custom_file()
        else:
            success = self.load_records_from_file()

        if success:
            if self.records:
                self.initialize_ui()
            else:
                QMessageBox.information(
                    self, "Info", "Aucun enregistrement à restaurer."
                )
                self.show_date_range_dialog()
        else:
            QMessageBox.warning(
                self, "Erreur", "Impossible de restaurer la session précédente."
            )
            self.show_date_range_dialog()

    def fetch_records_by_date_range(self, start_date, end_date, dialog):
        """Récupère les enregistrements entre une gamme de dates."""
        dialog.accept()
        start = start_date.toPython()
        end = end_date.toPython()
        self.records = self.db_manager.fetch_record_by_creation_date(start, end)
        if self.records:
            self.initialize_ui()
        else:
            QMessageBox.information(self, "Info", "Aucun entrée trouvé.")
            self.show_date_range_dialog()

    def initialize_ui(self):
        """Configure l'interface utilisateur pour la récupération des entrées."""
        self.showMaximized()
        self.display_next_item()

        # Ajouter une boîte de dialogue pour fermer la session
        dialog = QDialog(self)
        dialog.setWindowTitle("Session terminée")
        layout = QVBoxLayout(dialog)

        session_end_label = QLabel("Session terminée.")
        layout.addWidget(session_end_label)

        close_button = QPushButton("Fermer")
        close_button.clicked.connect(lambda: (dialog.accept(), self.close()))
        layout.addWidget(close_button)

        dialog.exec()

    def display_next_item(self):
        if not self.records:
            QMessageBox.information(self, "Info", "Tout fait! Félicitations! 🎂")
            return

        record = self.records[self.current_record_index]
        audio_path = record["audio_file"]
        question = record["question"]
        correct_response = record["response"]

        dialog = QDialog(self)
        dialog.setWindowTitle("Afficher l'élément")
        layout = QVBoxLayout(dialog)

        question_label = QLabel(f"Question: {question}")
        layout.addWidget(question_label)

        play_button = QPushButton("Lire l'audio")
        play_button.clicked.connect(lambda _, path=audio_path: self.play_audio(path))
        layout.addWidget(play_button)

        response_input = QLineEdit()
        layout.addWidget(response_input)

        submit_button = QPushButton("Vérifier la réponse")
        submit_button.clicked.connect(
            lambda _, input_field=response_input, response=correct_response, dlg=dialog: self.check_response_dialog(
                input_field, response, dlg
            )
        )
        layout.addWidget(submit_button)
        save_custom_button = QPushButton("Sauvegarder dans un fichier personnalisé")
        save_custom_button.clicked.connect(self.save_records_to_custom_file)
        layout.addWidget(save_custom_button)
        dialog.exec()

    @staticmethod
    def normalize_text(text):
        """Normalise le texte en supprimant la ponctuation et en remplaçant 'oe' par 'œ'."""
        text = unicodedata.normalize("NFKC", text)  # Normalisation Unicode
        text = text.lower().replace("oe", "œ")  # Remplace 'oe' par 'œ'
        text = text.translate(
            str.maketrans("", "", string.punctuation + "’'")
        )  # Supprime la ponctuation
        return text.strip()

    def check_response_dialog(self, input_field, correct_response, dialog):
        user_response = input_field.text().strip()
        if not user_response:
            QMessageBox.warning(self, "Erreur", "La réponse ne peut pas être vide!")
            return

        user_response_normalized = self.normalize_text(user_response)
        correct_response_normalized = self.normalize_text(correct_response)
        logging.info(f"User response: {user_response_normalized}")
        logging.info(f"Correct response: {correct_response_normalized}")
        print(user_response_normalized)
        print(correct_response_normalized)
        if user_response_normalized == correct_response_normalized:
            logging.info("Bonne réponse!")
            QMessageBox.information(self, "Succès", "Bonne réponse!")
            self.records.pop(self.current_record_index)
            self.save_records_to_file()  # Sauvegarder les enregistrements après modification
        else:
            logging.warning("Mauvaise réponse!")
            QMessageBox.warning(
                self,
                "Erreur",
                f"Mauvaise réponse! La correct réponse est:\n {correct_response} ",
            )
            self.records.append(self.records.pop(self.current_record_index))
            self.save_records_to_file()  # Sauvegarder les enregistrements après modification

        # Stop audio playback and close the dialog
        self.stop_audio(dialog)
        self.display_next_item()

    def play_audio(self, audio_path):
        if not os.path.exists(audio_path):
            logging.error(f"Le fichier audio est introuvable: {audio_path}")
            QMessageBox.critical(self, "Erreur", "Le fichier audio est introuvable!")
            return

        logging.info(f"Lecture de l'audio: {audio_path}")
        self.media_player.setSource(audio_path)
        self.media_player.play()

    def stop_audio(self, dialog=None):
        """Stop audio playback and optionally close the dialog."""
        if self.media_player.isPlaying():
            logging.info("Arrêt de la lecture audio.")
            self.media_player.stop()
        if dialog:
            dialog.accept()

    def closeEvent(self, event):
        """Arrêter l'audio proprement et sauvegarder les enregistrements."""
        self.save_records_to_file()  # Sauvegarder les enregistrements à la fermeture
        logging.info("Fermeture de l'application.")
        self.media_player.stop()
        super().closeEvent(event)
        self.deleteLater()  # Supprimer explicitement l'instance pour libérer les ressources
