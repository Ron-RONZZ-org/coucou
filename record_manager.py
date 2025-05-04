from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QLineEdit,  # Ajout pour le champ de recherche
)
from PySide6.QtCore import Qt


class RecordManagerApp(QWidget):
    def __init__(self, db_manager, font_size=12):  # Ajout de font_size
        super().__init__()
        self.setWindowTitle("Gérer les entrées")
        self.db_manager = db_manager  # Utiliser l'instance partagée de DatabaseManager
        self.font_size = font_size  # Taille de police par défaut
        self.setStyleSheet(
            f"* {{ font-size: {self.font_size}px; }}"
        )  # Appliquer la taille de police
        self.changed_lines = set()  # Suivre les lignes modifiées
        self.setup_ui()
        self.showMaximized()  # Ouvrir en taille maximale

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Champ de recherche
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher...")
        self.search_input.textChanged.connect(
            self.search_records
        )  # Connecter la recherche
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Table pour afficher les entrées
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Ajouter une colonne pour creation_date
        self.table.setHorizontalHeaderLabels(
            ["UUID", "Fichier Audio", "Question", "Réponse", "Créé le"]
        )
        self.table.itemChanged.connect(self.track_changes)  # Suivre les modifications
        layout.addWidget(self.table)

        # Boutons pour les actions
        button_layout = QHBoxLayout()
        save_button = QPushButton("Enregister")
        save_button.clicked.connect(
            self.save_changes
        )  # Enregistrer toutes les modifications
        button_layout.addWidget(save_button)

        delete_button = QPushButton("Supprimer")
        delete_button.clicked.connect(self.delete_record)
        button_layout.addWidget(delete_button)

        layout.addLayout(button_layout)

        # Charger les entrées
        self.load_records()

    def track_changes(self, item):
        """Ajoute la ligne modifiée à la liste des changements."""
        self.changed_lines.add(item.row())

    def save_changes(self):
        """Enregistre toutes les modifications dans la base de données."""
        # Créer une copie de changed_lines pour éviter les modifications pendant l'itération
        changed_lines_copy = list(self.changed_lines)
        for row in changed_lines_copy:
            record_id = self.table.item(row, 0).text()
            new_audio_file = self.table.item(row, 1).text()
            new_question = self.table.item(row, 2).text()
            new_response = self.table.item(row, 3).text()

            try:
                success = self.db_manager.update_record(
                    record_id, new_audio_file, new_question, new_response
                )
                self.changed_lines.discard(row)
                if not success:
                    raise Exception(f"Échec de la mise à jour pour UUID: {record_id}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

        if (
            not self.changed_lines
        ):  # Vérifie si toutes les modifications ont été enregistrées
            QMessageBox.information(
                self, "Succès", "Toutes les modifications ont été enregistrées."
            )

    def load_records(self):
        """Charge les entrées depuis la base de données et les affiche dans la table."""
        self.table.setRowCount(0)
        records = self.db_manager.fetch_all_records()
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            # UUID (lecture seule)
            uuid_item = QTableWidgetItem(record["UUID"])
            uuid_item.setFlags(uuid_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, uuid_item)

            # Fichier audio (modifiable)
            self.table.setItem(row, 1, QTableWidgetItem(record["audio_file"]))

            # Question (modifiable)
            self.table.setItem(row, 2, QTableWidgetItem(record["question"]))

            # Réponse (modifiable)
            self.table.setItem(row, 3, QTableWidgetItem(record["response"]))

            # Créé le (lecture seule)
            creation_date_item = QTableWidgetItem(record["creation_date"])
            creation_date_item.setFlags(creation_date_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, creation_date_item)

    def delete_record(self):
        """Supprime les entrées sélectionnés."""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self,
                "Erreur",
                "Veuillez sélectionner un ou plusieurs entrées à supprimer par CLIQUER sur les NUMÉROs des lignes.",
            )
            return

        for index in sorted(selected_rows, reverse=True):
            record_id = self.table.item(index.row(), 0).text()

            # Utiliser la méthode dédiée pour supprimer l'entrée
            success = self.db_manager.delete_record(record_id)
            if not success:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Échec de la suppression de l'entrée UUID: {record_id}.",
                )
                return

        QMessageBox.information(self, "Succès", "entrée(s) supprimé(s) avec succès.")
        self.load_records()  # Recharger les entrées après suppression

    def search_records(self, keyword):
        """Filtre les entrées affichées dans la table en fonction du mot-clé."""
        keyword = keyword.lower()
        for row in range(self.table.rowCount()):
            match = False
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item and keyword in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
