from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QWidget,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)
from PySide6.QtCore import Qt  # Import Qt for setWindowModality


class AudioSaverApp(QWidget):
    def __init__(self, db_manager, font_size=12):  # Ajout de font_size
        super().__init__()
        self.setWindowTitle("Ajouter un élément")
        self.db_manager = db_manager  # Utiliser l'instance partagée de DatabaseManager
        self.font_size = font_size  # Stocker la taille de police
        self.setStyleSheet(
            f"* {{ font-size: {self.font_size}px; }}"
        )  # Appliquer la taille de police

    def initialize_ui(self):
        if self.layout() is None:
            self.setLayout(QVBoxLayout())  # Initialiser un layout si aucun n'existe
        self.showMaximized()  # Ouvre la fenêtre principale en mode maximisé
        self.upload_audio()

        # Ajouter un bouton pour fermer la fenêtre
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.close)
        self.layout().addWidget(
            close_button
        )  # Ajouter le bouton à la mise en page existante

    def closeEvent(self, event):
        """Gérer la suppression propre de l'objet C++."""
        self.deleteLater()  # Supprimer l'objet proprement
        super().closeEvent(event)

    def upload_audio(self):
        # Crée une boîte de dialogue pour l'entrée simultanée
        dialog = QWidget()
        dialog.setWindowTitle("Télécharger un fichier audio et entrer les détails")
        dialog.setWindowModality(
            Qt.ApplicationModal
        )  # Rendre la boîte de dialogue modale
        layout = QFormLayout(dialog)

        # Sélection de fichier
        file_button = QPushButton("Sélectionner un fichier audio")
        file_path_input = QLineEdit()
        # file_path_input.setReadOnly(True)
        file_button.clicked.connect(lambda: self.select_file(file_path_input))
        layout.addRow("Fichier audio :", file_button)
        layout.addRow("", file_path_input)

        # Entrée de la question
        question_input = QLineEdit()
        layout.addRow("Question :", question_input)

        # Entrée de la réponse
        response_input = QLineEdit()
        layout.addRow("Réponse :", response_input)

        # Bouton de soumission
        submit_button = QPushButton("Soumettre")
        submit_button.clicked.connect(
            lambda: self.process_inputs(
                dialog,
                file_path_input,
                question_input,
                response_input,
            )
        )
        layout.addWidget(submit_button)

        dialog.setLayout(layout)
        dialog.destroyed.connect(
            lambda: self.safe_close()
        )  # Assure la fermeture de AudioSaverApp
        dialog.show()

    def safe_close(self):
        """Ferme l'application en toute sécurité si l'objet n'est pas supprimé."""
        if not self.isVisible():
            return
        self.close()

    def select_file(self, file_path_input):
        # Ouvre une boîte de dialogue pour sélectionner un fichier audio
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier audio",
            "",
            "Fichiers audio (*.mp3 *.wav *.ogg)",
        )
        if file_path:
            file_path_input.setText(file_path)

    def process_inputs(self, dialog, file_path_input, question_input, response_input):
        file_path = file_path_input.text()
        question = question_input.text()
        response = response_input.text()

        if not question.strip():
            QMessageBox.warning(
                self, "Avertissement", "La question ne peut pas être vide !"
            )
            return
        if not response.strip():
            QMessageBox.warning(
                self, "Avertissement", "La réponse ne peut pas être vide !"
            )
            return

        # Enregistrer les données dans la base de données via DatabaseManager
        try:
            self.db_manager.insert_record(
                file_path, question, response
            )  # La logique de génération est déplacée dans insert_record
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec de l'enregistrement des données dans la base de données : {e}",
            )
            return

        QMessageBox.information(
            self, "Succès", "Fichier audio et données enregistrés avec succès !"
        )

        # Réinitialiser les champs pour une nouvelle entrée
        file_path_input.clear()
        question_input.clear()
        response_input.clear()

        # Demander à l'utilisateur s'il souhaite ajouter une autre entrée
        continue_adding = QMessageBox.question(
            self,
            "Continuer ?",
            "Voulez-vous ajouter une autre entrée ?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if continue_adding == QMessageBox.No:
            dialog.close()
            self.close()
