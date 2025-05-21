import csv
import os
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from PySide6.QtGui import (
    QShortcut,
    QKeySequence,
)
from logger import logger
from missing_responses_dialog import MissingResponsesDialog
from common_methods import TimeUtils, ProgressBarHelper


class MassImporter(QWidget):
    def __init__(self, db_manager, font_size=12):  # Ajout de font_size
        super().__init__()
        self.setWindowTitle("Importer des données en masse")
        self.db_manager = db_manager  # Utiliser l'instance partagée de DatabaseManager
        self.font_size = font_size  # Stocker la taille de police
        self.setStyleSheet(
            f"* {{ font-size: {self.font_size}px; }}"
        )  # Appliquer la taille de police
        self.initialize_ui()

        # Ajouter les raccourcis clavier
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        select_csv_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        select_csv_shortcut.activated.connect(self.import_csv)

        logger.info("Interface MassImporter initialisée")

    def initialize_ui(self):
        layout = QVBoxLayout()

        # Bouton pour sélectionner un fichier CSV
        select_csv_button = QPushButton("Sélectionner des fichiers CSV (Ctrl+I)")
        select_csv_button.clicked.connect(self.import_csv)

        layout.addWidget(select_csv_button)

        # Label pour indiquer la contrainte d'unicité
        uniqueness_label = QLabel(
            "❗ : Deux entrées ne peuvent pas avoir simultanément les mêmes questions et les mêmes réponses. Ceci est implémenté pour éviter la duplication accidentelle"
        )
        layout.addWidget(uniqueness_label)

        # Ajout de la barre de progrès centralisée au layout
        self.progress_helper = ProgressBarHelper(parent_layout=layout)
        self.progress_helper.hide()

        # Bouton pour fermer la fenêtre
        close_button = QPushButton("Fermer (Ctrl+W)")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def import_csv(self):
        # Ouvre une boîte de dialogue pour sélectionner plusieurs fichiers CSV
        file_dialog = QFileDialog(
            self, "Sélectionner des fichiers CSV", "", "Fichiers CSV (*.csv)"
        )
        file_dialog.setFileMode(
            QFileDialog.ExistingFiles
        )  # Permet de sélectionner plusieurs fichiers existants
        file_dialog.setNameFilter("Fichiers CSV (*.csv)")  # Applique le filtre
        file_dialog.setOption(
            QFileDialog.DontUseNativeDialog, True
        )  # Désactive les options natives (facultatif)
        csv_paths, _ = file_dialog.getOpenFileNames()
        file_dialog.close()  # Fermer explicitement la boîte de dialogue
        if not csv_paths:
            return

        total_imported = 0
        total_failed = 0
        processed_files = 0
        total_files = len(csv_paths)

        # Initialisation pour l'avertissement des métadonnées
        found_uuid = False
        found_creation_date = False

        # Traiter chaque fichier CSV sélectionné
        missing_responses = []  # Pour stocker les entrées à compléter manuellement
        for csv_path in csv_paths:
            try:
                logger.info(f"Début d'importation depuis {csv_path}")
                with open(csv_path, "r", encoding="utf-8") as csv_file:
                    reader = csv.DictReader(csv_file)
                    if not {"audio_path", "question"}.issubset(reader.fieldnames):
                        logger.error(f"Colonnes CSV manquantes dans {csv_path}")
                        QMessageBox.warning(
                            self,
                            "Avertissement",
                            f"Le fichier {csv_path} ne contient pas les colonnes requises ('audio_path', 'question') et sera ignoré.",
                        )
                        processed_files += 1
                        continue

                    # Vérifier si les colonnes optionnelles sont présentes
                    if "UUID" in reader.fieldnames:
                        found_uuid = True
                    if "creation_date" in reader.fieldnames:
                        found_creation_date = True
                    # --- Ajout pour start_time et end_time ---
                    has_start_time = "start_time" in reader.fieldnames
                    has_end_time = "end_time" in reader.fieldnames

                    rows = list(reader)
                    total_rows = len(rows)
                    logger.info(
                        f"Nombre d'entrées à importer dans {csv_path}: {total_rows}"
                    )

                    # --- Nouvelle logique pour gérer les chemins relatifs audio_path ---
                    audio_base_dir = None
                    if rows:
                        # Trouver le premier audio_path non vide
                        first_audio_path = None
                        for row in rows:
                            candidate = row.get("audio_path", "").strip()
                            if candidate:
                                first_audio_path = candidate
                                break

                        if (
                            first_audio_path
                            and not os.path.isabs(first_audio_path)
                            and not os.path.exists(first_audio_path)
                        ):
                            reply = QMessageBox.question(
                                self,
                                "Chemin audio relatif ?",
                                f"Le fichier audio '{first_audio_path}' n'a pas été trouvé.\n\nEst-ce que les chemins audio de ce CSV sont relatifs à un dossier ?",
                                QMessageBox.Yes | QMessageBox.No,
                            )
                            if reply == QMessageBox.Yes:
                                folder = QFileDialog.getExistingDirectory(
                                    self,
                                    "Sélectionner le dossier parent des fichiers audio",
                                )
                                if folder:
                                    audio_base_dir = folder

                    # Mettre à jour la barre de progression pour ce fichier
                    self.progress_helper.show(total_rows)

                    failed_insertion_count = 0
                    for index, row in enumerate(rows, start=1):
                        file_path = row["audio_path"].strip()
                        if (
                            audio_base_dir
                            and file_path
                            and not os.path.isabs(file_path)
                        ):
                            file_path = os.path.join(audio_base_dir, file_path)
                        question = row["question"]
                        response = row.get("response", "")
                        attribution = row.get("attribution", "no-attribution")

                        start_time_ms = (
                            TimeUtils.parse_time_to_ms(row["start_time"])
                            if has_start_time
                            else None
                        )
                        end_time_ms = (
                            TimeUtils.parse_time_to_ms(row["end_time"])
                            if has_end_time
                            else None
                        )

                        # Ignorer les entrées avec réponse vide, mais les stocker pour saisie manuelle
                        if not response.strip():
                            failed_insertion_count += 1
                            logger.warning(
                                f"Entrée ignorée - réponse vide pour question: '{question}'"
                            )
                            missing_responses.append(
                                {
                                    "audio_path": file_path,
                                    "question": question,
                                    "response": response,
                                    "UUID": row.get("UUID", "").strip() or None,
                                    "creation_date": row.get(
                                        "creation_date", ""
                                    ).strip()
                                    or None,
                                    "start_time_ms": start_time_ms,
                                    "end_time_ms": end_time_ms,
                                    "attribution": attribution,
                                }
                            )
                            self.progress_helper.set_value(index)
                            continue

                        uuid = row.get("UUID", "").strip() or None  # UUID optionnel
                        creation_date = (
                            row.get("creation_date", "").strip() or None
                        )  # creation_date optionnel

                        # Enregistrer les données dans la base de données
                        try:
                            insertion_status_code = self.db_manager.insert_record(
                                file_path,
                                question,
                                response,
                                start_time_ms,
                                end_time_ms,
                                uuid,
                                creation_date,
                                attribution,
                            )
                            if insertion_status_code != 0:
                                failed_insertion_count += insertion_status_code
                                logger.warning(
                                    f"{question},{response} est déjà présent dans la base de données et n'est pas ajouté à nouveau"
                                )
                        except Exception as e:
                            logger.error(
                                f"Échec de l'enregistrement des données pour '{file_path}': {e}"
                            )
                            continue

                        self.progress_helper.set_value(index)

                    total_imported += total_rows - failed_insertion_count
                    total_failed += failed_insertion_count
                    processed_files += 1

                    # Afficher un aperçu de la progression totale
                    logger.info(
                        f"Fichier {processed_files}/{total_files} traité: {csv_path}"
                    )

            except Exception as e:
                logger.critical(f"Échec de la lecture du fichier CSV {csv_path} : {e}")
                QMessageBox.warning(
                    self, "Erreur", f"Échec de la lecture du fichier {csv_path} : {e}"
                )
                processed_files += 1
                continue

        self.progress_helper.hide()

        # Si des réponses sont manquantes, proposer une interface de saisie
        if missing_responses:
            self.prompt_missing_responses(missing_responses)
        # Message final avec le résumé
        custom_metadata_warning = ""
        if not found_uuid and not found_creation_date:
            custom_metadata_warning = (
                "❗(UUID) et ❗(creation_date) ne sont pas trouvés dans vos fichiers."
            )
        elif not found_uuid:
            custom_metadata_warning = "❗(UUID) n'est pas trouvé dans vos fichiers."
        elif not found_creation_date:
            custom_metadata_warning = (
                "❗(creation_date) n'est pas trouvé dans vos fichiers."
            )
        else:
            custom_metadata_warning = (
                "(UUID) et (creation_date) de coutume sont détectées et bien traitées."
            )

        logger.info(
            f"Importation terminée: {total_imported} entrées importées, {total_failed} échecs sur {processed_files} fichiers."
        )
        QMessageBox.information(
            self,
            "Complèt",
            f"Importation en masse terminée !\n\n"
            f"{total_files} fichiers traités\n"
            f"{total_imported} entrées importées avec succès\n"
            f"{total_failed} entrées dupliquées ou mal-formées ignorées\n"
            f"{custom_metadata_warning}",
        )

    def prompt_missing_responses(self, missing_responses):
        """
        Affiche une boîte de dialogue non bloquante pour compléter les réponses manquantes.
        Le résumé final sera affiché à la fermeture de la boîte de dialogue.
        """
        self.missing_dialog = MissingResponsesDialog(
            self, missing_responses, db_manager=self.db_manager
        )
        self.missing_dialog.finished.connect(
            lambda _: self.handle_missing_responses_finished(missing_responses)
        )
        self.missing_dialog.show()
        # On ne retourne plus rien ici, le traitement se fait dans le callback

    def handle_missing_responses_finished(self, missing_responses):
        """
        Callback appelé à la fermeture de la boîte de dialogue non bloquante.
        Affiche le résumé final (l'insertion est déjà faite par le dialog).
        """
        self.progress_helper.hide()
        # On ne peut plus compter précisément ici combien ont été insérées, donc on affiche juste le nombre total à compléter
        total_with_response = sum(
            1 for entry in missing_responses if entry.get("response", "").strip()
        )
        saved_for_later = len(missing_responses) - total_with_response
        QMessageBox.information(
            self,
            "Complèt",
            f"Saisie manuelle terminée !\n\n"
            f"{total_with_response} entrées avec réponse saisie manuellement\n"
            f"{saved_for_later} entrées non traitées restent à compléter plus tard (elles seront proposées à la prochaine importation ou reprise).",
        )
