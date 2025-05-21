import csv
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import (
    QShortcut,  # Déplacé ici depuis PySide6.QtWidgets
    QKeySequence,
)


class exporterBulk(QWidget):
    def __init__(self, db_manager, font_size=12):  # Ajout de font_size
        super().__init__()
        self.setWindowTitle("Exporter des données en masse")
        self.db_manager = db_manager  # Utiliser l'instance partagée de DatabaseManager
        self.font_size = font_size  # Stocker la taille de police
        self.setStyleSheet(
            f"* {{ font-size: {self.font_size}px; }}"
        )  # Appliquer la taille de police
        self.initialize_ui()

    def initialize_ui(self):
        layout = QVBoxLayout()

        # Bouton pour exporter les données
        export_csv_button = QPushButton("Exporter vers un fichier CSV")
        export_csv_button.clicked.connect(self.export_to_csv)
        layout.addWidget(export_csv_button)

        # Bouton pour fermer la fenêtre
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        # Ajout du raccourci clavier pour fermer la fenêtre
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        self.setLayout(layout)

    def export_to_csv(self):
        # Ouvre une boîte de dialogue pour sélectionner l'emplacement du fichier CSV
        csv_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer sous",
            "",
            "Fichiers CSV (*.csv)",
        )
        if not csv_path:
            return

        # Ajouter l'extension .csv si elle est manquante
        if not csv_path.endswith(".csv"):
            csv_path += ".csv"

        # Demander si l'utilisateur souhaite inclure UUID et creation_date
        include_metadata = (
            QMessageBox.question(
                self,
                "Inclure les métadonnées",
                "Voulez-vous inclure les colonnes «UUID» et «date de création» dans l'exportation ?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        )

        # Récupérer les entrées depuis la base de données
        try:
            records = self.db_manager.fetch_all_records()
            if not records:
                QMessageBox.information(self, "Info", "Aucun entrée trouvé à exporter.")
                return

            # Définir les colonnes à inclure
            if include_metadata:
                fieldnames = [
                    "UUID",
                    "audio_path",
                    "question",
                    "response",
                    "creation_date",
                ]
            else:
                fieldnames = ["audio_path", "question", "response"]

            # Écrire les entrées dans le fichier CSV
            with open(csv_path, "w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()

                for record in records:
                    row = {
                        "audio_path": record["media_file"],
                        "question": record["question"],
                        "response": record["response"],
                    }
                    if include_metadata:
                        row["UUID"] = record["UUID"]
                        row["creation_date"] = record["creation_date"]
                    writer.writerow(row)

            QMessageBox.information(
                self, "Succès", f"Exportation terminée avec succès vers {csv_path} !"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur", f"Échec de l'exportation des données : {e}"
            )

    def closeEvent(self, event):
        """Fermer proprement la connexion à la base de données."""
        self.db_manager.close_connection()
        super().closeEvent(event)
