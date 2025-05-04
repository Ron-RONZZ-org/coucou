import csv
import logging  # Importer le module logging
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QProgressBar,  # Importer QProgressBar pour la barre de statut
)

# Configurer le logger
logging.basicConfig(
    filename="bulk_import.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class BulkAudioSaverApp(QWidget):
    def __init__(self, db_manager, font_size=12):  # Ajout de font_size
        super().__init__()
        self.setWindowTitle("Importer des données en masse")
        self.db_manager = db_manager  # Utiliser l'instance partagée de DatabaseManager
        self.font_size = font_size  # Stocker la taille de police
        self.setStyleSheet(
            f"* {{ font-size: {self.font_size}px; }}"
        )  # Appliquer la taille de police
        self.progress_bar = QProgressBar()  # Initialiser la barre de statut
        self.progress_bar.setVisible(False)  # La cacher par défaut
        self.initialize_ui()

    def initialize_ui(self):
        layout = QVBoxLayout()

        # Bouton pour sélectionner un fichier CSV
        select_csv_button = QPushButton("Sélectionner un fichier CSV")
        select_csv_button.clicked.connect(self.import_csv)

        layout.addWidget(select_csv_button)

        # Label pour indiquer la contrainte d'unicité
        uniqueness_label = QLabel(
            "❗ : Deux entrées ne peuvent pas avoir les mêmes questions et réponses. Ceci est implenmenté pour éviter la duplication accidentelle"
        )
        layout.addWidget(uniqueness_label)

        # Ajouter la barre de statut au layout
        layout.addWidget(self.progress_bar)

        # Bouton pour fermer la fenêtre
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def import_csv(self):
        # Ouvre une boîte de dialogue pour sélectionner un fichier CSV
        csv_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier CSV",
            "",
            "Fichiers CSV (*.csv)",
        )
        if not csv_path:
            return

        # Lire et traiter le fichier CSV
        try:
            with open(csv_path, "r", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                if not {"audio_path", "question", "response"}.issubset(
                    reader.fieldnames
                ):
                    QMessageBox.critical(
                        self,
                        "Erreur",
                        "Le fichier CSV doit contenir les colonnes : 'audio_path', 'question', 'response'.",
                    )
                    return

                rows = list(
                    reader
                )  # Convertir en liste pour connaître le nombre total de lignes
                total_rows = len(rows)
                self.progress_bar.setMaximum(total_rows)  # Définir la valeur maximale
                self.progress_bar.setValue(0)  # Réinitialiser la barre de statut
                self.progress_bar.setVisible(True)  # Afficher la barre de statut
                failed_insertion_count = 0
                for index, row in enumerate(rows, start=1):
                    file_path = row["audio_path"]
                    question = row["question"]
                    response = row["response"]
                    uuid = row.get("UUID", "").strip() or None  # UUID optionnel
                    creation_date = (
                        row.get("creation_date", "").strip() or None
                    )  # creation_date optionnel

                    # Enregistrer les données dans la base de données
                    try:
                        failed_insertion_count += self.db_manager.insert_record(
                            file_path, question, response, uuid, creation_date
                        )  # La logique de génération est déplacée dans insert_record
                        logging.info(f"{question},{response} est bien ajouté")
                    except Exception as e:
                        logging.error(
                            f"Échec de l'enregistrement des données pour '{file_path}': {e}"
                        )
                        QMessageBox.warning(
                            self,
                            "Erreur",
                            f"Échec de l'enregistrement des données pour '{file_path}': {e}",
                        )
                        continue

                    self.progress_bar.setValue(
                        index
                    )  # Mettre à jour la barre de statut

                self.progress_bar.setVisible(
                    False
                )  # Cacher la barre de statut après l'importation
                # Afficher un message de succès si aucune exception n'est levée
                custom_metadata_warning = ""
                all_custom_metadata_specified = True
                if not uuid:
                    custom_metadata_warning += "❗(UUID)"
                    all_custom_metadata_specified = False
                if not creation_date:
                    custom_metadata_warning += "❗(creation_date)"
                    all_custom_metadata_specified = False
                if all_custom_metadata_specified == False:
                    custom_metadata_warning += "ne sont pas trouvé dans votre fichier. Vérifier les noms des colonnes correspond avec exactitude si cela ne pas attendu"
                else:
                    custom_metadata_warning = "(UUID) et (creation_date) de coutume sont detectées et bien traitées."
                logging.info(
                    f"Importation terminée avec {failed_insertion_count} échecs."
                )
                QMessageBox.information(
                    self,
                    "Complèt",
                    f"Importation en masse terminée ! {failed_insertion_count} entrées dupliqué ou mal-formé ne sont pas ajouté\n\n{custom_metadata_warning}",
                )

        except Exception as e:
            self.progress_bar.setVisible(
                False
            )  # Cacher la barre de statut en cas d'erreur
            logging.critical(f"Échec de la lecture du fichier CSV : {e}")
            QMessageBox.critical(
                self, "Erreur", f"Échec de la lecture du fichier CSV : {e}"
            )
